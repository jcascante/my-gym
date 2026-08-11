# Template-Defined Program Duration

## Problem

`duration_weeks` is not a property of a program template today — it's a `MatchRequest`
schema default (`= 8`) that flows unchanged into every generated `WorkoutProgram`, and
is independently re-hardcoded in the frontend (`ProgramBuilderPage.tsx:63`). The builder
UI never actually exposes a duration input; every program is silently 8 weeks long
regardless of which template generated it.

`ProgramTemplate` already varies meaningfully by progression model and deload cadence
(e.g. Push/Pull/Legs deloads every 6 weeks, most other templates every 4-5), which
implies templates have different natural program lengths. There's currently no way to
express that.

## Goals

- Let each `ProgramTemplate` define a default duration and a valid min/max range.
- Let the user express a duration preference up front (Preferences step), independent
  of which template they end up picking.
- Validate the requested duration against the *chosen* template's range at draft time.
- Surface each template's duration range in the template browser, consistent with how
  `days_per_week` and `session_duration` ranges are already shown.

## Non-goals

- Duration does **not** become a template-matching/scoring factor. `/match` behavior is
  unchanged; only `/draft`-time validation and display are affected.
- No fix to the existing `days_per_week`/`session_duration` "3-3" range-display quirk
  (pre-existing, unrelated to this work).
- No changes to `ProgramCreationForm.tsx` — grepped and confirmed unused anywhere in the
  app; `ProgramWizardStep1.tsx` is the live form component.

## Data model

Add three non-nullable columns to `ProgramTemplate`
(`backend/app/models/program.py`), mirroring the existing `days_per_week_min/max`
pattern:

```python
duration_weeks_default: Mapped[int] = mapped_column(Integer, nullable=False)
duration_weeks_min: Mapped[int] = mapped_column(Integer, nullable=False)
duration_weeks_max: Mapped[int] = mapped_column(Integer, nullable=False)
```

### Migration

New Alembic revision, following the existing two-step add-then-backfill-then-not-null
pattern used in `9f1a2b3c4d5e_backfill_start_date_on_workout_programs.py`:

1. Add the three columns as nullable.
2. Backfill every existing `program_templates` row via the seed data values below (the
   seed script re-running via `seed_program_templates` also keeps rows in sync going
   forward, since it upserts by slug).
3. Alter columns to `nullable=False`.

Downgrade drops the three columns.

### Seed data values

`backend/app/db/seed/program_templates.py` — each entry gets
`duration_weeks_default/min/max` added, chosen from the template's
`progression_ref.deload_every` cadence where present (roughly 2 deload cycles for
`default`, 1 cycle for `min`, 3 cycles for `max`), and from goal/experience for
templates with no `deload_every`:

| Template (slug) | Progression | default | min | max |
|---|---|---|---|---|
| full-body-x3 | linear_load, deload 4 | 8 | 4 | 12 |
| bodyweight-full-body-x3 | double_progression | 8 | 4 | 12 |
| upper-lower-x4 | double_progression, deload 4 | 8 | 4 | 12 |
| push-pull-legs-x6 | double_progression, deload 6 | 12 | 6 | 18 |
| full-body-x2 | double_progression | 8 | 4 | 12 |
| full-body-endurance-x3 | double_progression | 8 | 4 | 12 |
| full-body-undulating-x3 | weekly_undulating, deload 4 | 8 | 4 | 12 |
| upper-lower-advanced-x4 | linear_load, deload 4 | 8 | 4 | 12 |
| body-part-split-x5 | double_progression, deload 5 | 10 | 5 | 15 |
| powerlifting-strength-x4 | linear_load, deload 4 (peaking) | 12 | 8 | 16 |

## Backend API

- `MatchRequest.duration_weeks` (`backend/app/schemas/program_api.py:15`) loses its
  `= 8` default and becomes a required field. `/match` behavior is otherwise unchanged
  — duration is accepted but not used in scoring.
- `TemplateOut` (`backend/app/schemas/template.py:72`) gains
  `duration_weeks_default: int`, `duration_weeks_min: int`, `duration_weeks_max: int`.
  Since this schema's fields are read directly off the ORM object, no extra wiring is
  needed beyond adding the fields.
- `/draft` endpoint (`backend/app/api/v1/endpoints/programs.py:230`): immediately after
  loading `template` (line 240-242, where `ProgramTemplateNotFoundError` is already
  raised for a missing/inactive template), validate:

  ```python
  if not (template.duration_weeks_min <= data.duration_weeks <= template.duration_weeks_max):
      raise ValidationError(
          f"duration_weeks must be between {template.duration_weeks_min} and "
          f"{template.duration_weeks_max} for this template"
      )
  ```

  This follows the existing `ValidationError` pattern (`app/core/exceptions.py:52`,
  already used in `services/program/adaptation.py:76`), which maps to a 422 response.

## Frontend

- `frontend/src/types/template.ts` — `Template` interface gains
  `duration_weeks_default: number`, `duration_weeks_min: number`,
  `duration_weeks_max: number`.
- `frontend/src/types/programCreation.ts` — `MatchRequest` interface gains
  `duration_weeks: number`.
- `frontend/src/components/ProgramWizardStep1.tsx` — new `FormField` ("Program Duration
  (weeks)", type number, name `duration_weeks`), placed directly after the Session
  Duration field. State defaults to `'8'`, mirrors the existing `sessionDurationMin`
  state/handler pattern exactly (including the `initialValues` restore in the
  `useEffect`). Client-side bounds: `min="1" max="52"`.
- `frontend/src/pages/ProgramBuilderPage.tsx:63` — `duration_weeks: values.duration_weeks`
  replaces the hardcoded `8`.
- `frontend/src/components/TemplateListItem.tsx`:
  - Compact summary line (currently `"{levels} • {goals} • {days} days/week • {session} min"`)
    gains a trailing `• {duration} weeks` segment.
  - Expanded "Configuration" grid gains a fifth tile, "Duration", alongside the existing
    "Days Per Week" and "Session Duration" tiles.
  - Both use a small local formatting helper: `min === max ? `${min} weeks` : `${min}-${max} weeks`` —
    scoped to this new field only, not applied to the existing days/session displays.

### Error handling

A 422 from `/draft` on an out-of-range duration flows through the same error-handling
path `ProgramBuilderPage.tsx` already uses for other draft-creation failures (e.g.
required-inputs validation) — no new UI component. The user navigates back via the
existing `handleBack` stepper control to the Preferences step to adjust the duration
value (or picks a different template whose range fits).

## Testing

- Backend: migration up/down test (columns present, `NOT NULL` enforced,
  downgrade removes them cleanly).
- Backend: `/draft` returns 422 with the expected message when `duration_weeks` is
  outside the chosen template's range; succeeds at the boundary values (`min`, `max`).
- Backend: `/match` still succeeds without `duration_weeks` affecting result ordering
  (existing scoring tests should be unaffected — confirms non-goal held).
- Backend: `TemplateOut` serialization includes the three new fields.
- Frontend: `ProgramWizardStep1` renders the duration field, defaults to `8`, submits
  the entered value.
- Frontend: `TemplateListItem` renders `"8 weeks"` for a fixed-duration template and
  `"6-12 weeks"` for a ranged one, in both the compact and expanded views.
