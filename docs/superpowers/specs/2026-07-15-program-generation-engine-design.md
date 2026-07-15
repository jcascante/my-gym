# Program Generation Engine — Design Proposal

**Status:** Proposal (design only — no implementation in this scope)
**Date:** 2026-07-15
**Scope note:** Progress tracking is out of scope (built later). This document is a proposal; it does not build the solution.

## 1. Overview

A **pure rules-based** program-generation engine. It takes a user's profile, a chosen
training environment, and program preferences, then produces a structured workout program
the user **co-designs** through a `match → draft → feedback → accept` loop. State is
persisted at each stage.

The engine is deterministic and fast (sub-100 ms, comfortably under the <2 s target in
PROJECT_SCOPE). No LLM runs in the loop, but a seam is designed in so natural-language
feedback parsing can be added later without touching the engine core.

### In scope
- Template model, matching, exercise selection, progression math, draft + re-adaptation loop.
- Backend engine + API endpoints.
- Frontend builder wizard + preview.

### Out of scope
- Progress tracking / workout logging / post-workout feedback (`UserWorkoutLog`, `WorkoutFeedback`).
- LLM implementation (seam only).
- Any implementation work — this is a proposal.

## 2. Layered template model

A `ProgramTemplate` composes three **independent, swappable layers**:

- **Split** — the weekly session structure (e.g. Upper/Lower ×4). Each session is an ordered
  list of **slots**.
- **Slot rules** — each slot describes *what fills it* (movement pattern or body region, muscle
  emphasis, priority, set/rep scheme), **not** a specific exercise. Exercises are chosen at
  generation time.
- **Progression reference** — `{model_key, params}` pointing at a code-defined progression model.

Example (Upper/Lower ×4, `upper_a` session):

```yaml
split:
  sessions:
    - key: upper_a
      name: "Upper A"
      order: 1
      slots:
        - { pattern: horizontal_push, priority: primary,   scheme: main }
        - { pattern: horizontal_pull, priority: primary,   scheme: main }
        - { pattern: vertical_push,   priority: secondary, scheme: accessory }
        - { region:  core,            priority: accessory, scheme: accessory }
    - key: lower_a
      # ...
progression:
  model_key: linear_load
  params: { increment_source: environment }
```

`scheme` references named set/rep schemes (e.g. `main = 3×5`, `accessory = 3×10`) that the
progression model consumes together with the week number to produce concrete sets/reps/load.

## 3. Storage split

- **Templates → database** (`program_templates`). Split, slot rules, progression reference,
  and required inputs are stored as **validated JSON columns** (Pydantic models on the way in
  and out). Targeting metadata (goals, experience levels, day/duration ranges) lives in
  queryable columns for matching. Templates are seeded via a script mirroring the exercise
  seed (`app/db/seed/`), and are runtime-editable later via an admin surface.
- **Progression *algorithms* → code**, referenced by `model_key`. The DB stores *configuration*;
  code stores *logic*. This reconciles "templates in the DB" with "progression models in code."

### Progression models (code)

All four ship, behind a pluggable protocol so the most complex (undulating) can land last:

| `model_key`         | Behavior |
|---------------------|----------|
| `linear_load`       | Fixed increment added each week at fixed sets/reps. Increment from the environment's `available_weight_increments`. |
| `double_progression`| Work a rep range; add reps to the top across all sets, then add load and reset to the bottom. |
| `weekly_undulating` | Vary intensity/reps across the week (heavy/light/volume days) for the same lift. |
| `deload` (modifier) | Wraps any base model; every Nth week cuts volume/intensity, then resumes the climb. |

```python
class ProgressionModel(Protocol):
    key: str
    def resolve(self, slot: SlotScheme, week: int, base_load: float, params: dict) -> SetScheme:
        """Return concrete sets, reps, load, and rest for a slot in a given week."""
```

`Deload` is a decorator over a base `ProgressionModel`. Models are registered in a keyed
registry resolved from the template's `model_key`.

## 4. Data model (new tables)

| Table | Purpose | Key fields |
|-------|---------|-----------|
| `program_templates` | The catalog of blueprints (§2, §3). | `id, name, slug, description, goals[], experience_levels[], days_per_week_min/max, session_duration_min/max, split (JSON), slot_rules (JSON), progression_ref (JSON), required_inputs (JSON), is_active` |
| `workout_programs` | A generated program instance. | `id, user_id, template_id, environment_id, name, focus, status, duration_weeks, days_per_week, start_date, weight_unit, constraints (JSON), created_at, updated_at` |
| `workouts` | One row per session in the program's **base week**. Aligns with PROJECT_SCOPE "Workouts." | `id, program_id, key, name, focus, order` |
| `workout_exercises` | One row per slot in a session. | `id, workout_id, order, exercise_id, fills_rule (JSON: pattern/region), sets, reps_min, reps_max, base_load, rest_seconds, scheme_key, is_locked, is_user_swapped` |

`workout_programs.status`: **`draft → active → archived`** (tracking-related statuses deferred).

`workout_programs.constraints` (JSON) accumulates the user's edits and is the single source of
truth for re-adaptation:

```json
{
  "locked_slots": [12, 15],
  "excluded_exercise_ids": [88],
  "swaps": { "14": 42 },
  "volume_adjustments": { "upper_a": -1, "program": 0 },
  "required_inputs": { "bench_press_start": 60, "squat_start": 80 }
}
```

### Base-week + derive (key decision)

The program stores the **base week once** (`workouts` + `workout_exercises`). Each week's
concrete loads/reps are **derived at read time** by applying the progression model to the base
scheme and week number. This keeps re-adaptation cheap (edit once, no rewriting of N×days rows)
and matches the "fast engine" ethos. Per-week materialization can be added later when tracking
needs immutable per-day rows. *(Alternative considered: materialize all weeks up front —
rejected for MVP as heavier to store and churn on every edit.)*

## 5. Matching algorithm — `POST /programs/match`

Score each template against the profile as a weighted sum:

| Factor | Weight | Rule |
|--------|--------|------|
| Goal match | high | Template `goals` contains profile `fitness_focus`. |
| Experience match | high | Template `experience_levels` contains profile `experience_level`. |
| Days/week fit | medium | Requested `days_per_week` within template range; distance-penalized. |
| Session duration fit | medium | Requested duration within template range; distance-penalized. |
| Equipment feasibility | gate | A template whose required patterns cannot be filled by the environment is excluded (or heavily penalized). |

Returns the ranked **top 3** with a fit % and a per-factor "why this fits" breakdown, plus each
template's `required_inputs`. Deterministic, sub-millisecond.

## 6. Exercise selection (per slot)

For each slot's criteria:

1. **Candidate pool** = active exercises matching the slot's movement pattern / body region and
   muscle emphasis.
2. **Filter**:
   - `equipment_tags ⊆ environment.equipment_tags`
   - `difficulty_level ≤ user experience` (+1 level tolerance)
   - `contraindications ∩ user injuries = ∅`
3. **Rank**: primary-muscle fit, difficulty proximity, variety (avoid repeating a
   `movement_slug` already used in the program), slot priority.
4. **Constraints overlay**: locked/swapped slot → forced exercise; excluded exercise → dropped
   from pool; otherwise pick the top candidate.
5. **Fallback**: empty pool after filters → relax the least-critical filter (difficulty
   tolerance first) and flag the slot in the response.

## 7. Feedback & re-adaptation — `POST /programs/{id}/feedback`

Re-adaptation is **deterministic re-generation over the constraints overlay**, never ad-hoc
patching. Each action mutates `constraints`, then selection re-runs **only for affected slots**,
preserving everything locked. This guarantees edits the user liked survive later passes.

| Action | Effect |
|--------|--------|
| **swap** | Replace one slot's exercise with a chosen valid alternative. Records `swaps` + `is_user_swapped`. Alternatives via `GET /programs/{id}/slots/{slot_id}/alternatives`. |
| **exclude / regenerate slot** | Drop an exercise (adds to `excluded_exercise_ids`) and let the engine pick the next best for that slot. |
| **adjust volume/intensity** | Nudge sets/day or program volume within safe bounds; re-applies via `volume_adjustments`. |
| **lock** | Pin a slot so re-adaptation never changes it (`locked_slots`). |

Actions are repeatable until the user accepts.

## 8. End-to-end flow → endpoints

| User step | Endpoint | Result |
|-----------|----------|--------|
| Info collected, engine picks matching templates | `POST /programs/match` | Ranked shortlist + each template's `required_inputs` |
| User picks one, provides extra info if required | *(client collects `required_inputs`)* | — |
| Engine creates draft | `POST /programs/draft` | Persists `status=draft`, returns derived preview |
| User reviews | `GET /programs/{id}/preview` | All weeks derived |
| Feedback → engine re-adapts | `POST /programs/{id}/feedback` | Updated draft (repeatable) |
| (swap helper) | `GET /programs/{id}/slots/{slot_id}/alternatives` | Valid substitutes for a slot |
| User accepts → saved | `POST /programs/{id}/accept` | `status=active` (optionally archives prior active program) |
| Preview program | `GET /programs/{id}` | Read-only program |

The existing 501 `POST /programs` stub and `ProgramCreationRequest` schema are repurposed into
the `match` / `draft` requests. `ProgramCreationRequest` is extended/split to carry the match
inputs and, later, the chosen template id + required inputs.

## 9. Backend services layout

```
app/services/program/
  matching.py          # score templates vs profile -> ranked shortlist
  selection.py         # pick exercises per slot (filters, ranking, constraints)
  progression/
    __init__.py        # registry keyed by model_key
    base.py            # ProgressionModel protocol, SetScheme
    linear_load.py
    double_progression.py
    weekly_undulating.py
    deload.py          # modifier/decorator
  drafting.py          # template + selection -> persisted base-week draft
  adaptation.py        # apply FeedbackAction -> mutate constraints -> re-run affected slots
  preview.py           # derive concrete per-week schedule for display
  feedback_parser.py   # FeedbackParser protocol (LLM-ready seam)
```

### LLM-ready seam

```python
class FeedbackParser(Protocol):
    def parse(self, raw: FeedbackInput) -> FeedbackAction: ...
```

MVP implementation handles structured actions from the UI. A future LLM implementation parses
natural-language feedback into the **same** `FeedbackAction` type; the engine core is unchanged.

## 10. Performance & testing

**Performance:** in-memory computation over ~135 exercises and a handful of templates; one
cacheable exercise-library read. Generation is well under 100 ms versus the <2 s target. Async
SQLAlchemy throughout; exercise library is cacheable in memory.

**Testing (TDD, >80% coverage):**
- Unit: match scoring; selection filters (equipment / injury / difficulty); each progression
  model's math (linear increments, deload weeks, double-progression rollover, undulating
  pattern); adaptation preserves locks.
- Integration: full `match → draft → feedback → accept` flow.
- Determinism enables **golden-file program snapshots**.

## 11. Frontend (React + TypeScript)

**Pattern:** a single **Program Builder wizard** at `/programs/new` driving the four engine
stages via step state, plus a read-only preview route. TanStack Query owns server state; each
feedback action refetches the draft. Reuses the existing component library
(`Button`, `Card`, `FormField`, `Alert`, `Spinner`) and the existing `ProgramCreationForm`.

### Routes (add to `App.tsx`)

| Route | Purpose |
|-------|---------|
| `/programs` | List of the user's programs (draft + active) |
| `/programs/new` | Builder wizard (steps below) |
| `/programs/:id` | Read-only program preview (accepted or draft) |

### Wizard steps (in-page stepper, like `OnboardingPage`)

1. **Preferences** — reuse `ProgramCreationForm` (environment, days/week, duration, focus,
   weight unit, increments, progression preference, start date) → `useMatchTemplates`.
2. **Select template** — `TemplateMatchList` of `TemplateMatchCard`s showing fit %, "why this
   fits" factors, top-3 ranked; user picks one.
3. **Required inputs** *(conditional)* — `RequiredInputsForm` rendered dynamically from the
   chosen template's `required_inputs` (e.g. starting loads); skipped if none →
   `useCreateDraft`.
4. **Review & adapt** — `DraftProgramView`: `WeekTabs` (derived weeks) → `SessionCard` →
   `SlotRow`. Each slot has a `SlotFeedbackMenu` (swap / exclude / regenerate / lock / adjust);
   swap opens `ExerciseAlternativesModal` fed by `useSlotAlternatives`. `VolumeAdjustControl`
   nudges day/program volume. Every action → `useSubmitFeedback` → draft refetch → re-render.
   Loop freely.
5. **Accept** — `useAcceptProgram` flips draft→active → navigate to `/programs/:id`.

### New components

`ProgramBuilderPage`, `Stepper`, `TemplateMatchList` / `TemplateMatchCard`, `RequiredInputsForm`,
`DraftProgramView`, `WeekTabs`, `SessionCard`, `SlotRow`, `SlotFeedbackMenu`,
`ExerciseAlternativesModal`, `VolumeAdjustControl`, `ProgramPreview`, `ProgramListCard`.

### State & API

- Builder holds `draftId` + current step (local state or a small Zustand `programBuilder` store).
- Extend `src/api/programs.ts` with `matchTemplates`, `createDraft`, `getProgramPreview`,
  `submitFeedback`, `getSlotAlternatives`, `acceptProgram`.
- Add TanStack Query hooks in `hooks/usePrograms.ts` mirroring them.
- New TS types in `src/types/`: `TemplateMatch`, `RequiredInput`, `DraftProgram`, `Workout`,
  `WorkoutSlot`, `FeedbackAction`.

### UX notes

- Engine <100 ms → transitions feel instant; `Spinner` on mutations.
- Follows the existing Tailwind design system (responsive, accessible, keyboard-navigable
  menus/modals).
- Locked slots show a 🔒 badge; user-swapped slots a subtle marker so re-adaptation intent is
  legible.

### Full-stack flow

```
[Preferences form] ──POST /programs/match──▶ [ranked shortlist]
      ▼ pick one
[Required inputs?] ──POST /programs/draft──▶ [persisted draft]
      ▼
[Review: week tabs + slots] ──POST /programs/{id}/feedback──▶ [re-adapted draft]  ⟲ repeat
      ▼ accept
[POST /programs/{id}/accept] ──▶ status=active ──▶ [/programs/:id preview]
```

### Frontend testing

Vitest + React Testing Library per component (template selection, slot swap flow, wizard step
gating), following the `react-component-testing` skill.

## 12. Template authoring & seed examples

Templates live in the DB (§3), so authoring is fundamentally a data-entry problem. The MVP
avoids exposing that data shape to humans.

### MVP: curated seed catalog

The MVP ships a small **curated catalog** of example templates, authored as validated data and
loaded by a seed script (`app/db/seed/`, mirroring the exercise seed). No authoring UI is built
yet; trainers do not self-author in the MVP. This gives the matching engine real templates to
work against on day one while keeping scope tight.

Initial examples to seed (chosen for coverage across goal / experience / days / equipment):

| Template | Days | Experience | Goal focus | Progression | Environment |
|----------|------|-----------|-----------|-------------|-------------|
| Full Body | 3 | beginner | general / strength | `linear_load` + `deload` | gym or home |
| Bodyweight Full Body | 3 | beginner | general | `double_progression` (reps) | bodyweight |
| Upper / Lower | 4 | intermediate | strength / muscle_gain | `double_progression` + `deload` | gym |
| Push / Pull / Legs | 6 | intermediate–advanced | muscle_gain | `double_progression` + `deload` | gym |

### Future (design consideration only — not built in MVP)

Deferred per decision; captured here so the data model doesn't wall it off:

- **Form-based template builder** — a guided UI where a trainer composes a template with
  dropdowns (add sessions, add slots by movement pattern / body region / priority / set-rep
  scheme, pick a progression model + params, set deload cadence) and **never edits raw
  JSON/YAML**. Live-validated against the same Pydantic models that guard the seed. This is the
  intended "user-friendly" authoring path once the MVP engine is proven.
- **LLM-assisted authoring** — describe a program in natural language ("4-day upper/lower for
  intermediate lifters focused on hypertrophy") and have an LLM emit a draft template that the
  trainer refines in the form builder. Reuses the same validation seam as the `FeedbackParser`
  (§9); no new engine surface.
- **Ownership & roles** — the MVP catalog is global/admin-curated. Trainer-owned or org-scoped
  templates (and the role/permission model they require) are a future concern; the
  `program_templates` table can gain an optional `owner_id` / `visibility` column later without
  reshaping the engine.

## 13. Migrations

New Alembic migration adds `program_templates`, `workout_programs`, `workouts`,
`workout_exercises`. A seed script (`app/db/seed/`) populates the initial curated templates
(§12), mirroring the exercise seed pattern. Progression models are code-only (no schema).

## 14. Open decisions / notes

- **Base-week + derive** (§4) is the recommended storage strategy; revisit if/when tracking
  requires immutable per-week rows.
- **Template authoring** (§12): MVP is a seeded curated catalog; the friendly form builder and
  LLM-assisted authoring are deferred, with the schema kept forward-compatible for both.
- `ProgramCreationRequest` reshaping (§8) should preserve backward compatibility with the
  existing frontend `ProgramCreationForm` fields where possible.
