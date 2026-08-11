# Template-Defined Program Duration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let each `ProgramTemplate` define its own duration default/min/max instead of every program being hardcoded to 8 weeks, validate the user's requested duration against the chosen template at draft time, and surface duration in the builder UI and template browser.

**Architecture:** Add three columns to `ProgramTemplate` (`duration_weeks_default/min/max`), backfill via migration + seed data, drop the schema-level default on `MatchRequest.duration_weeks` (now sourced from a real user input), validate the requested value against the chosen template's range in the `/draft` endpoint, and thread a new "Program Duration" field through the builder's Preferences step and the template browser's display.

**Tech Stack:** FastAPI + SQLAlchemy + Alembic + pytest (backend), React + TypeScript + Vitest/RTL (frontend).

## Global Constraints

- Duration is **not** a template-matching/scoring factor — `/match` behavior and its scoring tests must be unaffected.
- Out-of-range `duration_weeks` at `/draft` time is a **hard rejection** (422), never a silent clamp.
- No changes to `ProgramCreationForm.tsx` (dead code, unused anywhere in the app).
- No changes to the existing `days_per_week`/`session_duration` "min-max" display behavior — the new duration display's collapse-when-equal formatting applies only to the new field.
- Spec: `docs/superpowers/specs/2026-08-05-template-duration-weeks-design.md`

---

### Task 1: `ProgramTemplate` duration columns — migration and model

**Files:**
- Create: `backend/alembic/versions/d1fcbf156087_add_duration_weeks_range_to_program_templates.py`
- Modify: `backend/app/models/program.py:41` (inside `ProgramTemplate`, after `session_duration_max`)
- Test: `backend/tests/test_program_models.py`

**Interfaces:**
- Produces: `ProgramTemplate.duration_weeks_default: int`, `ProgramTemplate.duration_weeks_min: int`, `ProgramTemplate.duration_weeks_max: int` — used by Task 2 (seed data), Task 4 (`TemplateOut`), and Task 5 (`/draft` validation).

- [ ] **Step 1: Write the failing test for the model defaults**

Add to `backend/tests/test_program_models.py` (new test, after `test_workout_exercise_rotation_pool_defaults_to_empty_list`):

```python
@pytest.mark.asyncio
async def test_program_template_duration_fields_default_when_omitted(db_session: AsyncSession):
    template = ProgramTemplate(
        name="Duration Default Test",
        slug="duration-default-test",
        description="",
        goals=["general"],
        experience_levels=["beginner"],
        days_per_week_min=3,
        days_per_week_max=3,
        session_duration_min=45,
        session_duration_max=60,
        split={"sessions": []},
        progression_ref={"model_key": "linear_load", "params": {}},
        required_inputs=[],
    )
    db_session.add(template)
    await db_session.commit()
    await db_session.refresh(template)

    assert template.duration_weeks_default == 8
    assert template.duration_weeks_min == 4
    assert template.duration_weeks_max == 12
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `docker compose exec backend uv run pytest tests/test_program_models.py::test_program_template_duration_fields_default_when_omitted -v`
Expected: FAIL with `sqlite3.IntegrityError` / `NotNullViolation` (or a `TypeError` if the columns don't exist yet) — the columns don't exist on `ProgramTemplate` yet.

- [ ] **Step 3: Add the columns to the model**

In `backend/app/models/program.py`, inside `class ProgramTemplate`, right after the `session_duration_max` line:

```python
    session_duration_min: Mapped[int] = mapped_column(Integer, nullable=False)
    session_duration_max: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_weeks_default: Mapped[int] = mapped_column(Integer, nullable=False, default=8)
    duration_weeks_min: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    duration_weeks_max: Mapped[int] = mapped_column(Integer, nullable=False, default=12)
```

- [ ] **Step 4: Write the migration**

Create `backend/alembic/versions/d1fcbf156087_add_duration_weeks_range_to_program_templates.py`:

```python
"""add duration_weeks range to program templates

Revision ID: d1fcbf156087
Revises: c3d9f7a1b5e8
Create Date: 2026-08-05 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d1fcbf156087"
down_revision: Union[str, None] = "c3d9f7a1b5e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (default, min, max) per template slug - see docs/superpowers/specs/2026-08-05-template-duration-weeks-design.md
DURATION_WEEKS_BY_SLUG = {
    "full-body-x3": (8, 4, 12),
    "bodyweight-full-body-x3": (8, 4, 12),
    "upper-lower-x4": (8, 4, 12),
    "push-pull-legs-x6": (12, 6, 18),
    "full-body-x2": (8, 4, 12),
    "full-body-endurance-x3": (8, 4, 12),
    "full-body-undulating-x3": (8, 4, 12),
    "upper-lower-advanced-x4": (8, 4, 12),
    "body-part-split-x5": (10, 5, 15),
    "powerlifting-strength-x4": (12, 8, 16),
}


def upgrade() -> None:
    op.add_column(
        "program_templates",
        sa.Column("duration_weeks_default", sa.Integer(), nullable=False, server_default="8"),
    )
    op.add_column(
        "program_templates",
        sa.Column("duration_weeks_min", sa.Integer(), nullable=False, server_default="4"),
    )
    op.add_column(
        "program_templates",
        sa.Column("duration_weeks_max", sa.Integer(), nullable=False, server_default="12"),
    )
    connection = op.get_bind()
    for slug, (default, minimum, maximum) in DURATION_WEEKS_BY_SLUG.items():
        connection.execute(
            sa.text(
                "UPDATE program_templates SET duration_weeks_default = :default, "
                "duration_weeks_min = :minimum, duration_weeks_max = :maximum WHERE slug = :slug"
            ),
            {"default": default, "minimum": minimum, "maximum": maximum, "slug": slug},
        )
    op.alter_column("program_templates", "duration_weeks_default", server_default=None)
    op.alter_column("program_templates", "duration_weeks_min", server_default=None)
    op.alter_column("program_templates", "duration_weeks_max", server_default=None)


def downgrade() -> None:
    op.drop_column("program_templates", "duration_weeks_max")
    op.drop_column("program_templates", "duration_weeks_min")
    op.drop_column("program_templates", "duration_weeks_default")
```

- [ ] **Step 5: Apply the migration**

Run: `docker compose exec backend uv run alembic upgrade head`
Expected: migration `d1fcbf156087` applies with no errors.

- [ ] **Step 6: Run the test to verify it passes**

Run: `docker compose exec backend uv run pytest tests/test_program_models.py::test_program_template_duration_fields_default_when_omitted -v`
Expected: PASS

- [ ] **Step 7: Verify the migration downgrades cleanly**

Run: `docker compose exec backend uv run alembic downgrade -1 && docker compose exec backend uv run alembic upgrade head`
Expected: both commands succeed with no errors, leaving the DB back at head.

- [ ] **Step 8: Commit**

```bash
git add backend/app/models/program.py backend/alembic/versions/d1fcbf156087_add_duration_weeks_range_to_program_templates.py backend/tests/test_program_models.py
git commit -m "feat: add duration_weeks range columns to program_templates"
```

---

### Task 2: Seed per-template duration values

**Files:**
- Modify: `backend/app/db/seed/program_templates.py` (10 insertions, one per template entry)
- Test: `backend/tests/test_seed_templates.py`

**Interfaces:**
- Consumes: `ProgramTemplate.duration_weeks_default/min/max` (Task 1).
- Produces: every seeded `ProgramTemplate` row has real, template-specific duration values — consumed by Task 4 (`TemplateOut` responses) and Task 5 (`/draft` validation).

- [ ] **Step 1: Write the failing test**

Replace `backend/tests/test_seed_templates.py` with:

```python
import pytest
from sqlalchemy import select

from app.db.seed.seed_program_templates import seed_program_templates
from app.models import ProgramTemplate
from app.schemas.template import TemplateDefinition


@pytest.mark.asyncio
async def test_seed_inserts_and_is_idempotent(db_session):
    await seed_program_templates(db_session)
    await seed_program_templates(db_session)  # second run must not duplicate
    rows = (await db_session.execute(select(ProgramTemplate))).scalars().all()
    slugs = {r.slug for r in rows}
    assert {"full-body-x3", "upper-lower-x4", "push-pull-legs-x6", "bodyweight-full-body-x3"} <= slugs
    for r in rows:
        TemplateDefinition.from_orm_template(r)  # every seed parses cleanly


@pytest.mark.asyncio
async def test_seed_sets_duration_weeks_range_per_template(db_session):
    await seed_program_templates(db_session)
    rows = (await db_session.execute(select(ProgramTemplate))).scalars().all()
    by_slug = {r.slug: r for r in rows}

    full_body = by_slug["full-body-x3"]
    assert (full_body.duration_weeks_min, full_body.duration_weeks_default, full_body.duration_weeks_max) == (
        4,
        8,
        12,
    )

    ppl = by_slug["push-pull-legs-x6"]
    assert (ppl.duration_weeks_min, ppl.duration_weeks_default, ppl.duration_weeks_max) == (6, 12, 18)

    for r in rows:
        assert r.duration_weeks_min <= r.duration_weeks_default <= r.duration_weeks_max
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `docker compose exec backend uv run pytest tests/test_seed_templates.py::test_seed_sets_duration_weeks_range_per_template -v`
Expected: FAIL — `full_body.duration_weeks_min` etc. are the Task 1 model defaults (`4, 8, 12`), so the `full-body-x3` assertion actually already passes, but the `push-pull-legs-x6` assertion fails because it still has the generic model default `(4, 8, 12)` instead of `(6, 12, 18)`.

- [ ] **Step 3: Add duration fields to each of the 10 seed entries**

In `backend/app/db/seed/program_templates.py`, insert three keys immediately after each entry's `"session_duration_max"` line:

`full-body-x3` (after line 11, `"session_duration_max": 60,`):
```python
        "session_duration_max": 60,
        "duration_weeks_default": 8,
        "duration_weeks_min": 4,
        "duration_weeks_max": 12,
```

`bodyweight-full-body-x3` (after line 87, `"session_duration_max": 45,`):
```python
        "session_duration_max": 45,
        "duration_weeks_default": 8,
        "duration_weeks_min": 4,
        "duration_weeks_max": 12,
```

`upper-lower-x4` (after line 155, `"session_duration_max": 75,`):
```python
        "session_duration_max": 75,
        "duration_weeks_default": 8,
        "duration_weeks_min": 4,
        "duration_weeks_max": 12,
```

`push-pull-legs-x6` (after line 257, `"session_duration_max": 75,`):
```python
        "session_duration_max": 75,
        "duration_weeks_default": 12,
        "duration_weeks_min": 6,
        "duration_weeks_max": 18,
```

`full-body-x2` (after line 382, `"session_duration_max": 45,`):
```python
        "session_duration_max": 45,
        "duration_weeks_default": 8,
        "duration_weeks_min": 4,
        "duration_weeks_max": 12,
```

`full-body-endurance-x3` (after line 439, `"session_duration_max": 45,`):
```python
        "session_duration_max": 45,
        "duration_weeks_default": 8,
        "duration_weeks_min": 4,
        "duration_weeks_max": 12,
```

`full-body-undulating-x3` (after line 507, `"session_duration_max": 60,`):
```python
        "session_duration_max": 60,
        "duration_weeks_default": 8,
        "duration_weeks_min": 4,
        "duration_weeks_max": 12,
```

`upper-lower-advanced-x4` (after line 594, `"session_duration_max": 90,`):
```python
        "session_duration_max": 90,
        "duration_weeks_default": 8,
        "duration_weeks_min": 4,
        "duration_weeks_max": 12,
```

`body-part-split-x5` (after line 696, `"session_duration_max": 90,`):
```python
        "session_duration_max": 90,
        "duration_weeks_default": 10,
        "duration_weeks_min": 5,
        "duration_weeks_max": 15,
```

`powerlifting-strength-x4` (after line 809, `"session_duration_max": 90,`):
```python
        "session_duration_max": 90,
        "duration_weeks_default": 12,
        "duration_weeks_min": 8,
        "duration_weeks_max": 16,
```

Since several entries share the same `"session_duration_max"` value, locate each insertion point by the `"slug"` a few lines above it, not by the value alone.

- [ ] **Step 4: Run the seed against a real DB and the tests**

Run: `docker compose exec backend uv run python -m app.db.seed.seed_program_templates`
Expected: completes with no errors (upserts by slug, so safe to re-run).

Run: `docker compose exec backend uv run pytest tests/test_seed_templates.py -v`
Expected: PASS (both tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/db/seed/program_templates.py backend/tests/test_seed_templates.py
git commit -m "feat: seed per-template duration_weeks ranges"
```

---

### Task 3: `MatchRequest.duration_weeks` becomes required

**Files:**
- Modify: `backend/app/schemas/program_api.py:15`
- Modify: `backend/tests/test_program_api_schemas.py:7-8` (`_base_kwargs`)

**Interfaces:**
- Consumes: none new.
- Produces: `MatchRequest`/`DraftRequest` now require an explicit `duration_weeks: int` (no default) — every caller (API clients, tests) must supply it explicitly.

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_program_api_schemas.py`, after `test_match_request_defaults`:

```python
def test_match_request_requires_duration_weeks():
    with pytest.raises(ValidationError):
        MatchRequest(environment_id=1, days_per_week=3, session_duration_min=60, fitness_focus="strength")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `docker compose exec backend uv run pytest tests/test_program_api_schemas.py::test_match_request_requires_duration_weeks -v`
Expected: FAIL — `duration_weeks` currently defaults to `8`, so no `ValidationError` is raised.

- [ ] **Step 3: Remove the default**

In `backend/app/schemas/program_api.py`, in `class MatchRequest`:

```python
class MatchRequest(BaseModel):
    environment_id: int
    days_per_week: int
    session_duration_min: int
    fitness_focus: str
    weight_unit: str = "kg"
    duration_weeks: int
    progression_style: ProgressionStyle = ProgressionStyle.CONSISTENT
```

- [ ] **Step 4: Fix the now-broken `_base_kwargs()` test helper**

In `backend/tests/test_program_api_schemas.py`:

```python
def _base_kwargs():
    return dict(
        environment_id=1,
        days_per_week=3,
        session_duration_min=60,
        fitness_focus="strength",
        duration_weeks=8,
    )
```

- [ ] **Step 5: Run the full schema test file**

Run: `docker compose exec backend uv run pytest tests/test_program_api_schemas.py -v`
Expected: PASS (all tests, including the new one and the five `_base_kwargs()`-based tests that previously relied on the removed default).

- [ ] **Step 6: Run the full backend suite to catch any other caller**

Run: `docker compose exec backend uv run pytest -v`
Expected: PASS. (All `/match` and `/draft` calls in `test_programs_flow.py` already pass `"duration_weeks": 8` explicitly in their JSON bodies, so they're unaffected.)

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas/program_api.py backend/tests/test_program_api_schemas.py
git commit -m "feat: require duration_weeks on MatchRequest instead of defaulting to 8"
```

---

### Task 4: Expose duration range on `TemplateOut`

**Files:**
- Modify: `backend/app/schemas/template.py:72-86` (`TemplateOut`)
- Modify: `backend/app/api/v1/endpoints/templates.py:25-38`
- Create: `backend/tests/test_templates_endpoint.py`

**Interfaces:**
- Consumes: `ProgramTemplate.duration_weeks_default/min/max` (Task 1), seeded values (Task 2).
- Produces: `GET /api/v1/templates` response items include `duration_weeks_default`, `duration_weeks_min`, `duration_weeks_max` — consumed by the frontend `Template` type (Task 8).

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_templates_endpoint.py`:

```python
import pytest


@pytest.mark.asyncio
async def test_list_templates_includes_duration_weeks_range(
    client, auth_headers, seeded_templates
):
    r = await client.get("/api/v1/templates", headers=auth_headers)
    assert r.status_code == 200
    templates = r.json()["templates"]
    full_body = next(t for t in templates if t["slug"] == "full-body-x3")
    assert full_body["duration_weeks_default"] == 8
    assert full_body["duration_weeks_min"] == 4
    assert full_body["duration_weeks_max"] == 12
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `docker compose exec backend uv run pytest tests/test_templates_endpoint.py -v`
Expected: FAIL with a `KeyError: 'duration_weeks_default'` — the response doesn't include the field yet.

- [ ] **Step 3: Add the fields to `TemplateOut`**

In `backend/app/schemas/template.py`, in `class TemplateOut`:

```python
class TemplateOut(BaseModel):
    """Response schema for a single template in list view."""

    slug: str
    name: str
    description: str
    goals: list[str]
    experience_levels: list[str]
    days_per_week_min: int
    days_per_week_max: int
    session_duration_min: int
    session_duration_max: int
    duration_weeks_default: int
    duration_weeks_min: int
    duration_weeks_max: int
    split: dict[str, Any]
    progression_ref: dict[str, Any]
    required_inputs: list[dict[str, Any]]
```

- [ ] **Step 4: Populate the fields in the endpoint**

In `backend/app/api/v1/endpoints/templates.py`:

```python
            TemplateOut(
                slug=t.slug,
                name=t.name,
                description=t.description,
                goals=t.goals,
                experience_levels=t.experience_levels,
                days_per_week_min=t.days_per_week_min,
                days_per_week_max=t.days_per_week_max,
                session_duration_min=t.session_duration_min,
                session_duration_max=t.session_duration_max,
                duration_weeks_default=t.duration_weeks_default,
                duration_weeks_min=t.duration_weeks_min,
                duration_weeks_max=t.duration_weeks_max,
                split=t.split,
                progression_ref=t.progression_ref,
                required_inputs=t.required_inputs,
            )
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `docker compose exec backend uv run pytest tests/test_templates_endpoint.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/template.py backend/app/api/v1/endpoints/templates.py backend/tests/test_templates_endpoint.py
git commit -m "feat: expose duration_weeks range on the templates list endpoint"
```

---

### Task 5: Validate `duration_weeks` against the chosen template at `/draft`

**Files:**
- Modify: `backend/app/api/v1/endpoints/programs.py:240-243`
- Test: `backend/tests/test_programs_flow.py`

**Interfaces:**
- Consumes: `ProgramTemplate.duration_weeks_min/max` (Task 1, Task 2), `app.core.ValidationError` (existing, `backend/app/core/exceptions.py:52`).
- Produces: `/draft` returns 422 with `{"detail": "duration_weeks must be between {min} and {max} for this template", "error_code": "VALIDATION_ERROR"}` when out of range.

- [ ] **Step 1: Write the failing tests**

Add to `backend/tests/test_programs_flow.py`, after `test_draft_requires_start_date`:

```python
@pytest.mark.asyncio
async def test_draft_rejects_duration_outside_template_range(
    client, auth_headers, seeded_templates, seeded_exercises, user_environment, db_session
):
    from sqlalchemy import select

    from app.models import ProgramTemplate

    template_id = (
        await db_session.execute(select(ProgramTemplate.id).where(ProgramTemplate.slug == "full-body-x3"))
    ).scalar_one()

    draft_body = {
        "environment_id": user_environment.id,
        "days_per_week": 3,
        "session_duration_min": 60,
        "fitness_focus": "strength",
        "weight_unit": "kg",
        "duration_weeks": 99,
        "start_date": "2026-01-05",
        "template_id": template_id,
        "required_inputs": {"squat_start": 80, "bench_start": 60},
    }
    r = await client.post("/api/v1/programs/draft", json=draft_body, headers=auth_headers)
    assert r.status_code == 422
    assert r.json()["error_code"] == "VALIDATION_ERROR"
    assert "duration_weeks must be between 4 and 12" in r.json()["detail"]


@pytest.mark.asyncio
async def test_draft_accepts_duration_at_template_min_boundary(
    client, auth_headers, seeded_templates, seeded_exercises, user_environment, db_session
):
    from sqlalchemy import select

    from app.models import ProgramTemplate

    template_id = (
        await db_session.execute(select(ProgramTemplate.id).where(ProgramTemplate.slug == "full-body-x3"))
    ).scalar_one()

    draft_body = {
        "environment_id": user_environment.id,
        "days_per_week": 3,
        "session_duration_min": 60,
        "fitness_focus": "strength",
        "weight_unit": "kg",
        "duration_weeks": 4,
        "start_date": "2026-01-05",
        "template_id": template_id,
        "required_inputs": {"squat_start": 80, "bench_start": 60},
    }
    r = await client.post("/api/v1/programs/draft", json=draft_body, headers=auth_headers)
    assert r.status_code == 201
    assert r.json()["duration_weeks"] == 4
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `docker compose exec backend uv run pytest tests/test_programs_flow.py::test_draft_rejects_duration_outside_template_range tests/test_programs_flow.py::test_draft_accepts_duration_at_template_min_boundary -v`
Expected: the first test FAILs because `/draft` currently returns 201 for any `duration_weeks` value (no range check exists); the second currently PASSes already (no regression to introduce).

- [ ] **Step 3: Add the validation**

In `backend/app/api/v1/endpoints/programs.py`, in the `draft` endpoint, right after the existing template lookup (which already raises `ProgramTemplateNotFoundError`):

```python
    template = await get_template(db, data.template_id)
    if template is None or not template.is_active:
        raise ProgramTemplateNotFoundError()
    if not (template.duration_weeks_min <= data.duration_weeks <= template.duration_weeks_max):
        raise ValidationError(
            f"duration_weeks must be between {template.duration_weeks_min} and "
            f"{template.duration_weeks_max} for this template"
        )
```

Add `ValidationError` to the existing `app.core` import block near the top of the file:

```python
from app.core import (
    ProgramNotFoundError,
    ProgramTemplateNotFoundError,
    TrainingEnvironmentNotFoundError,
    ValidationError,
    WorkoutExerciseNotFoundError,
)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `docker compose exec backend uv run pytest tests/test_programs_flow.py -v`
Expected: PASS (all tests in the file, including the two new ones).

- [ ] **Step 5: Run the full backend suite**

Run: `docker compose exec backend uv run pytest -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/v1/endpoints/programs.py backend/tests/test_programs_flow.py
git commit -m "feat: reject draft duration_weeks outside the chosen template's range"
```

---

### Task 6: Add the "Program Duration" field to the Preferences step

**Files:**
- Modify: `frontend/src/types/programCreation.ts` (`MatchRequest` interface)
- Modify: `frontend/src/components/ProgramWizardStep1.tsx`
- Test: `frontend/src/tests/components/ProgramWizardStep1.test.tsx`

**Interfaces:**
- Produces: `MatchRequest` (form type) gains `duration_weeks: number`; `ProgramWizardStep1`'s `onSubmit` payload includes it — consumed by Task 7 (`ProgramBuilderPage`).

- [ ] **Step 1: Write the failing tests**

Add to `frontend/src/tests/components/ProgramWizardStep1.test.tsx`, inside the `describe('ProgramWizardStep1', ...)` block:

```tsx
  it('defaults program duration to 8 weeks and submits it with the form values', () => {
    const onSubmit = vi.fn();

    render(<ProgramWizardStep1 environmentId={1} onSubmit={onSubmit} onCancel={vi.fn()} />);

    const durationInput = screen.getByLabelText(/program duration/i);
    expect((durationInput as HTMLInputElement).value).toBe('8');

    fireEvent.click(screen.getByRole('button', { name: /next/i }));

    expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ duration_weeks: 8 }));
  });

  it('submits a user-chosen program duration', () => {
    const onSubmit = vi.fn();

    render(<ProgramWizardStep1 environmentId={1} onSubmit={onSubmit} onCancel={vi.fn()} />);

    fireEvent.change(screen.getByLabelText(/program duration/i), { target: { value: '12' } });
    fireEvent.click(screen.getByRole('button', { name: /next/i }));

    expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ duration_weeks: 12 }));
  });
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd frontend && npx vitest run src/tests/components/ProgramWizardStep1.test.tsx`
Expected: FAIL — `getByLabelText(/program duration/i)` finds no element.

- [ ] **Step 3: Add `duration_weeks` to the form type**

In `frontend/src/types/programCreation.ts`, in `interface MatchRequest`:

```ts
export interface MatchRequest {
  environment_id: number;
  days_per_week: number;
  session_duration_min: number;
  duration_weeks: number;
  weight_unit: WeightUnit;
  progression_style: ProgressionStyle;
  effort_method: EffortMethod | '';
  start_date: string;
  movement_preferences?: Record<EquipmentFamily, number>;
  complementary_focus?: boolean;
  variety_preference?: VarietyPreference;
}
```

- [ ] **Step 4: Add the field to `ProgramWizardStep1`**

In `frontend/src/components/ProgramWizardStep1.tsx`, add state (after `sessionDurationMin`):

```tsx
  const [sessionDurationMin, setSessionDurationMin] = useState(
    initialValues?.session_duration_min.toString() ?? '60',
  );
  const [durationWeeks, setDurationWeeks] = useState(
    initialValues?.duration_weeks.toString() ?? '8',
  );
```

Restore it in the `useEffect` (after `setSessionDurationMin`):

```tsx
      setSessionDurationMin(initialValues.session_duration_min.toString());
      setDurationWeeks(initialValues.duration_weeks.toString());
```

Include it in `handleSubmit`'s `onSubmit` call (after `session_duration_min`):

```tsx
      session_duration_min: parseInt(sessionDurationMin, 10),
      duration_weeks: parseInt(durationWeeks, 10),
```

Add the input, right after the Session Duration `FormField` and before the Start Date `FormField`:

```tsx
        {/* Program Duration */}
        <FormField
          label="Program Duration (weeks)"
          type="number"
          name="duration_weeks"
          value={durationWeeks}
          onChange={(e) => setDurationWeeks(e.target.value)}
          min="1"
          max="52"
          step="1"
          required
        />
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd frontend && npx vitest run src/tests/components/ProgramWizardStep1.test.tsx`
Expected: PASS (all tests in the file).

- [ ] **Step 6: Type-check**

Run: `cd frontend && npm run type-check`
Expected: no errors. (This will still show an error for `ProgramBuilderPage.tsx`'s hardcoded `duration_weeks: 8` line and its test mock until Task 7 is done — that's expected at this point.)

- [ ] **Step 7: Commit**

```bash
git add frontend/src/types/programCreation.ts frontend/src/components/ProgramWizardStep1.tsx frontend/src/tests/components/ProgramWizardStep1.test.tsx
git commit -m "feat: add program duration input to the builder's Preferences step"
```

---

### Task 7: Wire the Preferences duration value into the match/draft request

**Files:**
- Modify: `frontend/src/pages/ProgramBuilderPage.tsx:63`
- Modify: `frontend/src/tests/pages/ProgramBuilderPage.test.tsx` (mocked `ProgramWizard`)

**Interfaces:**
- Consumes: `FormMatchRequest.duration_weeks` (Task 6).
- Produces: the real `duration_weeks` value (not a hardcoded `8`) flows into every `/match` and `/draft` call.

- [ ] **Step 1: Update the mocked `ProgramWizard` to supply `duration_weeks`**

In `frontend/src/tests/pages/ProgramBuilderPage.test.tsx`, in the `vi.mock('@/components/ProgramWizard', ...)` block, add `duration_weeks: 8` to the object passed to `onComplete` (after `session_duration_min: 60,`):

```tsx
        onComplete({
          environment_id: environmentId,
          days_per_week: 3,
          session_duration_min: 60,
          duration_weeks: 8,
          weight_unit: 'kg',
```

- [ ] **Step 2: Run the existing test suite to confirm the current hardcode masks the change**

Run: `cd frontend && npx vitest run src/tests/pages/ProgramBuilderPage.test.tsx`
Expected: PASS — at this point `ProgramBuilderPage.tsx` still hardcodes `duration_weeks: 8`, so the assertion at `expect.objectContaining({ ..., duration_weeks: 8 })` passes regardless of what the mock now sends. This step is a checkpoint, not a red/green TDD step — it confirms the mock update alone doesn't break anything before wiring the real code path in Step 3.

- [ ] **Step 3: Wire the real value through**

In `frontend/src/pages/ProgramBuilderPage.tsx`, in `onPrefs`:

```tsx
  const onPrefs = (values: FormMatchRequest) => {
    setFormPrefs(values);
    const fitnessFocus = userProfile?.fitness_focus || 'general';
    const apiRequest: ApiMatchRequest = {
      environment_id: values.environment_id,
      days_per_week: values.days_per_week,
      session_duration_min: values.session_duration_min,
      weight_unit: values.weight_unit,
      fitness_focus: fitnessFocus,
      duration_weeks: values.duration_weeks,
    };
    setApiPrefs(apiRequest);
    setStep(1);
  };
```

- [ ] **Step 4: Run the test suite to verify it still passes for the right reason**

Run: `cd frontend && npx vitest run src/tests/pages/ProgramBuilderPage.test.tsx`
Expected: PASS — now genuinely exercising the `values.duration_weeks -> apiRequest.duration_weeks` wiring instead of an unrelated hardcode.

- [ ] **Step 5: Type-check the whole frontend**

Run: `cd frontend && npm run type-check`
Expected: no errors.

- [ ] **Step 6: Run the full frontend test suite**

Run: `cd frontend && npm test -- --run`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/pages/ProgramBuilderPage.tsx frontend/src/tests/pages/ProgramBuilderPage.test.tsx
git commit -m "feat: stop hardcoding duration_weeks in the program builder"
```

---

### Task 8: Display duration range on `TemplateListItem`

**Files:**
- Modify: `frontend/src/types/template.ts` (`Template` interface)
- Modify: `frontend/src/components/TemplateListItem.tsx`
- Test: `frontend/src/tests/components/TemplateListItem.test.tsx`

**Interfaces:**
- Consumes: `TemplateOut.duration_weeks_default/min/max` (Task 4, via the `/templates` API response).
- Produces: none consumed elsewhere — this is a leaf display change.

- [ ] **Step 1: Write the failing tests**

In `frontend/src/tests/components/TemplateListItem.test.tsx`, add the three new fields to `mockTemplate` (after `session_duration_max: 60,`):

```ts
  session_duration_max: 60,
  duration_weeks_default: 8,
  duration_weeks_min: 4,
  duration_weeks_max: 12,
```

Add new tests inside `describe('TemplateListItem', ...)`:

```tsx
  it('should show the duration range in the compact summary when min and max differ', () => {
    render(<TemplateListItem template={mockTemplate} isExpanded={false} onToggle={() => {}} />);

    expect(screen.getByText(/4-12 weeks/i)).toBeInTheDocument();
  });

  it('should collapse the duration range to a single number when min equals max', () => {
    const fixedDurationTemplate = {
      ...mockTemplate,
      duration_weeks_default: 8,
      duration_weeks_min: 8,
      duration_weeks_max: 8,
    };
    render(<TemplateListItem template={fixedDurationTemplate} isExpanded={false} onToggle={() => {}} />);

    expect(screen.getByText(/\b8 weeks\b/i)).toBeInTheDocument();
    expect(screen.queryByText(/8-8 weeks/i)).not.toBeInTheDocument();
  });

  it('should show the duration range in the expanded Configuration section', () => {
    render(<TemplateListItem template={mockTemplate} isExpanded={true} onToggle={() => {}} />);

    expect(screen.getByText('Duration')).toBeInTheDocument();
    expect(screen.getByText('4-12 weeks')).toBeInTheDocument();
  });
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd frontend && npx vitest run src/tests/components/TemplateListItem.test.tsx`
Expected: FAIL — TypeScript compile error on `mockTemplate` missing the new required `Template` fields, and the new duration assertions find no matching text.

- [ ] **Step 3: Add the fields to the `Template` type**

In `frontend/src/types/template.ts`, in `interface Template`:

```ts
export interface Template {
  slug: string;
  name: string;
  description: string;
  goals: string[];
  experience_levels: string[];
  days_per_week_min: number;
  days_per_week_max: number;
  session_duration_min: number;
  session_duration_max: number;
  duration_weeks_default: number;
  duration_weeks_min: number;
  duration_weeks_max: number;
  split: {
    sessions: Session[];
    schemes: Record<string, Scheme>;
  };
  progression_ref: ProgressionRef;
  required_inputs: RequiredInput[];
}
```

- [ ] **Step 4: Add a duration-range formatter and wire it into both views**

In `frontend/src/components/TemplateListItem.tsx`, add a local helper above the component:

```tsx
function formatDurationWeeks(min: number, max: number): string {
  return min === max ? `${min} weeks` : `${min}-${max} weeks`;
}
```

Update the compact summary line:

```tsx
            <p className="body-sm text-neutral-600 dark:text-neutral-400">
              {template.experience_levels.join(', ')} • {template.goals.join(', ')} •{' '}
              {template.days_per_week_min}-{template.days_per_week_max} days/week •{' '}
              {template.session_duration_min}-{template.session_duration_max} min •{' '}
              {formatDurationWeeks(template.duration_weeks_min, template.duration_weeks_max)}
            </p>
```

Add a fifth tile to the expanded Configuration grid, right after the Session Duration tile:

```tsx
              <div>
                <p className="label-sm text-neutral-600 dark:text-neutral-400">Session Duration</p>
                <p className="body-sm font-medium text-neutral-900 dark:text-neutral-50">
                  {template.session_duration_min}-{template.session_duration_max} min
                </p>
              </div>
              <div>
                <p className="label-sm text-neutral-600 dark:text-neutral-400">Duration</p>
                <p className="body-sm font-medium text-neutral-900 dark:text-neutral-50">
                  {formatDurationWeeks(template.duration_weeks_min, template.duration_weeks_max)}
                </p>
              </div>
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd frontend && npx vitest run src/tests/components/TemplateListItem.test.tsx`
Expected: PASS (all tests in the file).

- [ ] **Step 6: Type-check and run the full frontend suite**

Run: `cd frontend && npm run type-check && npm test -- --run`
Expected: no errors, all tests PASS.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/types/template.ts frontend/src/components/TemplateListItem.tsx frontend/src/tests/components/TemplateListItem.test.tsx
git commit -m "feat: display each template's duration range in the template browser"
```

---

### Task 9: End-to-end manual verification

**Files:** none (manual check only, no code changes)

- [ ] **Step 1: Start the stack**

Run: `docker-compose up -d` (backend + db), and separately `cd frontend && npm run dev`.

- [ ] **Step 2: Re-seed templates so the running DB has the new duration values**

Run: `docker compose exec backend uv run python -m app.db.seed.seed_program_templates`

- [ ] **Step 3: Walk the builder flow in the browser**

Navigate to the program builder, fill out Preferences (confirm "Program Duration (weeks)" appears, defaulted to 8), pick a template, and confirm the draft is created successfully with the entered duration.

- [ ] **Step 4: Trigger the validation error**

Repeat the flow entering a duration outside a template's range (e.g. `20` weeks against `full-body-x3`'s 4-12 range) and confirm the draft request fails with a visible error rather than silently succeeding.

- [ ] **Step 5: Check the template browser**

Navigate to the templates browser page and confirm each template's card/row shows its duration range (or a single number for templates with a fixed duration), both collapsed and expanded.

- [ ] **Step 6: Report findings**

If anything looks wrong, note it — no commit for this task, it's verification only.

---

## Self-Review Notes

- **Spec coverage:** data model + migration (Task 1), seed values (Task 2), `MatchRequest` required field (Task 3), `TemplateOut` exposure (Task 4), `/draft` validation (Task 5), Preferences input (Task 6-7), template browser display (Task 8), manual E2E (Task 9). All spec sections are covered.
- **Type consistency:** `duration_weeks_default/min/max` naming is identical across the ORM model (Task 1), seed data (Task 2), `TemplateOut`/endpoint (Task 4), and the frontend `Template` type (Task 8). `duration_weeks` (single field) is identical across `MatchRequest`/`DraftRequest` (unchanged), the frontend form `MatchRequest` (Task 6), and `ProgramWizardStep1`'s submitted payload (Task 6).
- **Known pre-existing test dependency:** Task 3's removal of the `MatchRequest.duration_weeks` default only breaks the five `_base_kwargs()`-based tests in `test_program_api_schemas.py` (fixed in the same task) — all `/match` and `/draft` HTTP tests in `test_programs_flow.py` already pass `duration_weeks` explicitly in their JSON bodies and are unaffected.
