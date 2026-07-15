# Program Generation Engine — Backend Implementation Plan (Plan 1 of 3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the rules-based backend engine that matches templates to a user, drafts a program, re-adapts it from feedback, and serves it over REST — per `docs/superpowers/specs/2026-07-15-program-generation-engine-design.md`.

**Architecture:** Layered templates stored in the DB (split + slot rules + progression reference as validated JSON); progression algorithms live in code behind a registry. A program stores its **base week** once and derives per-week loads at read time. Re-adaptation is deterministic re-generation over a `constraints` overlay.

**Tech Stack:** FastAPI (async), Pydantic v2, SQLAlchemy 2.0 async, Alembic, pytest + httpx. SQLite in tests, PostgreSQL in prod.

## Global Constraints

- Async/await for all DB I/O; strict mypy; Ruff + Black.
- TDD: write the failing test first, >80% coverage.
- Custom exceptions subclass `app.core.exceptions.AppException` and are re-exported from `app/core/__init__.py`.
- Routes under `/api/v1/`, protected with `Depends(get_current_user)`; DB via `Depends(get_db)`.
- Enums are `str, enum.Enum`; models use `Mapped`/`mapped_column`, `Base` from `app.core.database`, `_utcnow` from `app.models.user`.
- Commit after every green test.

---

### Task 1: Program domain models

**Files:**
- Create: `backend/app/models/program.py`
- Modify: `backend/app/models/__init__.py` (export new models + enums)
- Test: `backend/tests/test_program_models.py`

**Interfaces:**
- Produces: `ProgramTemplate`, `WorkoutProgram`, `Workout`, `WorkoutExercise` ORM models; `ProgramStatus` enum (`DRAFT`, `ACTIVE`, `ARCHIVED`).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_program_models.py
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ProgramTemplate, WorkoutProgram, Workout, WorkoutExercise
from app.models.program import ProgramStatus


@pytest.mark.asyncio
async def test_template_and_program_persist(db_session: AsyncSession, test_user):
    template = ProgramTemplate(
        name="Upper/Lower x4", slug="upper-lower-x4", description="",
        goals=["strength", "muscle_gain"], experience_levels=["intermediate"],
        days_per_week_min=4, days_per_week_max=4,
        session_duration_min=45, session_duration_max=75,
        split={"sessions": []}, slot_rules={"upper_a": []},
        progression_ref={"model_key": "linear_load", "params": {}},
        required_inputs=[],
    )
    db_session.add(template)
    await db_session.flush()

    program = WorkoutProgram(
        user_id=test_user.id, template_id=template.id, environment_id=1,
        name="My Program", focus="strength", status=ProgramStatus.DRAFT,
        duration_weeks=8, days_per_week=4, weight_unit="kg",
        constraints={"locked_slots": [], "swaps": {}},
    )
    db_session.add(program)
    await db_session.flush()

    workout = Workout(program_id=program.id, key="upper_a", name="Upper A", focus="push,pull", order=1)
    db_session.add(workout)
    await db_session.flush()

    slot = WorkoutExercise(
        workout_id=workout.id, order=1, exercise_id=1,
        fills_rule={"pattern": "horizontal_push"}, sets=3, reps_min=5, reps_max=5,
        base_load=60.0, rest_seconds=120, scheme_key="main",
        is_locked=False, is_user_swapped=False,
    )
    db_session.add(slot)
    await db_session.commit()

    found = (await db_session.execute(select(WorkoutProgram))).scalar_one()
    assert found.status == ProgramStatus.DRAFT
    assert found.constraints["swaps"] == {}
```

- [ ] **Step 2: Run it and confirm it fails**

Run: `docker-compose exec backend pytest tests/test_program_models.py -v`
Expected: FAIL — `ImportError: cannot import name 'ProgramTemplate'`.

- [ ] **Step 3: Implement the models**

```python
# backend/app/models/program.py
import enum
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON, Boolean, Date, DateTime, Enum, Float, ForeignKey, Integer, String, Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.user import _utcnow

if TYPE_CHECKING:
    pass


class ProgramStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class ProgramTemplate(Base):
    __tablename__ = "program_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    slug: Mapped[str] = mapped_column(String(150), nullable=False, unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    goals: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    experience_levels: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    days_per_week_min: Mapped[int] = mapped_column(Integer, nullable=False)
    days_per_week_max: Mapped[int] = mapped_column(Integer, nullable=False)
    session_duration_min: Mapped[int] = mapped_column(Integer, nullable=False)
    session_duration_max: Mapped[int] = mapped_column(Integer, nullable=False)
    split: Mapped[dict] = mapped_column(JSON, nullable=False)
    slot_rules: Mapped[dict] = mapped_column(JSON, nullable=False)
    progression_ref: Mapped[dict] = mapped_column(JSON, nullable=False)
    required_inputs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)


class WorkoutProgram(Base):
    __tablename__ = "workout_programs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("program_templates.id"), nullable=False)
    environment_id: Mapped[int] = mapped_column(ForeignKey("training_environments.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    focus: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[ProgramStatus] = mapped_column(Enum(ProgramStatus), nullable=False, default=ProgramStatus.DRAFT)
    duration_weeks: Mapped[int] = mapped_column(Integer, nullable=False)
    days_per_week: Mapped[int] = mapped_column(Integer, nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date)
    weight_unit: Mapped[str] = mapped_column(String(3), nullable=False, default="kg")
    constraints: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    workouts: Mapped[list["Workout"]] = relationship(
        back_populates="program", cascade="all, delete-orphan", order_by="Workout.order",
    )


class Workout(Base):
    __tablename__ = "workouts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("workout_programs.id"), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    focus: Mapped[str | None] = mapped_column(String(100))
    order: Mapped[int] = mapped_column(Integer, nullable=False)

    program: Mapped["WorkoutProgram"] = relationship(back_populates="workouts")
    exercises: Mapped[list["WorkoutExercise"]] = relationship(
        back_populates="workout", cascade="all, delete-orphan", order_by="WorkoutExercise.order",
    )


class WorkoutExercise(Base):
    __tablename__ = "workout_exercises"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workout_id: Mapped[int] = mapped_column(ForeignKey("workouts.id"), nullable=False, index=True)
    order: Mapped[int] = mapped_column(Integer, nullable=False)
    exercise_id: Mapped[int] = mapped_column(ForeignKey("exercises.id"), nullable=False)
    fills_rule: Mapped[dict] = mapped_column(JSON, nullable=False)
    sets: Mapped[int] = mapped_column(Integer, nullable=False)
    reps_min: Mapped[int] = mapped_column(Integer, nullable=False)
    reps_max: Mapped[int] = mapped_column(Integer, nullable=False)
    base_load: Mapped[float | None] = mapped_column(Float)
    rest_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    scheme_key: Mapped[str] = mapped_column(String(50), nullable=False)
    is_locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_user_swapped: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    workout: Mapped["Workout"] = relationship(back_populates="exercises")
```

- [ ] **Step 4: Export from the models package**

```python
# backend/app/models/__init__.py  — add these to the existing exports
from app.models.program import (  # noqa: F401
    ProgramStatus, ProgramTemplate, WorkoutProgram, Workout, WorkoutExercise,
)
```
Append the four model names + `ProgramStatus` to the module's `__all__` if it defines one.

- [ ] **Step 5: Run tests to confirm green**

Run: `docker-compose exec backend pytest tests/test_program_models.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/program.py backend/app/models/__init__.py backend/tests/test_program_models.py
git commit -m "feat(program): add program template and program ORM models"
```

---

### Task 2: Alembic migration for the four tables

**Files:**
- Create: `backend/migrations/versions/<rev>_add_program_tables.py` (generated)
- Test: manual up/down verification (per `database-migrations` skill).

**Interfaces:** none (schema only).

- [ ] **Step 1: Autogenerate the migration**

Run: `docker-compose exec backend alembic revision --autogenerate -m "add program tables"`
Expected: a new file under `backend/migrations/versions/` creating `program_templates`, `workout_programs`, `workouts`, `workout_exercises`.

- [ ] **Step 2: Review the generated file**

Confirm all four `op.create_table(...)` calls exist, FKs point to `users`, `program_templates`, `training_environments`, `exercises`, and JSON columns are present. Remove any spurious drops of unrelated tables.

- [ ] **Step 3: Apply and verify up**

Run: `docker-compose exec backend alembic upgrade head`
Then: `docker-compose exec postgres psql -U postgres -d app_db -c "\dt"`
Expected: the four new tables listed.

- [ ] **Step 4: Verify down**

Run: `docker-compose exec backend alembic downgrade -1` then `alembic upgrade head`.
Expected: clean down + re-up with no errors.

- [ ] **Step 5: Commit**

```bash
git add backend/migrations/versions/
git commit -m "feat(program): migration for program tables"
```

---

### Task 3: Template-structure schemas (JSON validation)

**Files:**
- Create: `backend/app/schemas/template.py`
- Modify: `backend/app/schemas/__init__.py`
- Test: `backend/tests/test_template_schema.py`

**Interfaces:**
- Produces: `SlotRule`, `SessionDef`, `SplitDef`, `ProgressionRef`, `RequiredInput`, `TemplateDefinition` (Pydantic). `TemplateDefinition.from_orm_template(t) -> TemplateDefinition`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_template_schema.py
import pytest
from pydantic import ValidationError

from app.schemas.template import SlotRule, SplitDef, TemplateDefinition


def test_slot_rule_requires_pattern_or_region():
    with pytest.raises(ValidationError):
        SlotRule(priority="primary", scheme="main")  # neither pattern nor region


def test_valid_template_definition_parses():
    td = TemplateDefinition(
        split=SplitDef(sessions=[{
            "key": "upper_a", "name": "Upper A", "order": 1,
            "slots": [{"pattern": "horizontal_push", "priority": "primary", "scheme": "main"}],
        }]),
        progression={"model_key": "linear_load", "params": {}},
        schemes={"main": {"sets": 3, "reps_min": 5, "reps_max": 5, "rest_seconds": 120}},
        required_inputs=[],
    )
    assert td.split.sessions[0].slots[0].pattern == "horizontal_push"
```

- [ ] **Step 2: Run and confirm failure**

Run: `docker-compose exec backend pytest tests/test_template_schema.py -v`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement the schemas**

```python
# backend/app/schemas/template.py
from pydantic import BaseModel, ConfigDict, model_validator


class SchemeDef(BaseModel):
    sets: int
    reps_min: int
    reps_max: int
    rest_seconds: int


class SlotRule(BaseModel):
    pattern: str | None = None
    region: str | None = None
    muscles: list[str] = []
    priority: str = "secondary"       # primary | secondary | accessory
    scheme: str = "accessory"

    @model_validator(mode="after")
    def _require_pattern_or_region(self) -> "SlotRule":
        if not self.pattern and not self.region:
            raise ValueError("slot must define either pattern or region")
        return self


class SessionDef(BaseModel):
    key: str
    name: str
    order: int
    slots: list[SlotRule]


class SplitDef(BaseModel):
    sessions: list[SessionDef]


class ProgressionRef(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    model_key: str
    params: dict = {}
    deload_every: int | None = None   # None = no deload modifier


class RequiredInput(BaseModel):
    key: str
    label: str
    type: str = "number"             # number | text
    applies_to: str | None = None    # movement_slug or slot key the value seeds


class TemplateDefinition(BaseModel):
    split: SplitDef
    progression: ProgressionRef
    schemes: dict[str, SchemeDef]
    required_inputs: list[RequiredInput] = []

    @classmethod
    def from_orm_template(cls, t) -> "TemplateDefinition":
        return cls(
            split=SplitDef(**t.split),
            progression=ProgressionRef(**t.progression_ref),
            schemes={k: SchemeDef(**v) for k, v in (t.split.get("schemes", {}) or {}).items()}
            if isinstance(t.split, dict) and "schemes" in t.split
            else {k: SchemeDef(**v) for k, v in getattr(t, "schemes", {}).items()},
            required_inputs=[RequiredInput(**r) for r in t.required_inputs],
        )
```
> Note: `schemes` are stored inside the template `split` JSON under a `"schemes"` key (see Task 9 seed). `from_orm_template` reads them from there.

- [ ] **Step 4: Simplify `from_orm_template` to match the seed shape**

Replace the `from_orm_template` body with the single supported source (schemes live in `split["schemes"]`):

```python
    @classmethod
    def from_orm_template(cls, t) -> "TemplateDefinition":
        split_data = dict(t.split)
        schemes = split_data.pop("schemes", {})
        return cls(
            split=SplitDef(**split_data),
            progression=ProgressionRef(**t.progression_ref),
            schemes={k: SchemeDef(**v) for k, v in schemes.items()},
            required_inputs=[RequiredInput(**r) for r in t.required_inputs],
        )
```

- [ ] **Step 5: Export and run tests**

Add to `backend/app/schemas/__init__.py`:
```python
from app.schemas.template import (  # noqa: F401
    ProgressionRef, RequiredInput, SchemeDef, SessionDef, SlotRule, SplitDef, TemplateDefinition,
)
```
Run: `docker-compose exec backend pytest tests/test_template_schema.py -v` → PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/template.py backend/app/schemas/__init__.py backend/tests/test_template_schema.py
git commit -m "feat(program): template definition schemas with validation"
```

---

### Task 4: Progression base — protocol, SetScheme, registry

**Files:**
- Create: `backend/app/services/program/__init__.py`, `backend/app/services/program/progression/__init__.py`, `backend/app/services/program/progression/base.py`
- Test: `backend/tests/test_progression_registry.py`

**Interfaces:**
- Produces: `SetScheme` (dataclass: `sets:int, reps:int, load:float|None, rest_seconds:int, note:str|None`), `ProgressionModel` protocol with `key: str` and `resolve(base, week, params) -> SetScheme`, `SlotBase` (dataclass: `sets, reps_min, reps_max, rest_seconds, base_load`), `register(model)` and `get_model(key) -> ProgressionModel`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_progression_registry.py
import pytest
from app.services.program.progression.base import SlotBase, SetScheme, register, get_model


def test_register_and_get():
    class Dummy:
        key = "dummy"
        def resolve(self, base, week, params):
            return SetScheme(sets=base.sets, reps=base.reps_min, load=base.base_load, rest_seconds=base.rest_seconds, note=None)
    register(Dummy())
    model = get_model("dummy")
    out = model.resolve(SlotBase(sets=3, reps_min=5, reps_max=5, rest_seconds=120, base_load=60.0), week=1, params={})
    assert out.sets == 3 and out.load == 60.0


def test_get_unknown_raises():
    with pytest.raises(KeyError):
        get_model("nope")
```

- [ ] **Step 2: Run and confirm failure** — `pytest tests/test_progression_registry.py -v` → FAIL (import error).

- [ ] **Step 3: Implement base + registry**

```python
# backend/app/services/program/progression/base.py
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SlotBase:
    sets: int
    reps_min: int
    reps_max: int
    rest_seconds: int
    base_load: float | None


@dataclass(frozen=True)
class SetScheme:
    sets: int
    reps: int
    load: float | None
    rest_seconds: int
    note: str | None = None


class ProgressionModel(Protocol):
    key: str
    def resolve(self, base: SlotBase, week: int, params: dict) -> SetScheme: ...


_REGISTRY: dict[str, ProgressionModel] = {}


def register(model: ProgressionModel) -> None:
    _REGISTRY[model.key] = model


def get_model(key: str) -> ProgressionModel:
    if key not in _REGISTRY:
        raise KeyError(f"Unknown progression model: {key}")
    return _REGISTRY[key]
```
Leave `backend/app/services/program/__init__.py` and `.../progression/__init__.py` empty for now.

- [ ] **Step 4: Run tests → PASS.** `pytest tests/test_progression_registry.py -v`

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/program/ backend/tests/test_progression_registry.py
git commit -m "feat(program): progression model protocol and registry"
```

---

### Task 5: LinearLoad progression

**Files:**
- Create: `backend/app/services/program/progression/linear_load.py`
- Test: `backend/tests/test_progression_linear.py`

**Interfaces:**
- Consumes: `SlotBase`, `SetScheme` from `base`.
- Produces: `LinearLoad` (key `"linear_load"`); params: `{"increment": float}` (default 2.5). Week 1 = base_load; each week adds `increment`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_progression_linear.py
from app.services.program.progression.base import SlotBase
from app.services.program.progression.linear_load import LinearLoad


def test_linear_adds_increment_per_week():
    m = LinearLoad()
    base = SlotBase(sets=3, reps_min=5, reps_max=5, rest_seconds=120, base_load=60.0)
    assert m.resolve(base, week=1, params={"increment": 2.5}).load == 60.0
    assert m.resolve(base, week=3, params={"increment": 2.5}).load == 65.0
    assert m.resolve(base, week=1, params={}).reps == 5


def test_linear_handles_no_load():
    m = LinearLoad()
    base = SlotBase(sets=3, reps_min=8, reps_max=8, rest_seconds=90, base_load=None)
    assert m.resolve(base, week=2, params={"increment": 2.5}).load is None
```

- [ ] **Step 2: Run and confirm failure.**

- [ ] **Step 3: Implement**

```python
# backend/app/services/program/progression/linear_load.py
from app.services.program.progression.base import SetScheme, SlotBase, register


class LinearLoad:
    key = "linear_load"

    def resolve(self, base: SlotBase, week: int, params: dict) -> SetScheme:
        increment = float(params.get("increment", 2.5))
        load = None if base.base_load is None else base.base_load + increment * (week - 1)
        return SetScheme(sets=base.sets, reps=base.reps_min, load=load, rest_seconds=base.rest_seconds)


register(LinearLoad())
```

- [ ] **Step 4: Run tests → PASS.**

- [ ] **Step 5: Commit** — `git commit -m "feat(program): linear load progression"`

---

### Task 6: DoubleProgression

**Files:**
- Create: `backend/app/services/program/progression/double_progression.py`
- Test: `backend/tests/test_progression_double.py`

**Interfaces:**
- Produces: `DoubleProgression` (key `"double_progression"`); params: `{"increment": float}`. Adds one rep per week from `reps_min` until `reps_max`; on the week that would exceed `reps_max`, reset to `reps_min` and add `increment` to load. Repeats each cycle.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_progression_double.py
from app.services.program.progression.base import SlotBase
from app.services.program.progression.double_progression import DoubleProgression


def test_double_progression_cycle():
    m = DoubleProgression()
    base = SlotBase(sets=3, reps_min=8, reps_max=10, rest_seconds=90, base_load=20.0)
    p = {"increment": 2.5}
    assert (m.resolve(base, 1, p).reps, m.resolve(base, 1, p).load) == (8, 20.0)
    assert (m.resolve(base, 2, p).reps, m.resolve(base, 2, p).load) == (9, 20.0)
    assert (m.resolve(base, 3, p).reps, m.resolve(base, 3, p).load) == (10, 20.0)
    assert (m.resolve(base, 4, p).reps, m.resolve(base, 4, p).load) == (8, 22.5)  # reset + load up
    assert (m.resolve(base, 7, p).reps, m.resolve(base, 7, p).load) == (8, 25.0)
```

- [ ] **Step 2: Run and confirm failure.**

- [ ] **Step 3: Implement**

```python
# backend/app/services/program/progression/double_progression.py
from app.services.program.progression.base import SetScheme, SlotBase, register


class DoubleProgression:
    key = "double_progression"

    def resolve(self, base: SlotBase, week: int, params: dict) -> SetScheme:
        increment = float(params.get("increment", 2.5))
        span = base.reps_max - base.reps_min + 1  # reps steps per load cycle
        step = week - 1
        cycle, offset = divmod(step, span)
        reps = base.reps_min + offset
        load = None if base.base_load is None else base.base_load + increment * cycle
        return SetScheme(sets=base.sets, reps=reps, load=load, rest_seconds=base.rest_seconds)


register(DoubleProgression())
```

- [ ] **Step 4: Run tests → PASS.**

- [ ] **Step 5: Commit** — `git commit -m "feat(program): double progression"`

---

### Task 7: WeeklyUndulating

**Files:**
- Create: `backend/app/services/program/progression/weekly_undulating.py`
- Test: `backend/tests/test_progression_undulating.py`

**Interfaces:**
- Produces: `WeeklyUndulating` (key `"weekly_undulating"`); params: `{"waves": [{"reps": int, "intensity": float}], "increment": float}`. Rotates through `waves` by `(week-1) % len(waves)`; `load = base_load * intensity`, climbing `increment` each full wave cycle.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_progression_undulating.py
from app.services.program.progression.base import SlotBase
from app.services.program.progression.weekly_undulating import WeeklyUndulating


def test_undulating_rotates_waves():
    m = WeeklyUndulating()
    base = SlotBase(sets=4, reps_min=5, reps_max=12, rest_seconds=120, base_load=100.0)
    p = {"waves": [{"reps": 5, "intensity": 1.0}, {"reps": 12, "intensity": 0.7}], "increment": 5.0}
    assert (m.resolve(base, 1, p).reps, m.resolve(base, 1, p).load) == (5, 100.0)
    assert (m.resolve(base, 2, p).reps, m.resolve(base, 2, p).load) == (12, 70.0)
    assert m.resolve(base, 3, p).reps == 5           # new cycle
    assert m.resolve(base, 3, p).load == 105.0       # +increment after one full wave
```

- [ ] **Step 2: Run and confirm failure.**

- [ ] **Step 3: Implement**

```python
# backend/app/services/program/progression/weekly_undulating.py
from app.services.program.progression.base import SetScheme, SlotBase, register


class WeeklyUndulating:
    key = "weekly_undulating"

    def resolve(self, base: SlotBase, week: int, params: dict) -> SetScheme:
        waves = params.get("waves") or [{"reps": base.reps_min, "intensity": 1.0}]
        increment = float(params.get("increment", 0.0))
        step = week - 1
        cycle, idx = divmod(step, len(waves))
        wave = waves[idx]
        if base.base_load is None:
            load = None
        else:
            load = base.base_load * float(wave["intensity"]) + increment * cycle
        return SetScheme(sets=base.sets, reps=int(wave["reps"]), load=load, rest_seconds=base.rest_seconds)


register(WeeklyUndulating())
```

- [ ] **Step 4: Run tests → PASS.**

- [ ] **Step 5: Commit** — `git commit -m "feat(program): weekly undulating progression"`

---

### Task 8: Deload modifier

**Files:**
- Create: `backend/app/services/program/progression/deload.py`
- Modify: `backend/app/services/program/progression/__init__.py` (import all models so they register)
- Test: `backend/tests/test_progression_deload.py`

**Interfaces:**
- Produces: `apply_deload(scheme: SetScheme, week: int, every: int | None, factor: float = 0.6) -> SetScheme`. On weeks where `week % every == 0`, multiply load by `factor` and tag `note="deload"`. `every=None` returns the scheme unchanged.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_progression_deload.py
from app.services.program.progression.base import SetScheme
from app.services.program.progression.deload import apply_deload


def test_deload_every_fourth_week():
    s = SetScheme(sets=3, reps=5, load=100.0, rest_seconds=120)
    assert apply_deload(s, week=3, every=4).load == 100.0
    out = apply_deload(s, week=4, every=4)
    assert out.load == 60.0 and out.note == "deload"
    assert apply_deload(s, week=4, every=None).load == 100.0
```

- [ ] **Step 2: Run and confirm failure.**

- [ ] **Step 3: Implement**

```python
# backend/app/services/program/progression/deload.py
from app.services.program.progression.base import SetScheme


def apply_deload(scheme: SetScheme, week: int, every: int | None, factor: float = 0.6) -> SetScheme:
    if not every or week % every != 0 or scheme.load is None:
        return scheme
    return SetScheme(
        sets=scheme.sets, reps=scheme.reps, load=round(scheme.load * factor, 2),
        rest_seconds=scheme.rest_seconds, note="deload",
    )
```

- [ ] **Step 4: Register all models on import**

```python
# backend/app/services/program/progression/__init__.py
from app.services.program.progression import (  # noqa: F401
    double_progression, linear_load, weekly_undulating,
)
from app.services.program.progression.base import (  # noqa: F401
    SetScheme, SlotBase, get_model, register,
)
from app.services.program.progression.deload import apply_deload  # noqa: F401
```

- [ ] **Step 5: Run tests → PASS.** `pytest tests/test_progression_deload.py -v`

- [ ] **Step 6: Commit** — `git commit -m "feat(program): deload modifier + register progression models"`

---

### Task 9: Template seed data + seed script

**Files:**
- Create: `backend/app/db/seed/program_templates.py`, `backend/app/db/seed/seed_program_templates.py`
- Test: `backend/tests/test_seed_templates.py`

**Interfaces:**
- Produces: `PROGRAM_TEMPLATE_SEED: list[dict]` (the four templates from spec §12) and `async def seed_program_templates(db)` that upserts by `slug`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_seed_templates.py
import pytest
from sqlalchemy import select
from app.models import ProgramTemplate
from app.schemas.template import TemplateDefinition
from app.db.seed.seed_program_templates import seed_program_templates


@pytest.mark.asyncio
async def test_seed_inserts_and_is_idempotent(db_session):
    await seed_program_templates(db_session)
    await seed_program_templates(db_session)  # second run must not duplicate
    rows = (await db_session.execute(select(ProgramTemplate))).scalars().all()
    slugs = {r.slug for r in rows}
    assert {"full-body-x3", "upper-lower-x4", "push-pull-legs-x6", "bodyweight-full-body-x3"} <= slugs
    for r in rows:
        TemplateDefinition.from_orm_template(r)  # every seed parses cleanly
```

- [ ] **Step 2: Run and confirm failure.**

- [ ] **Step 3: Implement the seed data**

Create `backend/app/db/seed/program_templates.py` with four entries. Each entry's `split` carries a `"schemes"` key plus `"sessions"`. Full example for one template (repeat the shape for the others, varying split/goals/progression per spec §12 table):

```python
# backend/app/db/seed/program_templates.py
PROGRAM_TEMPLATE_SEED: list[dict] = [
    {
        "name": "Full Body", "slug": "full-body-x3",
        "description": "Three full-body days for beginners building general strength.",
        "goals": ["general", "strength"], "experience_levels": ["beginner"],
        "days_per_week_min": 3, "days_per_week_max": 3,
        "session_duration_min": 45, "session_duration_max": 60,
        "progression_ref": {"model_key": "linear_load", "params": {"increment": 2.5}, "deload_every": 4},
        "required_inputs": [
            {"key": "squat_start", "label": "Comfortable squat weight", "type": "number", "applies_to": "squat"},
            {"key": "bench_start", "label": "Comfortable bench weight", "type": "number", "applies_to": "horizontal_push"},
        ],
        "split": {
            "schemes": {
                "main": {"sets": 3, "reps_min": 5, "reps_max": 5, "rest_seconds": 120},
                "accessory": {"sets": 3, "reps_min": 10, "reps_max": 12, "rest_seconds": 60},
            },
            "sessions": [
                {"key": "full_a", "name": "Full Body A", "order": 1, "slots": [
                    {"pattern": "squat", "priority": "primary", "scheme": "main"},
                    {"pattern": "horizontal_push", "priority": "primary", "scheme": "main"},
                    {"pattern": "horizontal_pull", "priority": "primary", "scheme": "main"},
                    {"region": "core", "priority": "accessory", "scheme": "accessory"},
                ]},
                {"key": "full_b", "name": "Full Body B", "order": 2, "slots": [
                    {"pattern": "hinge", "priority": "primary", "scheme": "main"},
                    {"pattern": "vertical_push", "priority": "primary", "scheme": "main"},
                    {"pattern": "vertical_pull", "priority": "primary", "scheme": "main"},
                    {"region": "core", "priority": "accessory", "scheme": "accessory"},
                ]},
                {"key": "full_c", "name": "Full Body C", "order": 3, "slots": [
                    {"pattern": "squat", "priority": "primary", "scheme": "main"},
                    {"pattern": "horizontal_push", "priority": "secondary", "scheme": "accessory"},
                    {"pattern": "horizontal_pull", "priority": "secondary", "scheme": "accessory"},
                    {"region": "core", "priority": "accessory", "scheme": "accessory"},
                ]},
            ],
        },
    },
    # bodyweight-full-body-x3: same 3-day shape, goals ["general"], experience ["beginner"],
    #   progression {"model_key": "double_progression", "params": {"increment": 0}}, required_inputs [],
    #   slots use bodyweight-friendly patterns (squat, horizontal_push, vertical_pull, core), scheme reps_min/max 8/15.
    # upper-lower-x4: 4 sessions (upper_a, lower_a, upper_b, lower_b), goals ["strength","muscle_gain"],
    #   experience ["intermediate"], progression {"model_key":"double_progression","params":{"increment":2.5},"deload_every":4},
    #   duration 45-75; slots per session cover push/pull/squat/hinge + accessory isolation.
    # push-pull-legs-x6: 6 sessions (push_a,pull_a,legs_a,push_b,pull_b,legs_b), goals ["muscle_gain"],
    #   experience ["intermediate","advanced"], progression {"model_key":"double_progression","params":{"increment":2.5},"deload_every":6}.
]
```
> The four comment blocks describe the remaining three entries concretely; author them following the `full-body-x3` shape exactly (same keys, differing values as noted). Each session's slots must reference schemes defined in that template's `schemes` map.

- [ ] **Step 4: Implement the seed script (idempotent upsert by slug)**

```python
# backend/app/db/seed/seed_program_templates.py
import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker
from app.db.seed.program_templates import PROGRAM_TEMPLATE_SEED
from app.models import ProgramTemplate


async def seed_program_templates(db: AsyncSession) -> None:
    for entry in PROGRAM_TEMPLATE_SEED:
        existing = (
            await db.execute(select(ProgramTemplate).where(ProgramTemplate.slug == entry["slug"]))
        ).scalar_one_or_none()
        if existing is None:
            db.add(ProgramTemplate(**entry))
        else:
            for key, value in entry.items():
                setattr(existing, key, value)
            db.add(existing)
    await db.commit()


async def _main() -> None:
    async with async_session_maker() as session:
        await seed_program_templates(session)


if __name__ == "__main__":
    asyncio.run(_main())
```
> Check `app/core/database.py` for the actual session-maker name; if it is not `async_session_maker`, use the existing exported maker (mirror `seed_exercises.py`).

- [ ] **Step 5: Verify the seed helper name against `seed_exercises.py`**

Run: `docker-compose exec backend python -c "import app.db.seed.seed_exercises as s; print([n for n in dir(s) if 'session' in n.lower() or 'main' in n.lower()])"`
Match the session-acquisition pattern used there.

- [ ] **Step 6: Run tests → PASS.** `pytest tests/test_seed_templates.py -v`

- [ ] **Step 7: Run the seed against the dev DB**

Run: `docker-compose exec backend python -m app.db.seed.seed_program_templates`
Expected: no error; re-running does not duplicate.

- [ ] **Step 8: Commit** — `git commit -m "feat(program): seed curated program templates"`

---

### Task 10: Matching service

**Files:**
- Create: `backend/app/services/program/matching.py`
- Test: `backend/tests/test_matching.py`

**Interfaces:**
- Consumes: `ProgramTemplate` rows, user profile fields, environment `equipment_tags`.
- Produces: `MatchInput` (dataclass: `fitness_focus:str, experience_level:str, days_per_week:int, session_duration_min:int, environment_equipment:list[str]`), `TemplateMatch` (dataclass: `template_id:int, slug:str, name:str, fit_pct:int, factors:dict[str,float]`), `rank_templates(templates, inp, feasibility) -> list[TemplateMatch]` sorted desc, top 3. `feasibility` is a `dict[template_id, bool]` computed by the caller (Task 11 provides `template_is_feasible`).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_matching.py
from app.services.program.matching import MatchInput, rank_templates


class _T:
    def __init__(self, id, slug, goals, exps, dmin, dmax, smin, smax):
        self.id, self.slug, self.name = id, slug, slug
        self.goals, self.experience_levels = goals, exps
        self.days_per_week_min, self.days_per_week_max = dmin, dmax
        self.session_duration_min, self.session_duration_max = smin, smax


def test_goal_and_experience_rank_highest():
    templates = [
        _T(1, "ul", ["strength"], ["intermediate"], 4, 4, 45, 75),
        _T(2, "fb", ["endurance"], ["beginner"], 3, 3, 30, 45),
    ]
    inp = MatchInput("strength", "intermediate", 4, 60, ["barbell"])
    ranked = rank_templates(templates, inp, feasibility={1: True, 2: True})
    assert ranked[0].template_id == 1
    assert ranked[0].fit_pct > ranked[1].fit_pct


def test_infeasible_template_excluded():
    templates = [_T(1, "ul", ["strength"], ["intermediate"], 4, 4, 45, 75)]
    inp = MatchInput("strength", "intermediate", 4, 60, [])
    assert rank_templates(templates, inp, feasibility={1: False}) == []
```

- [ ] **Step 2: Run and confirm failure.**

- [ ] **Step 3: Implement**

```python
# backend/app/services/program/matching.py
from dataclasses import dataclass

WEIGHTS = {"goal": 0.35, "experience": 0.3, "days": 0.2, "duration": 0.15}


@dataclass(frozen=True)
class MatchInput:
    fitness_focus: str
    experience_level: str
    days_per_week: int
    session_duration_min: int
    environment_equipment: list[str]


@dataclass(frozen=True)
class TemplateMatch:
    template_id: int
    slug: str
    name: str
    fit_pct: int
    factors: dict


def _range_fit(value: int, low: int, high: int) -> float:
    if low <= value <= high:
        return 1.0
    distance = low - value if value < low else value - high
    return max(0.0, 1.0 - distance / max(low, 1))


def rank_templates(templates, inp: MatchInput, feasibility: dict[int, bool]) -> list[TemplateMatch]:
    matches: list[TemplateMatch] = []
    for t in templates:
        if not feasibility.get(t.id, False):
            continue
        factors = {
            "goal": 1.0 if inp.fitness_focus in t.goals else 0.0,
            "experience": 1.0 if inp.experience_level in t.experience_levels else 0.3,
            "days": _range_fit(inp.days_per_week, t.days_per_week_min, t.days_per_week_max),
            "duration": _range_fit(inp.session_duration_min, t.session_duration_min, t.session_duration_max),
        }
        score = sum(WEIGHTS[k] * v for k, v in factors.items())
        matches.append(TemplateMatch(t.id, t.slug, t.name, round(score * 100), factors))
    matches.sort(key=lambda m: m.fit_pct, reverse=True)
    return matches[:3]
```

- [ ] **Step 4: Run tests → PASS.**

- [ ] **Step 5: Commit** — `git commit -m "feat(program): template matching/ranking"`

---

### Task 11: Exercise selection service

**Files:**
- Create: `backend/app/services/program/selection.py`
- Test: `backend/tests/test_selection.py`

**Interfaces:**
- Consumes: `Exercise` rows, `SlotRule`, environment equipment, user `experience_level` + injuries, and a `constraints` dict.
- Produces:
  - `SelectionContext` (dataclass: `equipment:list[str], experience:str, injuries:list[str], used_movement_slugs:set[str]`).
  - `select_for_slot(candidates, rule: SlotRule, ctx, locked_exercise_id: int | None, excluded_ids: set[int]) -> Exercise | None`.
  - `template_is_feasible(sessions: list, all_exercises, equipment) -> bool` — true if every slot has ≥1 equipment-valid candidate.
  - `EXPERIENCE_ORDER = {"beginner":0,"intermediate":1,"advanced":2}`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_selection.py
from app.schemas.template import SlotRule
from app.services.program.selection import SelectionContext, select_for_slot


class _Ex:
    def __init__(self, id, slug, mslug, pattern, region, muscles, equip, diff, contra):
        self.id, self.slug, self.movement_slug = id, slug, mslug
        self.movement_pattern = type("P", (), {"value": pattern})
        self.body_region = type("R", (), {"value": region})
        self.primary_muscles, self.equipment_tags = muscles, equip
        self.difficulty_level = type("D", (), {"value": diff})
        self.contraindications = contra


def _ctx(equip, injuries=()):
    return SelectionContext(list(equip), "intermediate", list(injuries), set())


def test_filters_by_equipment_and_injury():
    bench = _Ex(1, "bb-bench", "bench", "horizontal_push", "upper_body", ["chest"], ["barbell"], "intermediate", ["shoulder"])
    pushup = _Ex(2, "pushup", "pushup", "horizontal_push", "upper_body", ["chest"], [], "beginner", [])
    rule = SlotRule(pattern="horizontal_push", priority="primary", scheme="main")
    # shoulder injury excludes bench; no barbell anyway -> pushup chosen
    chosen = select_for_slot([bench, pushup], rule, _ctx([], injuries=["shoulder"]), None, set())
    assert chosen.id == 2


def test_locked_overrides_selection():
    a = _Ex(1, "a", "a", "squat", "lower_body", ["quads"], [], "beginner", [])
    b = _Ex(2, "b", "b", "squat", "lower_body", ["quads"], [], "beginner", [])
    rule = SlotRule(pattern="squat", priority="primary", scheme="main")
    assert select_for_slot([a, b], rule, _ctx([]), locked_exercise_id=2, excluded_ids=set()).id == 2
```

- [ ] **Step 2: Run and confirm failure.**

- [ ] **Step 3: Implement**

```python
# backend/app/services/program/selection.py
from dataclasses import dataclass

from app.schemas.template import SlotRule

EXPERIENCE_ORDER = {"beginner": 0, "intermediate": 1, "advanced": 2}


@dataclass
class SelectionContext:
    equipment: list[str]
    experience: str
    injuries: list[str]
    used_movement_slugs: set[str]


def _matches_rule(ex, rule: SlotRule) -> bool:
    if rule.pattern and ex.movement_pattern.value != rule.pattern:
        return False
    if rule.region and ex.body_region.value != rule.region:
        return False
    if rule.muscles and not (set(rule.muscles) & set(ex.primary_muscles)):
        return False
    return True


def _passes_filters(ex, ctx: SelectionContext, tolerance: int = 1) -> bool:
    if not set(ex.equipment_tags) <= set(ctx.equipment):
        return False
    if EXPERIENCE_ORDER[ex.difficulty_level.value] > EXPERIENCE_ORDER[ctx.experience] + tolerance:
        return False
    if set(ex.contraindications) & set(ctx.injuries):
        return False
    return True


def _score(ex, rule: SlotRule, ctx: SelectionContext) -> tuple:
    muscle_fit = len(set(rule.muscles) & set(ex.primary_muscles))
    variety = 0 if ex.movement_slug in ctx.used_movement_slugs else 1
    diff_gap = -abs(EXPERIENCE_ORDER[ex.difficulty_level.value] - EXPERIENCE_ORDER[ctx.experience])
    return (variety, muscle_fit, diff_gap, -ex.id)


def select_for_slot(candidates, rule: SlotRule, ctx: SelectionContext,
                    locked_exercise_id: int | None, excluded_ids: set[int]):
    if locked_exercise_id is not None:
        for ex in candidates:
            if ex.id == locked_exercise_id:
                return ex
    pool = [ex for ex in candidates
            if ex.id not in excluded_ids and _matches_rule(ex, rule) and _passes_filters(ex, ctx)]
    if not pool:  # fallback: relax difficulty tolerance
        pool = [ex for ex in candidates
                if ex.id not in excluded_ids and _matches_rule(ex, rule) and _passes_filters(ex, ctx, tolerance=99)]
    if not pool:
        return None
    return max(pool, key=lambda ex: _score(ex, rule, ctx))


def template_is_feasible(sessions, all_exercises, equipment) -> bool:
    ctx = SelectionContext(list(equipment), "advanced", [], set())
    for session in sessions:
        for slot in session.slots:
            if select_for_slot(all_exercises, slot, ctx, None, set()) is None:
                return False
    return True
```

- [ ] **Step 4: Run tests → PASS.**

- [ ] **Step 5: Commit** — `git commit -m "feat(program): exercise selection + feasibility"`

---

### Task 12: Program CRUD

**Files:**
- Create: `backend/app/crud/program.py`
- Modify: `backend/app/crud/__init__.py`
- Test: covered indirectly by Task 13/14 service tests (no standalone test).

**Interfaces:**
- Produces async helpers:
  - `list_active_templates(db) -> list[ProgramTemplate]`
  - `get_template(db, template_id) -> ProgramTemplate | None`
  - `get_program(db, user_id, program_id) -> WorkoutProgram | None` (eager-loads `workouts.exercises`)
  - `save_program(db, program) -> WorkoutProgram`

- [ ] **Step 1: Implement**

```python
# backend/app/crud/program.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import ProgramTemplate, Workout, WorkoutProgram


async def list_active_templates(db: AsyncSession) -> list[ProgramTemplate]:
    result = await db.execute(select(ProgramTemplate).where(ProgramTemplate.is_active.is_(True)))
    return list(result.scalars().all())


async def get_template(db: AsyncSession, template_id: int) -> ProgramTemplate | None:
    result = await db.execute(select(ProgramTemplate).where(ProgramTemplate.id == template_id))
    return result.scalar_one_or_none()


async def get_program(db: AsyncSession, user_id: int, program_id: int) -> WorkoutProgram | None:
    result = await db.execute(
        select(WorkoutProgram)
        .where(WorkoutProgram.id == program_id, WorkoutProgram.user_id == user_id)
        .options(selectinload(WorkoutProgram.workouts).selectinload(Workout.exercises))
    )
    return result.scalar_one_or_none()


async def save_program(db: AsyncSession, program: WorkoutProgram) -> WorkoutProgram:
    db.add(program)
    await db.commit()
    await db.refresh(program)
    return program
```

- [ ] **Step 2: Export** in `backend/app/crud/__init__.py`:
```python
from app.crud.program import (  # noqa: F401
    get_program, get_template, list_active_templates, save_program,
)
```

- [ ] **Step 3: Commit** — `git commit -m "feat(program): program crud helpers"`

---

### Task 13: Drafting + preview (derive) service

**Files:**
- Create: `backend/app/services/program/drafting.py`, `backend/app/services/program/preview.py`
- Test: `backend/tests/test_drafting.py`, `backend/tests/test_preview.py`

**Interfaces:**
- Consumes: `TemplateDefinition`, `SelectionContext`, exercise list, progression registry, `apply_deload`.
- Produces:
  - `build_draft(template, definition, ctx, exercises, *, user_id, environment_id, days_per_week, duration_weeks, weight_unit, required_inputs) -> WorkoutProgram` (populates `.workouts[].exercises[]` in memory; caller persists).
  - `derive_week(program, definition, week) -> list[dict]` — for each workout, resolve each slot via the progression model + deload into `{workout, exercise_id, sets, reps, load, rest_seconds, note}`.

- [ ] **Step 1: Write the failing test (drafting)**

```python
# backend/tests/test_drafting.py
import pytest
from app.schemas.template import TemplateDefinition
from app.services.program.selection import SelectionContext
from app.services.program.drafting import build_draft


@pytest.mark.asyncio
async def test_build_draft_fills_slots(sample_template_orm, sample_exercises):
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(equipment=["barbell", "bench", "squat_rack"], experience="intermediate", injuries=[], used_movement_slugs=set())
    program = build_draft(
        sample_template_orm, definition, ctx, sample_exercises,
        user_id=1, environment_id=1, days_per_week=3, duration_weeks=8,
        weight_unit="kg", required_inputs={"squat_start": 80, "bench_start": 60},
    )
    assert len(program.workouts) == len(definition.split.sessions)
    assert all(w.exercises for w in program.workouts)
```
> Add `sample_template_orm` and `sample_exercises` fixtures to `conftest.py` (a single seeded template row + a handful of `Exercise` rows covering the template's patterns). Use the seed helpers from Tasks 9 and the exercise seed.

- [ ] **Step 2: Run and confirm failure.**

- [ ] **Step 3: Implement drafting**

```python
# backend/app/services/program/drafting.py
from app.models import Workout, WorkoutExercise, WorkoutProgram, ProgramStatus
from app.schemas.template import TemplateDefinition
from app.services.program.selection import SelectionContext, select_for_slot


def _base_load_for(rule, required_inputs: dict) -> float | None:
    # required_inputs keyed by movement pattern seed key (e.g. "squat_start"); applies_to matched by caller upstream
    for key, value in required_inputs.items():
        if rule.pattern and key.startswith(rule.pattern.split("_")[0]):
            return float(value)
    return None


def build_draft(template, definition: TemplateDefinition, ctx: SelectionContext, exercises, *,
                user_id: int, environment_id: int, days_per_week: int, duration_weeks: int,
                weight_unit: str, required_inputs: dict) -> WorkoutProgram:
    program = WorkoutProgram(
        user_id=user_id, template_id=template.id, environment_id=environment_id,
        name=template.name, focus=(template.goals[0] if template.goals else None),
        status=ProgramStatus.DRAFT, duration_weeks=duration_weeks, days_per_week=days_per_week,
        weight_unit=weight_unit,
        constraints={"locked_slots": [], "excluded_exercise_ids": [], "swaps": {},
                     "volume_adjustments": {}, "required_inputs": required_inputs},
    )
    for session in definition.split.sessions:
        workout = Workout(key=session.key, name=session.name,
                          focus=",".join(filter(None, [s.pattern or s.region for s in session.slots])),
                          order=session.order)
        for i, rule in enumerate(session.slots, start=1):
            scheme = definition.schemes[rule.scheme]
            chosen = select_for_slot(exercises, rule, ctx, None, set())
            if chosen is None:
                continue
            ctx.used_movement_slugs.add(chosen.movement_slug)
            workout.exercises.append(WorkoutExercise(
                order=i, exercise_id=chosen.id, fills_rule=rule.model_dump(),
                sets=scheme.sets, reps_min=scheme.reps_min, reps_max=scheme.reps_max,
                base_load=_base_load_for(rule, required_inputs), rest_seconds=scheme.rest_seconds,
                scheme_key=rule.scheme, is_locked=False, is_user_swapped=False,
            ))
        program.workouts.append(workout)
    return program
```

- [ ] **Step 4: Implement preview/derive**

```python
# backend/app/services/program/preview.py
from app.schemas.template import TemplateDefinition
from app.services.program.progression import apply_deload, get_model
from app.services.program.progression.base import SlotBase


def derive_week(program, definition: TemplateDefinition, week: int) -> list[dict]:
    model = get_model(definition.progression.model_key)
    every = definition.progression.deload_every
    params = definition.progression.params
    days = []
    for workout in program.workouts:
        slots = []
        for ex in workout.exercises:
            base = SlotBase(sets=ex.sets, reps_min=ex.reps_min, reps_max=ex.reps_max,
                            rest_seconds=ex.rest_seconds, base_load=ex.base_load)
            scheme = apply_deload(model.resolve(base, week, params), week, every)
            slots.append({
                "workout_exercise_id": ex.id, "exercise_id": ex.exercise_id,
                "sets": scheme.sets, "reps": scheme.reps, "load": scheme.load,
                "rest_seconds": scheme.rest_seconds, "note": scheme.note,
                "is_locked": ex.is_locked, "is_user_swapped": ex.is_user_swapped,
            })
        days.append({"workout_id": workout.id, "key": workout.key, "name": workout.name, "slots": slots})
    return days
```

- [ ] **Step 5: Write the preview test**

```python
# backend/tests/test_preview.py
import pytest
from app.schemas.template import TemplateDefinition
from app.services.program.selection import SelectionContext
from app.services.program.drafting import build_draft
from app.services.program.preview import derive_week


@pytest.mark.asyncio
async def test_derive_week_applies_progression(sample_template_orm, sample_exercises):
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(["barbell", "bench", "squat_rack"], "intermediate", [], set())
    program = build_draft(sample_template_orm, definition, ctx, sample_exercises,
                          user_id=1, environment_id=1, days_per_week=3, duration_weeks=8,
                          weight_unit="kg", required_inputs={"squat_start": 80})
    for w in program.workouts:  # give ids so derive output is stable
        w.id = w.order
        for j, ex in enumerate(w.exercises, 1):
            ex.id = j
    w1 = derive_week(program, definition, 1)
    w2 = derive_week(program, definition, 2)
    load1 = next((s["load"] for d in w1 for s in d["slots"] if s["load"] is not None), None)
    load2 = next((s["load"] for d in w2 for s in d["slots"] if s["load"] is not None), None)
    assert load2 > load1  # progression increased load week over week
```

- [ ] **Step 6: Run both test files → PASS.**

- [ ] **Step 7: Commit** — `git commit -m "feat(program): drafting and per-week derivation"`

---

### Task 14: Adaptation service (feedback actions)

**Files:**
- Create: `backend/app/services/program/adaptation.py`, `backend/app/services/program/feedback_parser.py`
- Test: `backend/tests/test_adaptation.py`

**Interfaces:**
- Consumes: a persisted `WorkoutProgram` (with workouts/exercises), `TemplateDefinition`, exercises, `SelectionContext`.
- Produces:
  - `FeedbackAction` (Pydantic: `type: str` in {`swap`,`exclude`,`regenerate`,`adjust_volume`,`lock`}, `workout_exercise_id: int | None`, `exercise_id: int | None`, `workout_key: str | None`, `delta: int | None`).
  - `FeedbackParser` protocol + `StructuredFeedbackParser.parse(payload: dict) -> FeedbackAction` (the LLM-ready seam).
  - `apply_feedback(program, definition, action, ctx, exercises) -> WorkoutProgram` — mutates `program.constraints` and re-selects affected slots, never touching locked slots.
  - `alternatives_for_slot(program, definition, workout_exercise_id, ctx, exercises) -> list` of valid substitute exercises.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_adaptation.py
import pytest
from app.schemas.template import TemplateDefinition
from app.services.program.selection import SelectionContext
from app.services.program.drafting import build_draft
from app.services.program.adaptation import FeedbackAction, apply_feedback


def _program(sample_template_orm, sample_exercises):
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(["barbell", "bench", "squat_rack", "dumbbells"], "intermediate", [], set())
    program = build_draft(sample_template_orm, definition, ctx, sample_exercises,
                          user_id=1, environment_id=1, days_per_week=3, duration_weeks=8,
                          weight_unit="kg", required_inputs={})
    for w in program.workouts:
        w.id = w.order
        for j, ex in enumerate(w.exercises, 1):
            ex.id = w.order * 100 + j
    return definition, ctx, program


@pytest.mark.asyncio
async def test_lock_then_regenerate_preserves_locked(sample_template_orm, sample_exercises):
    definition, ctx, program = _program(sample_template_orm, sample_exercises)
    target = program.workouts[0].exercises[0]
    locked_exercise = target.exercise_id
    apply_feedback(program, definition, FeedbackAction(type="lock", workout_exercise_id=target.id), ctx, sample_exercises)
    apply_feedback(program, definition, FeedbackAction(type="regenerate", workout_exercise_id=target.id), ctx, sample_exercises)
    assert program.workouts[0].exercises[0].exercise_id == locked_exercise
    assert target.id in program.constraints["locked_slots"]


@pytest.mark.asyncio
async def test_exclude_changes_exercise(sample_template_orm, sample_exercises):
    definition, ctx, program = _program(sample_template_orm, sample_exercises)
    target = program.workouts[0].exercises[0]
    original = target.exercise_id
    apply_feedback(program, definition, FeedbackAction(type="exclude", workout_exercise_id=target.id), ctx, sample_exercises)
    assert original in program.constraints["excluded_exercise_ids"]
```
> `sample_exercises` must include ≥2 valid options for the first slot's pattern so `exclude` can pick a different one.

- [ ] **Step 2: Run and confirm failure.**

- [ ] **Step 3: Implement the feedback parser seam**

```python
# backend/app/services/program/feedback_parser.py
from typing import Protocol

from app.services.program.adaptation import FeedbackAction


class FeedbackParser(Protocol):
    def parse(self, payload: dict) -> FeedbackAction: ...


class StructuredFeedbackParser:
    def parse(self, payload: dict) -> FeedbackAction:
        return FeedbackAction(**payload)
```

- [ ] **Step 4: Implement adaptation**

```python
# backend/app/services/program/adaptation.py
from pydantic import BaseModel

from app.schemas.template import SlotRule, TemplateDefinition
from app.services.program.selection import SelectionContext, select_for_slot


class FeedbackAction(BaseModel):
    type: str
    workout_exercise_id: int | None = None
    exercise_id: int | None = None
    workout_key: str | None = None
    delta: int | None = None


def _find_slot(program, we_id: int):
    for w in program.workouts:
        for ex in w.exercises:
            if ex.id == we_id:
                return w, ex
    return None, None


def _reselect(program, we_id, ctx, exercises):
    _, ex = _find_slot(program, we_id)
    if ex is None or ex.is_locked:
        return
    rule = SlotRule(**ex.fills_rule)
    excluded = set(program.constraints.get("excluded_exercise_ids", []))
    locked = program.constraints.get("swaps", {}).get(str(we_id))
    chosen = select_for_slot(exercises, rule, ctx, locked, excluded)
    if chosen is not None:
        ex.exercise_id = chosen.id


def apply_feedback(program, definition: TemplateDefinition, action: FeedbackAction,
                   ctx: SelectionContext, exercises):
    c = program.constraints
    c.setdefault("locked_slots", []); c.setdefault("excluded_exercise_ids", [])
    c.setdefault("swaps", {}); c.setdefault("volume_adjustments", {})

    if action.type == "lock" and action.workout_exercise_id is not None:
        _, ex = _find_slot(program, action.workout_exercise_id)
        if ex is not None:
            ex.is_locked = True
            if action.workout_exercise_id not in c["locked_slots"]:
                c["locked_slots"].append(action.workout_exercise_id)

    elif action.type == "swap" and action.workout_exercise_id is not None and action.exercise_id is not None:
        _, ex = _find_slot(program, action.workout_exercise_id)
        if ex is not None and not ex.is_locked:
            c["swaps"][str(action.workout_exercise_id)] = action.exercise_id
            ex.exercise_id = action.exercise_id
            ex.is_user_swapped = True

    elif action.type == "exclude" and action.workout_exercise_id is not None:
        _, ex = _find_slot(program, action.workout_exercise_id)
        if ex is not None and not ex.is_locked:
            if ex.exercise_id not in c["excluded_exercise_ids"]:
                c["excluded_exercise_ids"].append(ex.exercise_id)
            _reselect(program, action.workout_exercise_id, ctx, exercises)

    elif action.type == "regenerate" and action.workout_exercise_id is not None:
        _reselect(program, action.workout_exercise_id, ctx, exercises)

    elif action.type == "adjust_volume" and action.workout_key and action.delta is not None:
        c["volume_adjustments"][action.workout_key] = (
            c["volume_adjustments"].get(action.workout_key, 0) + action.delta
        )
        for w in program.workouts:
            if w.key == action.workout_key:
                for ex in w.exercises:
                    ex.sets = max(1, ex.sets + action.delta)

    # SQLAlchemy needs a new dict object to detect the JSON mutation
    program.constraints = dict(c)
    return program


def alternatives_for_slot(program, definition, workout_exercise_id, ctx, exercises):
    _, ex = _find_slot(program, workout_exercise_id)
    if ex is None:
        return []
    rule = SlotRule(**ex.fills_rule)
    from app.services.program.selection import _matches_rule, _passes_filters
    return [e for e in exercises if _matches_rule(e, rule) and _passes_filters(e, ctx) and e.id != ex.exercise_id]
```

- [ ] **Step 5: Run tests → PASS.** `pytest tests/test_adaptation.py -v`

- [ ] **Step 6: Commit** — `git commit -m "feat(program): feedback adaptation + parser seam"`

---

### Task 15: Program exceptions + API schemas

**Files:**
- Modify: `backend/app/core/exceptions.py`, `backend/app/core/__init__.py`
- Create: `backend/app/schemas/program_api.py`
- Modify: `backend/app/schemas/__init__.py`
- Test: `backend/tests/test_program_api_schemas.py`

**Interfaces:**
- Produces: `ProgramTemplateNotFoundError`, `ProgramNotFoundError` (both `AppException`, 404). API schemas: `MatchRequest`, `TemplateMatchOut`, `DraftRequest`, `FeedbackRequest`, `ProgramPreviewOut`, `SlotPreviewOut`, `WorkoutPreviewOut`, `AlternativeOut`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_program_api_schemas.py
from app.schemas.program_api import DraftRequest, MatchRequest


def test_match_request_defaults():
    r = MatchRequest(environment_id=1, days_per_week=4, session_duration_min=60,
                     fitness_focus="strength", weight_unit="kg", duration_weeks=8)
    assert r.duration_weeks == 8


def test_draft_request_carries_required_inputs():
    r = DraftRequest(template_id=2, environment_id=1, days_per_week=4, session_duration_min=60,
                     fitness_focus="strength", weight_unit="kg", duration_weeks=8,
                     required_inputs={"squat_start": 80})
    assert r.required_inputs["squat_start"] == 80
```

- [ ] **Step 2: Run and confirm failure.**

- [ ] **Step 3: Add exceptions**

```python
# append to backend/app/core/exceptions.py
class ProgramTemplateNotFoundError(AppException):
    error_code: str = "PROGRAM_TEMPLATE_NOT_FOUND"
    def __init__(self, message: str = "Program template not found"):
        super().__init__(message, status_code=404)


class ProgramNotFoundError(AppException):
    error_code: str = "PROGRAM_NOT_FOUND"
    def __init__(self, message: str = "Program not found"):
        super().__init__(message, status_code=404)
```
Re-export both from `backend/app/core/__init__.py` alongside the existing exception exports.

- [ ] **Step 4: Add API schemas**

```python
# backend/app/schemas/program_api.py
from pydantic import BaseModel, ConfigDict


class MatchRequest(BaseModel):
    environment_id: int
    days_per_week: int
    session_duration_min: int
    fitness_focus: str
    weight_unit: str = "kg"
    duration_weeks: int = 8


class TemplateMatchOut(BaseModel):
    template_id: int
    slug: str
    name: str
    fit_pct: int
    factors: dict
    required_inputs: list


class DraftRequest(MatchRequest):
    template_id: int
    required_inputs: dict = {}


class FeedbackRequest(BaseModel):
    type: str
    workout_exercise_id: int | None = None
    exercise_id: int | None = None
    workout_key: str | None = None
    delta: int | None = None


class SlotPreviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    workout_exercise_id: int
    exercise_id: int
    sets: int
    reps: int
    load: float | None
    rest_seconds: int
    note: str | None
    is_locked: bool
    is_user_swapped: bool


class WorkoutPreviewOut(BaseModel):
    workout_id: int
    key: str
    name: str
    slots: list[SlotPreviewOut]


class ProgramPreviewOut(BaseModel):
    program_id: int
    name: str
    status: str
    duration_weeks: int
    weeks: dict[int, list[WorkoutPreviewOut]]


class AlternativeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    slug: str
```
Export all from `backend/app/schemas/__init__.py`.

- [ ] **Step 5: Run tests → PASS.**

- [ ] **Step 6: Commit** — `git commit -m "feat(program): api schemas + program exceptions"`

---

### Task 16: API endpoints — match, draft, preview, feedback, alternatives, accept

**Files:**
- Rewrite: `backend/app/api/v1/endpoints/programs.py`
- Test: `backend/tests/test_programs_flow.py` (replaces/extends `test_programs_stub.py`)

**Interfaces:**
- Consumes: everything above. Uses `get_current_user`, `get_db`, `crud.program`, `crud.exercise` (list all active exercises), `crud.training_environment.get_training_environment`.
- Produces endpoints:
  - `POST /programs/match` → `list[TemplateMatchOut]`
  - `POST /programs/draft` → `ProgramPreviewOut` (status draft)
  - `GET /programs/{id}/preview` → `ProgramPreviewOut`
  - `POST /programs/{id}/feedback` → `ProgramPreviewOut`
  - `GET /programs/{id}/slots/{we_id}/alternatives` → `list[AlternativeOut]`
  - `POST /programs/{id}/accept` → `ProgramPreviewOut` (status active)
  - `GET /programs/{id}` → `ProgramPreviewOut`

- [ ] **Step 1: Write the failing integration test**

```python
# backend/tests/test_programs_flow.py
import pytest


@pytest.mark.asyncio
async def test_full_flow(client, auth_headers, seeded_templates, seeded_exercises, user_environment):
    # 1. match
    body = {"environment_id": user_environment.id, "days_per_week": 3, "session_duration_min": 60,
            "fitness_focus": "strength", "weight_unit": "kg", "duration_weeks": 8}
    r = await client.post("/api/v1/programs/match", json=body, headers=auth_headers)
    assert r.status_code == 200
    matches = r.json()
    assert matches and "fit_pct" in matches[0]

    # 2. draft
    draft_body = {**body, "template_id": matches[0]["template_id"], "required_inputs": {"squat_start": 80}}
    r = await client.post("/api/v1/programs/draft", json=draft_body, headers=auth_headers)
    assert r.status_code == 201
    program = r.json()
    pid = program["program_id"]
    assert program["status"] == "draft"
    assert 1 in {int(k) for k in program["weeks"].keys()}

    # 3. feedback: lock first slot
    we_id = program["weeks"]["1"][0]["slots"][0]["workout_exercise_id"]
    r = await client.post(f"/api/v1/programs/{pid}/feedback",
                          json={"type": "lock", "workout_exercise_id": we_id}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["weeks"]["1"][0]["slots"][0]["is_locked"] is True

    # 4. accept
    r = await client.post(f"/api/v1/programs/{pid}/accept", headers=auth_headers)
    assert r.status_code == 200 and r.json()["status"] == "active"
```
> Add fixtures to `conftest.py`: `auth_headers` (reuse `test_user_token`), `seeded_templates` (call `seed_program_templates`), `seeded_exercises` (seed a subset of the exercise library sufficient for the beginner full-body template), `user_environment` (a `TrainingEnvironment` for `test_user` with equipment covering the template).

- [ ] **Step 2: Run and confirm failure.**

- [ ] **Step 3: Implement the endpoints**

```python
# backend/app/api/v1/endpoints/programs.py
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_user
from app.core import (
    ProgramNotFoundError, ProgramTemplateNotFoundError, TrainingEnvironmentNotFoundError,
)
from app.core.database import get_db
from app.crud.exercise import list_exercises  # existing; returns active Exercise rows
from app.crud.program import get_program, get_template, list_active_templates, save_program
from app.crud.training_environment import get_training_environment
from app.models import ProgramStatus, User
from app.schemas.program_api import (
    AlternativeOut, DraftRequest, FeedbackRequest, MatchRequest,
    ProgramPreviewOut, TemplateMatchOut, WorkoutPreviewOut,
)
from app.schemas.template import TemplateDefinition
from app.services.program.adaptation import FeedbackAction, alternatives_for_slot, apply_feedback
from app.services.program.drafting import build_draft
from app.services.program.matching import MatchInput, rank_templates
from app.services.program.preview import derive_week
from app.services.program.selection import SelectionContext, template_is_feasible

router = APIRouter(prefix="/programs", tags=["programs"])


async def _ctx_for(db, user: User, environment) -> SelectionContext:
    profile = user.profile
    injuries = []
    if profile and profile.injuries_limitations:
        injuries = [w.strip().lower() for w in profile.injuries_limitations.split(",") if w.strip()]
    experience = profile.experience_level.value if profile and profile.experience_level else "beginner"
    return SelectionContext(list(environment.equipment_tags), experience, injuries, set())


def _preview_out(program, definition) -> ProgramPreviewOut:
    weeks = {w: [WorkoutPreviewOut(**day) for day in derive_week(program, definition, w)]
             for w in range(1, program.duration_weeks + 1)}
    return ProgramPreviewOut(program_id=program.id, name=program.name, status=program.status.value,
                             duration_weeks=program.duration_weeks, weeks=weeks)


@router.post("/match", response_model=list[TemplateMatchOut])
async def match(data: MatchRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    environment = await get_training_environment(db, user.id, data.environment_id)
    if environment is None:
        raise TrainingEnvironmentNotFoundError()
    templates = await list_active_templates(db)
    exercises = await list_exercises(db)
    feasibility = {}
    definitions = {}
    for t in templates:
        d = TemplateDefinition.from_orm_template(t)
        definitions[t.id] = d
        feasibility[t.id] = template_is_feasible(d.split.sessions, exercises, environment.equipment_tags)
    profile = user.profile
    inp = MatchInput(data.fitness_focus,
                     profile.experience_level.value if profile and profile.experience_level else "beginner",
                     data.days_per_week, data.session_duration_min, list(environment.equipment_tags))
    ranked = rank_templates(templates, inp, feasibility)
    return [TemplateMatchOut(**m.__dict__, required_inputs=[r.model_dump() for r in definitions[m.template_id].required_inputs])
            for m in ranked]


@router.post("/draft", response_model=ProgramPreviewOut, status_code=status.HTTP_201_CREATED)
async def draft(data: DraftRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    environment = await get_training_environment(db, user.id, data.environment_id)
    if environment is None:
        raise TrainingEnvironmentNotFoundError()
    template = await get_template(db, data.template_id)
    if template is None or not template.is_active:
        raise ProgramTemplateNotFoundError()
    definition = TemplateDefinition.from_orm_template(template)
    ctx = await _ctx_for(db, user, environment)
    exercises = await list_exercises(db)
    program = build_draft(template, definition, ctx, exercises, user_id=user.id,
                          environment_id=environment.id, days_per_week=data.days_per_week,
                          duration_weeks=data.duration_weeks, weight_unit=data.weight_unit,
                          required_inputs=data.required_inputs)
    await save_program(db, program)
    program = await get_program(db, user.id, program.id)
    return _preview_out(program, definition)


async def _load(db, user, program_id):
    program = await get_program(db, user.id, program_id)
    if program is None:
        raise ProgramNotFoundError()
    template = await get_template(db, program.template_id)
    return program, TemplateDefinition.from_orm_template(template)


@router.get("/{program_id}", response_model=ProgramPreviewOut)
async def get_one(program_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    program, definition = await _load(db, user, program_id)
    return _preview_out(program, definition)


@router.get("/{program_id}/preview", response_model=ProgramPreviewOut)
async def preview(program_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    program, definition = await _load(db, user, program_id)
    return _preview_out(program, definition)


@router.post("/{program_id}/feedback", response_model=ProgramPreviewOut)
async def feedback(program_id: int, data: FeedbackRequest, user: User = Depends(get_current_user),
                   db: AsyncSession = Depends(get_db)):
    program, definition = await _load(db, user, program_id)
    environment = await get_training_environment(db, user.id, program.environment_id)
    ctx = await _ctx_for(db, user, environment)
    exercises = await list_exercises(db)
    apply_feedback(program, definition, FeedbackAction(**data.model_dump()), ctx, exercises)
    await save_program(db, program)
    program = await get_program(db, user.id, program.id)
    return _preview_out(program, definition)


@router.get("/{program_id}/slots/{we_id}/alternatives", response_model=list[AlternativeOut])
async def alternatives(program_id: int, we_id: int, user: User = Depends(get_current_user),
                       db: AsyncSession = Depends(get_db)):
    program, definition = await _load(db, user, program_id)
    environment = await get_training_environment(db, user.id, program.environment_id)
    ctx = await _ctx_for(db, user, environment)
    exercises = await list_exercises(db)
    return alternatives_for_slot(program, definition, we_id, ctx, exercises)


@router.post("/{program_id}/accept", response_model=ProgramPreviewOut)
async def accept(program_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    program, definition = await _load(db, user, program_id)
    program.status = ProgramStatus.ACTIVE
    await save_program(db, program)
    return _preview_out(program, definition)
```
> Verify `app.crud.exercise` exposes an active-exercise lister; if the name differs from `list_exercises`, use the existing one. Ensure `get_current_user` eager-loads `user.profile` (it is a lazy relationship) — if not, load the profile explicitly inside `_ctx_for` via a crud call.

- [ ] **Step 4: Run the flow test → PASS.** `pytest tests/test_programs_flow.py -v`

- [ ] **Step 5: Delete the obsolete stub test**

Remove `backend/tests/test_programs_stub.py` (the 501 behavior no longer exists).

- [ ] **Step 6: Run the whole suite + quality gates**

```bash
docker-compose exec backend pytest
docker-compose exec backend ruff check . --fix
docker-compose exec backend black .
docker-compose exec backend mypy app/
```
Expected: all green.

- [ ] **Step 7: Commit** — `git commit -m "feat(program): program generation endpoints (match/draft/feedback/accept)"`

---

## Self-Review (backend)

- **Spec coverage:** §2 layered template → Tasks 1,3,9. §3 storage split → Tasks 1,9 + progression Tasks 4–8. §4 data model + base-week-derive → Tasks 1,13. §5 matching → Task 10. §6 selection → Task 11. §7 feedback → Task 14,16. §8 endpoints → Task 16. §9 services layout → Tasks 4–14. §10 testing → every task is TDD; integration in Task 16. §12 seed catalog → Task 9. §13 migration → Task 2.
- **Deferred to later plans:** Frontend (§11) → Plan 2. Docs (§12 authoring UI is future-only; technical/user HTML) → Plan 3.
- **Type consistency:** `SetScheme`/`SlotBase` used identically across progression tasks; `SelectionContext`, `SlotRule`, `TemplateDefinition`, `FeedbackAction`, `derive_week` signatures match between producer and consumer tasks.

**Known verification points for the implementer** (surfaced, not hidden): exact `async_session_maker`/exercise-lister names (Tasks 9, 16) and whether `get_current_user` eager-loads `profile` (Task 16) must be confirmed against the codebase during execution.
