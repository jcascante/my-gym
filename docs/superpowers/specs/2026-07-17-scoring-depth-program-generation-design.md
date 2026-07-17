# Scoring-Depth Program Generation — Design

**Status:** Approved design (brainstormed 2026-07-17)
**Approach:** Algorithmic depth now, ML-ready seams after MVP. Latency budget 500 ms.
**Builds on:** The existing rules-based engine (`backend/app/services/program/`) and the
already-shipped taxonomy / progression-style / effort-method work.

## 1. Goal

Raise program quality before MVP ships by making **template matching** and **exercise
selection** substantially smarter, driven by richer user signals — while staying deterministic,
fast, and structured so learned scorers can drop in later.

User-prioritized improvements (in order):

1. **Movement preferences** — bias exercise choice toward preferred equipment families
   (barbell, dumbbell, kettlebell, machine, cable, bodyweight, bands) as a **soft weight, never
   a hard filter**. A single program must be free to mix families (e.g. barbell main + kettlebell
   accessory + bodyweight core).
2. **Focus + smart complementation** — honor a primary focus (e.g. upper body) while
   intelligently filling remaining volume with complementary/antagonist work and core, instead
   of leaving gaps or over-hammering the focus.
3. **Periodization tolerance** — already expressed as `ProgressionStyle` (`consistent` /
   `variable`); surfaced and wired more deliberately, not re-invented.
4. **Historical adaptation** — explicitly **out of scope** for now.
5. **Week-to-week variety** — configurable exercise rotation across weeks (`low` / `medium` /
   `high`), keeping main lifts stable so progression stays coherent.

Non-goals: user-authored templates (a future admin/trainer **Templates Module** owns authoring);
any learned model in the MVP; historical/longitudinal personalization.

## 2. Design principles

- **Soft over hard.** New preferences are *weights*, not filters. Equipment feasibility and
  injury contraindications remain the only hard gates. A preference can never empty a slot's pool.
- **Weighted linear scoring over lexicographic tuples.** Selection moves from the current
  fixed-order tuple to a tunable weighted sum so factors trade off smoothly and weights are one
  step from being learned.
- **Feature extraction separated from scoring.** Every scorer consumes a plain feature dict, so
  the same features can later feed a learned model without touching call sites.
- **Curated templates stay curated.** We enrich *matching* and *selection*; template authoring is
  a separate future module.

## 3. New user signals

All three are **per-program** inputs (they can legitimately vary by environment and intent), stored
in `WorkoutProgram.constraints` alongside the existing `progression_style` / `effort_method`.
Optional profile-level defaults can seed them later; MVP collects them in the creation wizard.

| Signal | Shape | Default | Role |
|--------|-------|---------|------|
| `movement_preferences` | `dict[EquipmentFamily, float]` weights in `[0.0, 2.0]`, e.g. `{"kettlebell": 1.5, "machine": 0.5}` | all `1.0` (neutral) | Soft multiplier in selection scoring. Missing family = neutral. |
| `complementary_focus` | `bool` (+ derived antagonist/core targeting) | `true` | When the focus is a region, spend non-primary slots on under-covered / antagonist muscles + core. |
| `variety_preference` | enum `low` \| `medium` \| `high` | `low` | Controls week-to-week rotation of eligible (non-main) slots. |

`EquipmentFamily` is a new enum mapping the granular `Exercise.equipment_tags` (≈38 values) up to
7 families. The mapping lives in one place (`preferences.py`) and is the only equipment-family
authority.

## 4. Equipment families (`preferences.py`)

A new module owns:

- `EquipmentFamily` enum: `barbell, dumbbell, kettlebell, machine, cable, bodyweight, bands`.
- `EQUIPMENT_FAMILY: dict[str, EquipmentFamily]` mapping each seeded equipment tag to a family
  (e.g. `barbell → barbell`, `ez_bar → barbell`, `lat_pulldown_machine → machine`,
  `cable_machine → cable`, `none → bodyweight`, `resistance_bands → bands`).
- `movement_preference_weight(ex, prefs) -> float`: the exercise's preference multiplier =
  the **max** family weight among its equipment tags (max, not mean, so a mostly-preferred
  compound isn't penalized by an incidental bench tag). Neutral `1.0` when `prefs` is empty.

This keeps the granular tags intact for filtering while giving preferences a coarse, robust axis.

## 5. Enhanced exercise selection (`selection.py`)

### 5.1 Filters (unchanged, still hard gates)
Equipment subset, difficulty tolerance, injury contraindications, exclusions, locks, and the
empty-pool difficulty-relax fallback all stay exactly as today.

### 5.2 From tuple to weighted score
Replace the lexicographic `_score` tuple with a weighted linear model:

```python
@dataclass(frozen=True)
class SelectionWeights:
    variety: float = 1.0
    priority_fit: float = 1.5      # compound↔primary, isolation↔accessory
    muscle_fit: float = 1.0
    difficulty: float = 0.75
    unilateral_balance: float = 0.5
    movement_preference: float = 1.25   # NEW
    complementary_coverage: float = 1.25  # NEW

class ExerciseScorer(Protocol):
    def score(self, features: dict[str, float]) -> float: ...
```

`HeuristicExerciseScorer` = weighted sum of a normalized feature dict. A future
`LearnedExerciseScorer` implements the same protocol. `select_for_slot` extracts features per
candidate, scores, and takes the max.

### 5.3 New features
- **movement_preference** — `movement_preference_weight(ex, prefs)` (§4), normalized to `[0,1]`.
- **complementary_coverage** — for non-primary slots when `complementary_focus` is on: reward
  exercises whose primary muscles are **under-covered** in the session so far. Uses a running
  muscle-coverage counter on `SelectionContext` (see §6). Neutral for primary slots (they follow
  the slot's own pattern/muscle rule).

Existing features (variety, priority_fit, muscle_fit, difficulty, unilateral_balance) are kept and
folded into the same normalized dict.

### 5.4 `SelectionContext` additions
```python
@dataclass
class SelectionContext:
    equipment: list[str]
    experience: str
    injuries: list[str]
    used_movement_slugs: set[str]
    used_unilateral_flags: list[bool] = field(default_factory=list)
    movement_preferences: dict[str, float] = field(default_factory=dict)  # NEW: family->weight
    muscle_coverage: Counter[str] = field(default_factory=Counter)        # NEW
    complementary_focus: bool = True                                      # NEW
    weights: SelectionWeights = field(default_factory=SelectionWeights)   # NEW
```
`build_draft` updates `muscle_coverage` (and the existing slug/unilateral trackers) after each
pick. Backward compatibility: the new `SelectionContext` fields default to neutral (empty prefs
→ `1.0` multiplier, empty coverage → uniform deficit → no bias), so on existing fixtures the
weighted score preserves today's ranking. The product default the wizard sends is
`complementary_focus = true`; the dataclass field default and the weighted-vs-lexicographic
rewrite are chosen to keep existing golden snapshots stable, **except** for a small set of
selection tie-break tests that Phase 2 explicitly re-baselines (the same kind of re-baseline the
prior taxonomy work did when it dropped the `-ex.id` tiebreaker).

## 6. Smart complementation (`complementation.py`)

A small module that answers "what is this session missing?":

- `coverage_deficit(ex, coverage) -> float` — higher when the exercise's primary muscles are the
  least-covered so far in the session. Drives the `complementary_coverage` feature.
- `is_core(ex) -> bool` and antagonist grouping (push↔pull, quad↔hinge, etc.) so accessory slots
  that the template marks generically can gravitate to genuine balance + core when
  `complementary_focus` is on.

This is what turns "focus upper body" into "upper-body primary + balanced pull/rear-delt/core
accessories" rather than five pressing variations. It only re-weights within a slot's already-legal
pool — it never overrides a template's explicit slot pattern/region.

## 7. Enhanced template matching (`matching.py`)

Expand the 4-factor weighted score to a richer, still-deterministic model behind a protocol:

```python
@dataclass(frozen=True)
class MatchWeights:
    goal: float = 0.25
    experience: float = 0.20
    days: float = 0.12
    duration: float = 0.08
    movement_preference: float = 0.15   # NEW
    focus_complement: float = 0.12      # NEW
    periodization: float = 0.08         # NEW

class TemplateScorer(Protocol):
    def score(self, features: dict[str, float]) -> float: ...
```

New factors:
- **movement_preference** — how well the template's dominant equipment (inferred from its slot
  patterns / feasible exercises) aligns with the user's preferred families.
- **focus_complement** — reward templates whose structure supports the user's focus +
  complementary intent (a balanced split scores higher for `complementary_focus` users than a
  single-region template; a pure-focus template scores higher when complementary is off).
- **periodization** — reward templates whose native `progression_ref.model_key` aligns with the
  user's `progression_style` (`consistent`↔linear/double, `variable`↔undulating).

Equipment feasibility stays a **gate** (infeasible templates excluded). `MatchInput` gains
`movement_preferences`, `complementary_focus`, `progression_style`. Feature extraction is a pure
function; `HeuristicTemplateScorer` applies the weights. Output stays "ranked top-3 + per-factor
breakdown" so the existing "why this fits" UI keeps working (now with more factors).

## 8. Week-to-week variety (`variety.py` + `preview.py`)

Today the base week is stored once and every week derives identical exercises (only load/reps
progress). To add controlled variety:

- At draft time, for **eligible slots** (non-primary / accessory scheme), compute a small
  **rotation pool** — the top-N scoring exercises for that slot (N by variety level:
  `low`→1, `medium`→2, `high`→3) — and store the pool's exercise ids on
  `WorkoutExercise.rotation_pool` (new JSON column, default `[]`).
- **Primary/main-scheme slots never rotate** — progression needs a stable lift to load week over
  week. Their pool is always the single chosen exercise.
- `preview.derive_week` picks `rotation_pool[(week - 1) % len(pool)]` for eligible slots when a
  pool has >1 entry; otherwise uses the stored `exercise_id` (today's exact behavior).
- Rotation is **deterministic** (pure function of week index) so golden-file snapshots stay stable.

Storage cost is tiny (a short id list per slot) and re-adaptation still edits the base week once.

## 9. ML-ready seams (summary)

| Seam | Protocol | MVP impl | Future impl |
|------|----------|----------|-------------|
| Template ranking | `TemplateScorer` | `HeuristicTemplateScorer` (weights) | `LearnedTemplateScorer` |
| Exercise ranking | `ExerciseScorer` | `HeuristicExerciseScorer` (weights) | `LearnedExerciseScorer` |
| Feature extraction | pure `extract_*_features` fns | hand-built dicts | same dicts → model input |

No learned models ship in the MVP; the protocols + feature functions are the only forward
investment.

## 10. Data model & migrations

- **No new tables.** New per-program signals live in `WorkoutProgram.constraints` (JSON) — no
  schema change.
- **One column:** `workout_exercises.rotation_pool` (JSON, nullable/default `[]`) for §8. New
  reversible Alembic migration.
- Optional future: profile-level preference defaults (`user_profiles`) — **deferred**, not in this
  plan.

## 11. Endpoint wiring

- `ProgramCreationRequest` / `MatchRequest` / `DraftRequest` gain `movement_preferences`,
  `complementary_focus`, `variety_preference` (all optional with today's defaults).
- `_ctx_for` populates the new `SelectionContext` fields from the request + profile.
- `rank_templates` receives the enriched `MatchInput`.
- `build_draft` stores the signals in `constraints`, builds rotation pools, and updates coverage
  trackers.
- `derive_week` applies rotation from stored pools + constraints.

Every addition is backward compatible: omitting the new fields reproduces today's exact output, so
existing `test_matching`, `test_selection`, `test_drafting`, `test_preview`, and API-schema tests
keep passing except where a task explicitly extends them.

## 12. Phasing

1. **Signals & schema** — enums, request/constraints fields, `rotation_pool` column + migration,
   `preferences.py` equipment-family map. (Foundational, no behavior change yet.)
2. **Selection depth** — `SelectionWeights`, `ExerciseScorer`, weighted rewrite, movement-preference
   feature. Ship the biggest quality lever first.
3. **Complementation** — `complementation.py`, coverage tracking, complementary-coverage feature.
4. **Matching depth** — `MatchWeights`, `TemplateScorer`, three new factors.
5. **Week-to-week variety** — rotation pools at draft, rotation in preview.
6. **Frontend + docs** — collect the three signals in the wizard; surface rotation + "why this
   fits" in preview; author the user + technical HTML docs (§15) rendering the §14 algorithm
   reference.

Each phase is independently shippable and independently testable (TDD, golden-file snapshots for
determinism, >80% coverage).

## 13. Performance

All computation is in-memory over ~148 exercises and a handful of templates, with one cacheable
exercise-library read. The added scoring is O(candidates × features) per slot — still well under
the 500 ms budget (and comfortably under the prior <100 ms in practice).

## 14. Algorithm reference (diagrams + formulas)

This section is the canonical algorithm specification. It is the source material for the
technical HTML doc (§15) and must be kept in sync with the implementation.

### 14.1 End-to-end pipeline

```
 user profile + environment + wizard signals
                    │
                    ▼
        ┌───────────────────────┐
        │  1. MATCH             │   score every active template
        │  (matching.py)        │   feasibility gate → rank → top 3
        └───────────┬───────────┘
                    │ user picks one template
                    ▼
        ┌───────────────────────┐
        │  2. DRAFT             │   per session, per slot:
        │  (drafting.py)        │   filter pool → score → pick
        │   ├ selection.py      │   build rotation pools (eligible slots)
        │   └ complementation.py│   update coverage / variety trackers
        └───────────┬───────────┘
                    │ base week persisted once
                    ▼
        ┌───────────────────────┐
        │  3. DERIVE / PREVIEW  │   for week w = 1..N:
        │  (preview.py)         │   apply progression model + rotation
        └───────────────────────┘
```

### 14.2 Template matching

**Feasibility gate (hard).** A template `T` is eligible only if every slot can be filled by at
least one exercise given the environment equipment `E`:

```
feasible(T, E) = ∀ slot s ∈ T :  ∃ exercise x :
                     matches_rule(x, s) ∧ equipment_tags(x) ⊆ E
```

Infeasible templates are dropped before scoring (they never appear in results).

**Match score (soft).** For each feasible template, a weighted linear combination of normalized
per-factor scores in `[0, 1]`:

```
match(T) = Σ_k  w_k · f_k(T)          where  Σ_k w_k = 1
```

| Factor `f_k` | Formula | Weight `w_k` |
|--------------|---------|--------------|
| `goal` | `1` if `user.fitness_focus ∈ T.goals` else `0` | 0.25 |
| `experience` | `1` if `user.experience ∈ T.experience_levels` else `0.3` | 0.20 |
| `days` | `range_fit(days, T.days_min, T.days_max)` | 0.12 |
| `duration` | `range_fit(dur, T.dur_min, T.dur_max)` | 0.08 |
| `movement_preference` | mean preferred-family weight of `T`'s dominant equipment, normalized | 0.15 |
| `focus_complement` | `1` if `T`'s split structure matches the user's focus + complementary intent, graded otherwise | 0.12 |
| `periodization` | `1` if `T.progression.model_key` aligns with `user.progression_style`, else `0.3` | 0.08 |

**Range fit** (used for days & duration) linearly penalizes distance outside the template's band:

```
range_fit(v, lo, hi) = 1                              if lo ≤ v ≤ hi
                     = max(0, 1 − dist / max(lo, 1))  otherwise
                       where dist = (lo − v) if v < lo else (v − hi)
```

Result: `fit_pct = round(match(T) · 100)`, sorted descending, top 3 returned with the per-factor
`factors` dict powering the "why this fits" UI.

### 14.3 Exercise selection (per slot)

```
        candidates (full exercise library)
                    │
          ┌─────────▼──────────┐
          │  HARD FILTERS      │   drop if any fails:
          │                    │   • equipment_tags(x) ⊄ E
          │                    │   • difficulty(x) > exp + tolerance
          │                    │   • contraindications(x) ∩ injuries ≠ ∅
          │                    │   • x ∈ excluded_ids
          └─────────┬──────────┘
                    │ (locked slot short-circuits to the locked exercise)
          pool empty? ──yes──▶ relax difficulty tolerance → retry → else None
                    │ no
          ┌─────────▼──────────┐
          │  WEIGHTED SCORE    │   score(x) = Σ wᵢ · featureᵢ(x)
          └─────────┬──────────┘
                    ▼
              argmax → chosen
```

**Filters are boolean gates**; only exercises passing all of them are scored. The locked-slot and
empty-pool-fallback paths are unchanged from today.

**Selection score.** A weighted sum of normalized features in `[0, 1]`:

```
score(x) = w_variety      · variety(x)
         + w_priority      · priority_fit(x)
         + w_muscle        · muscle_fit(x)
         + w_difficulty    · difficulty(x)
         + w_unilateral    · unilateral_balance(x)
         + w_movement      · movement_pref(x)          ← NEW
         + w_complement    · complementary_coverage(x)  ← NEW
```

Default weights (`SelectionWeights`): variety `1.0`, priority_fit `1.5`, muscle_fit `1.0`,
difficulty `0.75`, unilateral_balance `0.5`, movement_preference `1.25`,
complementary_coverage `1.25`.

| Feature | Definition (normalized to `[0,1]`) |
|---------|-----------------------------------|
| `variety(x)` | `1` if `movement_slug(x)` unused in this program, else `0` |
| `priority_fit(x)` | `1` if `(slot.priority == primary) == is_compound(x)`, else `0` |
| `muscle_fit(x)` | `|slot.muscles ∩ primary_muscles(x)| / max(1, |slot.muscles|)` |
| `difficulty(x)` | `1 − |lvl(x) − lvl(user)| / 2` (levels: beginner 0, intermediate 1, advanced 2) |
| `unilateral_balance(x)` | `0` if `is_unilateral(x)` equals the previous pick's, else `1` |
| `movement_pref(x)` | `max_family_weight(x, prefs) / 2` (families weighted `0..2`; neutral 1 → 0.5) |
| `complementary_coverage(x)` | `deficit(primary_muscles(x), session_coverage)`; higher when x hits the least-covered muscles. Neutral (`0.5`) for primary slots. |

**Movement preference weight** — coarse family axis, `max` over the exercise's tags so a mostly
preferred lift is not dragged down by an incidental tag:

```
max_family_weight(x, prefs) = max{ prefs[family(tag)] : tag ∈ equipment_tags(x) }
                              (default 1.0 when prefs empty or family unlisted)
```

**Complementary coverage deficit** — for non-primary slots when `complementary_focus` is on,
let `coverage[m]` be the running count of slots already hitting muscle `m` in the session:

```
deficit(M, coverage) = 1 − ( mean_{m ∈ M} coverage[m] ) / ( 1 + max_m coverage[m] )
```

This rewards exercises that train currently under-trained muscles (antagonists, rear delts, core),
so "focus upper" resolves to a balanced session rather than repeated presses — **without** ever
overriding a slot's explicit pattern/region rule (it only re-orders within the legal pool).

### 14.4 Week-to-week variety (derivation)

For eligible (non-main) slots the drafter stores a `rotation_pool` of the top-`N` scoring
exercises, `N = {low:1, medium:2, high:3}`. Derivation is a pure function of the week index:

```
exercise_for(slot, week) = rotation_pool[(week − 1) mod len(pool)]   if len(pool) > 1
                         = slot.exercise_id                          otherwise
```

Main/primary slots always have `len(pool) == 1`, so the progression model always loads a stable
lift. Determinism keeps golden-file snapshots valid.

## 15. Documentation deliverables (build during Phase 6, not now)

Two HTML docs are produced when the engine work lands, following the `documentation` skill's
templates and themes. **They are deferred to Phase 6** — this spec section defines their scope so
they aren't forgotten:

- **User doc** — `docs/user/PROGRAM_GENERATION.html` (navy theme). Plain-language: what "movement
  preferences", "complementary focus", and "variety" do; how choices change the resulting program;
  no formulas. Analogy-driven ("we favor your preferred equipment but still mix in what balances
  your body").
- **Technical doc** — `docs/technical/WORKOUT_PROGRAMS_TECHNICAL.html` (blue theme). Renders §14
  verbatim: pipeline diagram, feasibility gate, both weighted-score formulas, feature tables,
  rotation formula, the `TemplateScorer`/`ExerciseScorer` protocol seams, file paths
  (`matching.py`, `selection.py`, `complementation.py`, `preferences.py`, `variety.py`,
  `preview.py`), and worked numeric examples. Update both section indexes and `docs/README.md`.

The §14 reference here is the single source of truth; the technical HTML is its rendered form.
