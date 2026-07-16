# Smarter Program Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close three gaps in MyGym's program generation engine: brittle free-form exercise tags, a dead-code progression-style preference, and no effort-measurement concept — making generated programs measurably smarter and more personalized.

**Architecture:** Three independently-shippable phases against the existing `backend/app/services/program/` pipeline (matching → selection → drafting → preview). Phase 1 hardens exercise data (canonical enums + two new boolean attributes) and feeds it into `selection.py` scoring. Phase 2 wires an already-defined-but-unused `ProgressionStyle` enum end-to-end as a per-program override applied at preview/draft time. Phase 3 adds an `EffortMethod` preference that changes what the drafter asks for (a 1RM vs. a working weight) and what the preview shows per set.

**Tech Stack:** FastAPI + Pydantic V2 + SQLAlchemy 2.0 async + Alembic (backend), React + TypeScript + Vitest (frontend), pytest + pytest-asyncio (backend tests).

## Global Constraints

- TDD: write the failing test before the implementation for every step below.
- Backend: `docker-compose exec backend pytest`, `docker-compose exec backend ruff check . --fix`, `docker-compose exec backend mypy app/`.
- Frontend: `docker-compose exec frontend npm run test:watch`, `docker-compose exec frontend npm run type-check`.
- Every schema/behavior addition must be backward compatible: omitting a new field must reproduce today's exact behavior (existing tests in `backend/tests/test_drafting.py`, `test_preview.py`, `test_selection.py`, `test_program_api_schemas.py` must keep passing unmodified except where a task explicitly edits them).
- Alembic migrations must be reversible (`upgrade` and `downgrade` both implemented).
- Commit after every task (not every step) with a `feat(program-engine): ...` or `feat(program-ui): ...` prefix, matching this repo's existing commit style (see `git log`).

---

## Phase 1 — Exercise taxonomy & matching quality

### Task 1: Canonical enums + `is_unilateral`/`is_compound` on `Exercise`

**Files:**
- Modify: `backend/app/models/exercise.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/alembic/versions/c8d9e0f1a2b3_merge_heads_add_exercise_flags.py`
- Test: `backend/tests/test_exercise_model.py`

**Interfaces:**
- Produces: `Equipment`, `Muscle`, `Contraindication` (str enums) and `Exercise.is_unilateral: bool`, `Exercise.is_compound: bool`, both exported from `app.models`.

**Context:** `alembic heads` currently reports two unmerged heads (`a7c903edb637` and `b2c3d4e5f6a7`), both descending from `a1b2c3d4e5f6`. `alembic upgrade head` fails ambiguously until they're merged. This migration merges them and adds the two new columns in the same step.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_exercise_model.py
from app.models.exercise import Contraindication, Equipment, Exercise, Muscle


def test_equipment_enum_covers_all_seeded_values():
    seeded = {
        "ab_wheel", "assault_bike", "assisted_dip_machine", "assisted_pullup_machine", "barbell",
        "battle_ropes", "bench", "cable_machine", "calf_raise_machine", "chest_press_machine",
        "dumbbells", "ez_bar", "gymnastic_rings", "hack_squat_machine", "hip_abduction_machine",
        "hip_adduction_machine", "jump_rope", "kettlebell", "lat_pulldown_machine", "leg_curl_machine",
        "leg_extension_machine", "leg_press_machine", "medicine_ball", "none", "pec_deck_machine",
        "plyo_box", "pull_up_bar", "resistance_bands", "rowing_machine", "sandbag", "seated_row_machine",
        "shoulder_press_machine", "sled", "smith_machine", "squat_rack", "stair_climber",
        "stationary_bike", "treadmill",
    }
    assert seeded <= {e.value for e in Equipment}


def test_muscle_enum_covers_all_seeded_values():
    seeded = {
        "abs", "biceps", "calves", "cardio", "chest", "deep_core", "forearms", "glutes", "hamstrings",
        "hip_abductors", "hip_adductors", "hip_flexors", "lats", "lower_back", "obliques", "quads",
        "shoulders_anterior", "shoulders_lateral", "shoulders_posterior", "traps", "triceps", "upper_back",
    }
    assert seeded <= {m.value for m in Muscle}


def test_contraindication_enum_covers_all_seeded_values():
    seeded = {"ankle", "elbow", "hip", "knee", "lower_back", "neck", "shoulder", "wrist"}
    assert seeded <= {c.value for c in Contraindication}


def test_exercise_has_unilateral_and_compound_flags():
    columns = Exercise.__table__.columns
    assert "is_unilateral" in columns
    assert "is_compound" in columns
    assert columns["is_unilateral"].nullable is False
    assert columns["is_compound"].nullable is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker-compose exec backend pytest tests/test_exercise_model.py -v`
Expected: FAIL with `ImportError: cannot import name 'Equipment'`

- [ ] **Step 3: Add the enums and columns**

In `backend/app/models/exercise.py`, add after `MovementPattern`:

```python
class Equipment(str, enum.Enum):
    AB_WHEEL = "ab_wheel"
    ASSAULT_BIKE = "assault_bike"
    ASSISTED_DIP_MACHINE = "assisted_dip_machine"
    ASSISTED_PULLUP_MACHINE = "assisted_pullup_machine"
    BARBELL = "barbell"
    BATTLE_ROPES = "battle_ropes"
    BENCH = "bench"
    CABLE_MACHINE = "cable_machine"
    CALF_RAISE_MACHINE = "calf_raise_machine"
    CHEST_PRESS_MACHINE = "chest_press_machine"
    DUMBBELLS = "dumbbells"
    EZ_BAR = "ez_bar"
    GYMNASTIC_RINGS = "gymnastic_rings"
    HACK_SQUAT_MACHINE = "hack_squat_machine"
    HIP_ABDUCTION_MACHINE = "hip_abduction_machine"
    HIP_ADDUCTION_MACHINE = "hip_adduction_machine"
    JUMP_ROPE = "jump_rope"
    KETTLEBELL = "kettlebell"
    LAT_PULLDOWN_MACHINE = "lat_pulldown_machine"
    LEG_CURL_MACHINE = "leg_curl_machine"
    LEG_EXTENSION_MACHINE = "leg_extension_machine"
    LEG_PRESS_MACHINE = "leg_press_machine"
    MEDICINE_BALL = "medicine_ball"
    NONE = "none"
    PEC_DECK_MACHINE = "pec_deck_machine"
    PLYO_BOX = "plyo_box"
    PULL_UP_BAR = "pull_up_bar"
    RESISTANCE_BANDS = "resistance_bands"
    ROWING_MACHINE = "rowing_machine"
    SANDBAG = "sandbag"
    SEATED_ROW_MACHINE = "seated_row_machine"
    SHOULDER_PRESS_MACHINE = "shoulder_press_machine"
    SLED = "sled"
    SMITH_MACHINE = "smith_machine"
    SQUAT_RACK = "squat_rack"
    STAIR_CLIMBER = "stair_climber"
    STATIONARY_BIKE = "stationary_bike"
    TREADMILL = "treadmill"


class Muscle(str, enum.Enum):
    ABS = "abs"
    BICEPS = "biceps"
    CALVES = "calves"
    CARDIO = "cardio"
    CHEST = "chest"
    DEEP_CORE = "deep_core"
    FOREARMS = "forearms"
    GLUTES = "glutes"
    HAMSTRINGS = "hamstrings"
    HIP_ABDUCTORS = "hip_abductors"
    HIP_ADDUCTORS = "hip_adductors"
    HIP_FLEXORS = "hip_flexors"
    LATS = "lats"
    LOWER_BACK = "lower_back"
    OBLIQUES = "obliques"
    QUADS = "quads"
    SHOULDERS_ANTERIOR = "shoulders_anterior"
    SHOULDERS_LATERAL = "shoulders_lateral"
    SHOULDERS_POSTERIOR = "shoulders_posterior"
    TRAPS = "traps"
    TRICEPS = "triceps"
    UPPER_BACK = "upper_back"


class Contraindication(str, enum.Enum):
    ANKLE = "ankle"
    ELBOW = "elbow"
    HIP = "hip"
    KNEE = "knee"
    LOWER_BACK = "lower_back"
    NECK = "neck"
    SHOULDER = "shoulder"
    WRIST = "wrist"
```

In the `Exercise` class body, add after `contraindications`:

```python
    is_unilateral: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_compound: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
```

(`equipment_tags`, `primary_muscles`, `secondary_muscles`, `contraindications` keep their existing `Mapped[list[str]]` JSON column type — validation against the new enums happens at the seed layer in Task 2 and the API schema layer in Task 3, not the DB column type, so no migration is needed for those four columns.)

In `backend/app/models/__init__.py`, update the exercise import and `__all__`:

```python
from .exercise import BodyRegion, Contraindication, Equipment, Exercise, Muscle, MovementPattern
```

Add `"Equipment"`, `"Muscle"`, `"Contraindication"` to `__all__`.

- [ ] **Step 4: Write the merge + add-columns migration**

```python
# backend/alembic/versions/c8d9e0f1a2b3_merge_heads_add_exercise_flags.py
"""merge heads and add exercise is_unilateral/is_compound flags

Revision ID: c8d9e0f1a2b3
Revises: a7c903edb637, b2c3d4e5f6a7
Create Date: 2026-07-16 09:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c8d9e0f1a2b3"
down_revision: Union[str, Sequence[str], None] = ("a7c903edb637", "b2c3d4e5f6a7")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "exercises",
        sa.Column("is_unilateral", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "exercises",
        sa.Column("is_compound", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column("exercises", "is_unilateral", server_default=None)
    op.alter_column("exercises", "is_compound", server_default=None)


def downgrade() -> None:
    op.drop_column("exercises", "is_compound")
    op.drop_column("exercises", "is_unilateral")
```

- [ ] **Step 5: Run test to verify it passes**

Run: `docker-compose exec backend pytest tests/test_exercise_model.py -v`
Expected: PASS (4 tests)

- [ ] **Step 6: Verify migration reversibility**

Run: `docker-compose exec backend uv run alembic upgrade head && docker-compose exec backend uv run alembic downgrade -1 && docker-compose exec backend uv run alembic upgrade head`
Expected: all three commands exit 0, and `docker-compose exec backend uv run alembic heads` now shows a single head `c8d9e0f1a2b3`.

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/exercise.py backend/app/models/__init__.py backend/alembic/versions/c8d9e0f1a2b3_merge_heads_add_exercise_flags.py backend/tests/test_exercise_model.py
git commit -m "feat(program-engine): add canonical exercise tag enums and is_unilateral/is_compound flags"
```

---

### Task 2: Classify + validate seed exercises at upsert time

**Files:**
- Create: `backend/app/db/seed/exercise_classification.py`
- Modify: `backend/app/db/seed/seed_exercises.py`
- Test: `backend/tests/test_exercise_classification.py`

**Interfaces:**
- Consumes: `Equipment`, `Muscle`, `Contraindication` from `app.models.exercise` (Task 1), `MovementPattern` from `app.models.exercise`.
- Produces: `classify_exercise(data: dict[str, object]) -> tuple[bool, bool]` (returns `(is_unilateral, is_compound)`), `validate_tags(data: dict[str, object]) -> None` (raises `ValueError` on an unrecognized tag), both importable from `app.db.seed.exercise_classification`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_exercise_classification.py
import pytest

from app.db.seed.exercise_classification import classify_exercise, validate_tags
from app.db.seed.exercises import EXERCISE_SEED_DATA


def test_classifies_bilateral_compound_squat():
    data = {"name": "Barbell Back Squat", "movement_pattern": "SQUAT"}
    assert classify_exercise(data) == (False, True)


def test_classifies_unilateral_compound_hinge():
    data = {"name": "Single-Leg Dumbbell Romanian Deadlift", "movement_pattern": "HINGE"}
    assert classify_exercise(data) == (True, True)


def test_classifies_unilateral_compound_row():
    data = {"name": "Single-Arm Dumbbell Row", "movement_pattern": "HORIZONTAL_PULL"}
    assert classify_exercise(data) == (True, True)


def test_classifies_bilateral_isolation_curl():
    data = {"name": "Dumbbell Bicep Curl", "movement_pattern": "ISOLATION"}
    assert classify_exercise(data) == (False, False)


def test_classifies_split_squat_as_unilateral():
    data = {"name": "Bulgarian Split Squat", "movement_pattern": "LUNGE"}
    assert classify_exercise(data) == (True, True)


def test_validate_tags_accepts_known_values():
    validate_tags(
        {
            "slug": "test-ex",
            "equipment_tags": ["barbell", "bench"],
            "primary_muscles": ["chest"],
            "secondary_muscles": ["triceps"],
            "contraindications": ["shoulder"],
        }
    )  # should not raise


def test_validate_tags_rejects_unknown_equipment():
    with pytest.raises(ValueError, match="unknown-equipment"):
        validate_tags(
            {
                "slug": "test-ex",
                "equipment_tags": ["unknown-equipment"],
                "primary_muscles": [],
                "secondary_muscles": [],
                "contraindications": [],
            }
        )


def test_all_seed_exercises_pass_tag_validation():
    for data in EXERCISE_SEED_DATA:
        validate_tags(data)  # should not raise for any of the 148 seeded exercises
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker-compose exec backend pytest tests/test_exercise_classification.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.db.seed.exercise_classification'`

- [ ] **Step 3: Write the classification + validation module**

```python
# backend/app/db/seed/exercise_classification.py
from app.models.exercise import Contraindication, Equipment, Muscle, MovementPattern

_UNILATERAL_KEYWORDS = (
    "single-leg",
    "single leg",
    "single-arm",
    "single arm",
    "one-arm",
    "one arm",
    "one-leg",
    "one leg",
    "alternating",
    "split squat",
    "step-up",
    "step up",
    "pistol",
    "unilateral",
    "lunge",
)

_NON_COMPOUND_PATTERNS = {
    MovementPattern.ISOLATION,
    MovementPattern.ROTATION,
    MovementPattern.ANTI_ROTATION,
    MovementPattern.MOBILITY,
}

_VALID_EQUIPMENT = {e.value for e in Equipment}
_VALID_MUSCLES = {m.value for m in Muscle}
_VALID_CONTRAINDICATIONS = {c.value for c in Contraindication}


def classify_exercise(data: dict[str, object]) -> tuple[bool, bool]:
    """Derive (is_unilateral, is_compound) from an exercise's name and movement pattern."""
    name = str(data["name"]).lower()
    is_unilateral = any(keyword in name for keyword in _UNILATERAL_KEYWORDS)
    pattern = MovementPattern[str(data["movement_pattern"])]
    is_compound = pattern not in _NON_COMPOUND_PATTERNS
    return is_unilateral, is_compound


def validate_tags(data: dict[str, object]) -> None:
    """Raise ValueError if any equipment/muscle/contraindication tag isn't in the canonical vocabulary."""
    invalid_equipment = set(data.get("equipment_tags", [])) - _VALID_EQUIPMENT  # type: ignore[arg-type]
    invalid_primary = set(data.get("primary_muscles", [])) - _VALID_MUSCLES  # type: ignore[arg-type]
    invalid_secondary = set(data.get("secondary_muscles", [])) - _VALID_MUSCLES  # type: ignore[arg-type]
    invalid_contra = set(data.get("contraindications", [])) - _VALID_CONTRAINDICATIONS  # type: ignore[arg-type]
    if invalid_equipment or invalid_primary or invalid_secondary or invalid_contra:
        raise ValueError(
            f"{data.get('slug')}: unrecognized tags - "
            f"equipment_tags={invalid_equipment}, primary_muscles={invalid_primary}, "
            f"secondary_muscles={invalid_secondary}, contraindications={invalid_contra}"
        )
```

- [ ] **Step 4: Wire classification + validation into the upsert**

In `backend/app/db/seed/seed_exercises.py`, add the import and call both helpers before constructing/updating each `Exercise`:

```python
from app.db.seed.exercise_classification import classify_exercise, validate_tags
```

Replace the loop body:

```python
    for data in EXERCISE_SEED_DATA:
        validate_tags(data)
        is_unilateral, is_compound = classify_exercise(data)
        row = {**data, "is_unilateral": is_unilateral, "is_compound": is_compound}

        existing = await db.execute(select(Exercise).where(Exercise.slug == data["slug"]))
        exercise = existing.scalar_one_or_none()

        if exercise is None:
            exercise = Exercise(**row, is_active=True)
            db.add(exercise)
        else:
            for key, value in row.items():
                setattr(exercise, key, value)
            exercise.is_active = True
            db.add(exercise)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `docker-compose exec backend pytest tests/test_exercise_classification.py -v`
Expected: PASS (7 tests)

- [ ] **Step 6: Run the full existing seed/drafting/preview/selection suite to confirm no regression**

Run: `docker-compose exec backend pytest tests/test_drafting.py tests/test_preview.py tests/test_selection.py -v`
Expected: PASS (all existing tests, unmodified)

- [ ] **Step 7: Commit**

```bash
git add backend/app/db/seed/exercise_classification.py backend/app/db/seed/seed_exercises.py backend/tests/test_exercise_classification.py
git commit -m "feat(program-engine): classify and validate exercises at seed time"
```

---

### Task 3: Expose new fields on `ExerciseResponse`

**Files:**
- Modify: `backend/app/schemas/exercise.py`
- Test: `backend/tests/test_exercise_schema.py`

**Interfaces:**
- Consumes: `Equipment`, `Muscle`, `Contraindication` from `app.models` (Task 1).
- Produces: `ExerciseResponse` now includes `equipment_tags: list[Equipment]`, `primary_muscles: list[Muscle]`, `secondary_muscles: list[Muscle]`, `contraindications: list[Contraindication]`, `is_unilateral: bool`, `is_compound: bool`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_exercise_schema.py
from datetime import datetime

import pytest
from pydantic import ValidationError

from app.schemas.exercise import ExerciseResponse


def _base_kwargs(**overrides: object) -> dict[str, object]:
    kwargs: dict[str, object] = {
        "id": 1,
        "name": "Barbell Back Squat",
        "slug": "barbell-back-squat",
        "movement_slug": "back_squat",
        "body_region": "lower_body",
        "movement_pattern": "squat",
        "primary_muscles": ["quads", "glutes"],
        "secondary_muscles": ["hamstrings"],
        "equipment_tags": ["barbell", "squat_rack"],
        "difficulty_level": "intermediate",
        "instructions": "Squat down.",
        "form_cues": [],
        "safety_notes": None,
        "contraindications": ["knee"],
        "is_unilateral": False,
        "is_compound": True,
        "created_at": datetime(2026, 1, 1),
        "updated_at": datetime(2026, 1, 1),
    }
    kwargs.update(overrides)
    return kwargs


def test_exercise_response_accepts_valid_tags():
    resp = ExerciseResponse(**_base_kwargs())
    assert resp.is_compound is True
    assert resp.is_unilateral is False


def test_exercise_response_rejects_unknown_equipment_tag():
    with pytest.raises(ValidationError):
        ExerciseResponse(**_base_kwargs(equipment_tags=["not-a-real-tag"]))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker-compose exec backend pytest tests/test_exercise_schema.py -v`
Expected: FAIL — `is_unilateral`/`is_compound` unexpected, and unknown equipment tag doesn't raise (field is still `list[str]`)

- [ ] **Step 3: Update the schema**

```python
# backend/app/schemas/exercise.py
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models import BodyRegion, Contraindication, Equipment, ExperienceLevel, Muscle, MovementPattern


class ExerciseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    movement_slug: str
    body_region: BodyRegion
    movement_pattern: MovementPattern
    primary_muscles: list[Muscle]
    secondary_muscles: list[Muscle]
    equipment_tags: list[Equipment]
    difficulty_level: ExperienceLevel
    instructions: str
    form_cues: list[str]
    safety_notes: str | None
    contraindications: list[Contraindication]
    is_unilateral: bool
    is_compound: bool
    created_at: datetime
    updated_at: datetime
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker-compose exec backend pytest tests/test_exercise_schema.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/exercise.py backend/tests/test_exercise_schema.py
git commit -m "feat(program-engine): validate exercise tags and expose is_unilateral/is_compound in API"
```

---

### Task 4: Compound/unilateral-aware exercise selection scoring

**Files:**
- Modify: `backend/app/services/program/selection.py`
- Modify: `backend/app/services/program/drafting.py`
- Modify: `backend/tests/test_selection.py`

**Interfaces:**
- Consumes: `Exercise.is_compound`, `Exercise.is_unilateral` (Task 1).
- Produces: `SelectionContext.used_unilateral_flags: list[bool]` (new field, default empty list); `_score()` now weighs priority-vs-compound fit and unilateral/bilateral alternation.

- [ ] **Step 1: Write the failing tests**

Replace `backend/tests/test_selection.py` with:

```python
# backend/tests/test_selection.py
from app.schemas.template import SlotRule
from app.services.program.selection import SelectionContext, select_for_slot


class _Ex:
    def __init__(
        self, id, slug, mslug, pattern, region, muscles, equip, diff, contra,
        is_compound=True, is_unilateral=False,
    ):
        self.id, self.slug, self.movement_slug = id, slug, mslug
        self.movement_pattern = type("P", (), {"value": pattern})
        self.body_region = type("R", (), {"value": region})
        self.primary_muscles, self.equipment_tags = muscles, equip
        self.difficulty_level = type("D", (), {"value": diff})
        self.contraindications = contra
        self.is_compound = is_compound
        self.is_unilateral = is_unilateral


def _ctx(equip, injuries=(), used_unilateral_flags=None):
    return SelectionContext(list(equip), "intermediate", list(injuries), set(), used_unilateral_flags or [])


def test_filters_by_equipment_and_injury():
    bench = _Ex(
        1, "bb-bench", "bench", "horizontal_push", "upper_body", ["chest"], ["barbell"], "intermediate", ["shoulder"]
    )
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


def test_primary_slot_prefers_compound_exercise():
    compound = _Ex(
        1, "squat", "squat", "squat", "lower_body", ["quads"], [], "intermediate", [], is_compound=True
    )
    isolation = _Ex(
        2, "leg-ext", "leg_ext", "squat", "lower_body", ["quads"], [], "intermediate", [], is_compound=False
    )
    rule = SlotRule(pattern="squat", priority="primary", scheme="main")
    chosen = select_for_slot([isolation, compound], rule, _ctx([]), None, set())
    assert chosen.id == 1


def test_accessory_slot_prefers_isolation_exercise():
    compound = _Ex(
        1, "squat", "squat", "squat", "lower_body", ["quads"], [], "intermediate", [], is_compound=True
    )
    isolation = _Ex(
        2, "leg-ext", "leg_ext", "squat", "lower_body", ["quads"], [], "intermediate", [], is_compound=False
    )
    rule = SlotRule(pattern="squat", priority="accessory", scheme="accessory")
    chosen = select_for_slot([compound, isolation], rule, _ctx([]), None, set())
    assert chosen.id == 2


def test_penalizes_repeating_unilateral_mode_back_to_back():
    unilateral = _Ex(
        1, "split-squat", "split_squat", "lunge", "lower_body", ["quads"], [], "intermediate", [],
        is_unilateral=True,
    )
    bilateral = _Ex(
        2, "squat", "squat", "lunge", "lower_body", ["quads"], [], "intermediate", [], is_unilateral=False
    )
    rule = SlotRule(pattern="lunge", priority="accessory", scheme="accessory")
    # last pick in the session was already unilateral -> bilateral should win the tie
    chosen = select_for_slot([unilateral, bilateral], rule, _ctx([], used_unilateral_flags=[True]), None, set())
    assert chosen.id == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker-compose exec backend pytest tests/test_selection.py -v`
Expected: FAIL — `SelectionContext` doesn't accept a 5th positional arg, `_score` doesn't use `is_compound`/`is_unilateral`

- [ ] **Step 3: Update `SelectionContext` and `_score`**

In `backend/app/services/program/selection.py`, replace the `SelectionContext` dataclass and `_score`:

```python
from dataclasses import dataclass, field

from app.models.exercise import Exercise
from app.schemas.template import SlotRule

EXPERIENCE_ORDER = {"beginner": 0, "intermediate": 1, "advanced": 2}


@dataclass
class SelectionContext:
    equipment: list[str]
    experience: str
    injuries: list[str]
    used_movement_slugs: set[str]
    used_unilateral_flags: list[bool] = field(default_factory=list)
```

(keep `_matches_rule` and `_passes_filters` unchanged)

```python
def _score(ex: Exercise, rule: SlotRule, ctx: SelectionContext) -> tuple[int, int, int, int, int]:
    muscle_fit = len(set(rule.muscles) & set(ex.primary_muscles))
    variety = 0 if ex.movement_slug in ctx.used_movement_slugs else 1
    diff_gap = -abs(EXPERIENCE_ORDER[ex.difficulty_level.value] - EXPERIENCE_ORDER[ctx.experience])
    priority_fit = 1 if (rule.priority == "primary") == ex.is_compound else 0
    unilateral_balance = 0
    if ctx.used_unilateral_flags and ctx.used_unilateral_flags[-1] == ex.is_unilateral:
        unilateral_balance = -1
    return (variety, priority_fit, muscle_fit, diff_gap, unilateral_balance)
```

Note: `-ex.id` (the previous final tiebreaker) is dropped from the tuple because `_Ex` test doubles and real `Exercise` rows don't always have deterministic ids in tests; ties are now broken by insertion order of `max()`, which is stable and sufficient — no test in this suite or `test_drafting.py`/`test_preview.py` depends on id-based tiebreaking.

- [ ] **Step 4: Record unilateral picks in `build_draft`**

In `backend/app/services/program/drafting.py`, in the slot-fill loop inside `build_draft`, after `ctx.used_movement_slugs.add(chosen.movement_slug)`, add:

```python
            ctx.used_unilateral_flags.append(chosen.is_unilateral)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `docker-compose exec backend pytest tests/test_selection.py -v`
Expected: PASS (5 tests)

- [ ] **Step 6: Run full backend suite to confirm no regression**

Run: `docker-compose exec backend pytest -v`
Expected: PASS (all tests, including `test_drafting.py`, `test_preview.py`, `test_program_api_schemas.py`)

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/program/selection.py backend/app/services/program/drafting.py backend/tests/test_selection.py
git commit -m "feat(program-engine): weight exercise selection by compound/isolation fit and unilateral balance"
```

---

## Phase 2 — Static vs. variable progression (per-program)

### Task 5: `weekly_undulating` falls back to the slot's own rep range

**Files:**
- Modify: `backend/app/services/program/progression/weekly_undulating.py`
- Modify: `backend/tests/test_progression_undulating.py`

**Interfaces:**
- Produces: `WeeklyUndulating.resolve()` now tolerates waves that omit `"reps"`, defaulting to `base.reps_min`. Existing explicit-`"reps"` behavior is unchanged.

**Context:** No seed template uses `weekly_undulating` today, so this contract has zero production callers — safe to extend. Phase 2's override (Task 6) needs to force `weekly_undulating` onto templates whose schemes have rep ranges the override can't know about ahead of time (e.g. main scheme reps 5, accessory reps 10-12, in the same template); an intensity-only wave (reps omitted) sidesteps that mismatch entirely.

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_progression_undulating.py`:

```python
def test_undulating_defaults_reps_to_base_reps_min_when_wave_omits_reps():
    m = WeeklyUndulating()
    base = SlotBase(sets=3, reps_min=10, reps_max=12, rest_seconds=60, base_load=50.0)
    p = {"waves": [{"intensity": 1.0}, {"intensity": 0.85}]}
    assert m.resolve(base, 1, p).reps == 10
    assert m.resolve(base, 2, p).reps == 10
    assert m.resolve(base, 2, p).load == 42.5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker-compose exec backend pytest tests/test_progression_undulating.py -v`
Expected: FAIL with `KeyError: 'reps'`

- [ ] **Step 3: Add the fallback**

In `backend/app/services/program/progression/weekly_undulating.py`, change:

```python
            reps=int(cast(int, wave["reps"])),
```

to:

```python
            reps=int(cast(int, wave.get("reps", base.reps_min))),
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker-compose exec backend pytest tests/test_progression_undulating.py -v`
Expected: PASS (2 tests — the existing `test_undulating_rotates_waves` and the new one)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/program/progression/weekly_undulating.py backend/tests/test_progression_undulating.py
git commit -m "feat(program-engine): weekly_undulating defaults reps to the slot's own range when a wave omits it"
```

---

### Task 6: `apply_progression_style` override helper

**Files:**
- Create: `backend/app/services/program/style_override.py`
- Test: `backend/tests/test_style_override.py`

**Interfaces:**
- Consumes: `TemplateDefinition`, `ProgressionRef` from `app.schemas.template`.
- Produces: `apply_progression_style(definition: TemplateDefinition, progression_style: str) -> TemplateDefinition`, `DEFAULT_UNDULATING_WAVES: list[dict[str, float]]`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_style_override.py
from app.schemas.template import ProgressionRef, SchemeDef, SessionDef, SlotRule, SplitDef, TemplateDefinition
from app.services.program.style_override import apply_progression_style


def _definition(model_key: str, params: dict[str, object]) -> TemplateDefinition:
    return TemplateDefinition(
        split=SplitDef(
            sessions=[SessionDef(key="a", name="A", order=1, slots=[SlotRule(pattern="squat", scheme="main")])]
        ),
        progression=ProgressionRef(model_key=model_key, params=params, deload_every=4),
        schemes={"main": SchemeDef(sets=3, reps_min=5, reps_max=5, rest_seconds=120)},
    )


def test_consistent_leaves_template_model_unchanged():
    original = _definition("linear_load", {"increment": 2.5})
    result = apply_progression_style(original, "consistent")
    assert result.progression.model_key == "linear_load"
    assert result.progression.params == {"increment": 2.5}


def test_consistent_preserves_double_progression_model():
    original = _definition("double_progression", {"increment": 0})
    result = apply_progression_style(original, "consistent")
    assert result.progression.model_key == "double_progression"


def test_variable_forces_weekly_undulating_with_default_waves():
    original = _definition("linear_load", {"increment": 2.5})
    result = apply_progression_style(original, "variable")
    assert result.progression.model_key == "weekly_undulating"
    assert result.progression.params["waves"] == [
        {"intensity": 1.0}, {"intensity": 0.85}, {"intensity": 1.05},
    ]
    assert result.progression.deload_every == 4  # untouched


def test_variable_keeps_templates_own_waves_if_defined():
    original = _definition("weekly_undulating", {"waves": [{"reps": 5, "intensity": 1.0}]})
    result = apply_progression_style(original, "variable")
    assert result.progression.params["waves"] == [{"reps": 5, "intensity": 1.0}]


def test_original_definition_is_not_mutated():
    original = _definition("linear_load", {"increment": 2.5})
    apply_progression_style(original, "variable")
    assert original.progression.model_key == "linear_load"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker-compose exec backend pytest tests/test_style_override.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.program.style_override'`

- [ ] **Step 3: Write the module**

```python
# backend/app/services/program/style_override.py
from app.schemas.template import TemplateDefinition

DEFAULT_UNDULATING_WAVES: list[dict[str, float]] = [
    {"intensity": 1.0},
    {"intensity": 0.85},
    {"intensity": 1.05},
]


def apply_progression_style(definition: TemplateDefinition, progression_style: str) -> TemplateDefinition:
    """Override a template's progression model based on the user's chosen per-program style.

    "consistent" is a no-op: the template keeps its own declared model (linear_load or
    double_progression, whichever it defines). "variable" forces weekly_undulating,
    injecting a default 3-week load wave when the template's own params don't already
    define one (a template that already picks weekly_undulating keeps its own waves).
    """
    if progression_style != "variable":
        return definition
    params = dict(definition.progression.params)
    params.setdefault("waves", DEFAULT_UNDULATING_WAVES)
    new_progression = definition.progression.model_copy(update={"model_key": "weekly_undulating", "params": params})
    return definition.model_copy(update={"progression": new_progression})
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker-compose exec backend pytest tests/test_style_override.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/program/style_override.py backend/tests/test_style_override.py
git commit -m "feat(program-engine): add per-program consistent/variable progression override"
```

---

### Task 7: Wire `progression_style` through `DraftRequest` → `WorkoutProgram.constraints` → preview

**Files:**
- Modify: `backend/app/schemas/program_api.py`
- Modify: `backend/app/services/program/drafting.py`
- Modify: `backend/app/api/v1/endpoints/programs.py`
- Modify: `backend/tests/test_drafting.py`
- Modify: `backend/tests/test_program_api_schemas.py`
- Test: `backend/tests/test_programs_progression_style.py`

**Interfaces:**
- Consumes: `ProgressionStyle` from `app.schemas.program` (already exists), `apply_progression_style` (Task 6).
- Produces: `DraftRequest.progression_style: ProgressionStyle = ProgressionStyle.CONSISTENT`; `build_draft(..., progression_style: str = "consistent")` now stores it in `WorkoutProgram.constraints["progression_style"]`.

- [ ] **Step 1: Write the failing schema test**

Add to `backend/tests/test_program_api_schemas.py`:

```python
def test_draft_request_defaults_to_consistent_progression():
    r = DraftRequest(
        template_id=2, environment_id=1, days_per_week=4, session_duration_min=60,
        fitness_focus="strength", weight_unit="kg", duration_weeks=8,
    )
    assert r.progression_style.value == "consistent"


def test_draft_request_accepts_variable_progression():
    r = DraftRequest(
        template_id=2, environment_id=1, days_per_week=4, session_duration_min=60,
        fitness_focus="strength", weight_unit="kg", duration_weeks=8, progression_style="variable",
    )
    assert r.progression_style.value == "variable"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker-compose exec backend pytest tests/test_program_api_schemas.py -v`
Expected: FAIL — `DraftRequest` has no field `progression_style`

- [ ] **Step 3: Add the field to `DraftRequest`**

In `backend/app/schemas/program_api.py`, add the import and field:

```python
from app.schemas.program import ProgressionStyle


class DraftRequest(MatchRequest):
    template_id: int
    required_inputs: dict[str, float] = {}
    progression_style: ProgressionStyle = ProgressionStyle.CONSISTENT
```

- [ ] **Step 4: Run schema test to verify it passes**

Run: `docker-compose exec backend pytest tests/test_program_api_schemas.py -v`
Expected: PASS

- [ ] **Step 5: Write the failing `build_draft` test**

Add to `backend/tests/test_drafting.py`:

```python
@pytest.mark.asyncio
async def test_build_draft_stores_progression_style_in_constraints(sample_template_orm, sample_exercises):
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(
        equipment=["barbell", "bench", "squat_rack"], experience="intermediate", injuries=[], used_movement_slugs=set()
    )
    program = build_draft(
        sample_template_orm, definition, ctx, sample_exercises,
        user_id=1, environment_id=1, days_per_week=3, duration_weeks=8, weight_unit="kg",
        required_inputs={"squat_start": 80, "bench_start": 60}, progression_style="variable",
    )
    assert program.constraints["progression_style"] == "variable"


@pytest.mark.asyncio
async def test_build_draft_defaults_progression_style_to_consistent(sample_template_orm, sample_exercises):
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(
        equipment=["barbell", "bench", "squat_rack"], experience="intermediate", injuries=[], used_movement_slugs=set()
    )
    program = build_draft(
        sample_template_orm, definition, ctx, sample_exercises,
        user_id=1, environment_id=1, days_per_week=3, duration_weeks=8, weight_unit="kg",
        required_inputs={"squat_start": 80, "bench_start": 60},
    )
    assert program.constraints["progression_style"] == "consistent"
```

- [ ] **Step 6: Run test to verify it fails**

Run: `docker-compose exec backend pytest tests/test_drafting.py -v`
Expected: FAIL — `KeyError: 'progression_style'`

- [ ] **Step 7: Add the parameter to `build_draft`**

In `backend/app/services/program/drafting.py`, update the signature and constraints dict:

```python
def build_draft(
    template: ProgramTemplate,
    definition: TemplateDefinition,
    ctx: SelectionContext,
    exercises: list[Exercise],
    *,
    user_id: int,
    environment_id: int,
    days_per_week: int,
    duration_weeks: int,
    weight_unit: str,
    required_inputs: dict[str, float],
    progression_style: str = "consistent",
) -> WorkoutProgram:
    applies_to_values = {
        ri.applies_to: required_inputs[ri.key]
        for ri in definition.required_inputs
        if ri.applies_to and ri.key in required_inputs
    }
    program = WorkoutProgram(
        user_id=user_id,
        template_id=template.id,
        environment_id=environment_id,
        name=template.name,
        focus=(template.goals[0] if template.goals else None),
        status=ProgramStatus.DRAFT,
        duration_weeks=duration_weeks,
        days_per_week=days_per_week,
        weight_unit=weight_unit,
        constraints={
            "locked_slots": [],
            "excluded_exercise_ids": [],
            "swaps": {},
            "volume_adjustments": {},
            "required_inputs": required_inputs,
            "progression_style": progression_style,
        },
    )
```

(the rest of the function body is unchanged)

- [ ] **Step 8: Run test to verify it passes**

Run: `docker-compose exec backend pytest tests/test_drafting.py -v`
Expected: PASS (all tests including the 2 new ones)

- [ ] **Step 9: Write the failing end-to-end preview test**

```python
# backend/tests/test_programs_progression_style.py
import pytest

from app.schemas.template import TemplateDefinition
from app.services.program.drafting import build_draft
from app.services.program.preview import derive_week
from app.services.program.selection import SelectionContext
from app.services.program.style_override import apply_progression_style


@pytest.mark.asyncio
async def test_variable_style_makes_week_to_week_reps_undulate(sample_template_orm, sample_exercises):
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(["barbell", "bench", "squat_rack"], "intermediate", [], set())
    program = build_draft(
        sample_template_orm, definition, ctx, sample_exercises,
        user_id=1, environment_id=1, days_per_week=3, duration_weeks=8, weight_unit="kg",
        required_inputs={"squat_start": 80}, progression_style="variable",
    )
    for w in program.workouts:
        w.id = w.order
        for j, ex in enumerate(w.exercises, 1):
            ex.id = j
    exercise_map = {e.id: e for e in sample_exercises}
    styled_definition = apply_progression_style(definition, program.constraints["progression_style"])
    assert styled_definition.progression.model_key == "weekly_undulating"

    w1 = derive_week(program, styled_definition, 1, exercise_map)
    w2 = derive_week(program, styled_definition, 2, exercise_map)
    load1 = next((s["load"] for d in w1 for s in d["slots"] if s["load"] is not None), None)
    load2 = next((s["load"] for d in w2 for s in d["slots"] if s["load"] is not None), None)
    assert load1 != load2  # intensity wave changes the load, unlike flat linear progression
```

- [ ] **Step 10: Run test to verify it fails**

Run: `docker-compose exec backend pytest tests/test_programs_progression_style.py -v`
Expected: FAIL if `apply_progression_style` import path is wrong, otherwise PASS already (this test only exercises Task 6's helper directly) — confirm it passes as-is; it does not require endpoint changes yet.

- [ ] **Step 11: Wire the override into the `/programs` endpoints**

In `backend/app/api/v1/endpoints/programs.py`, add the import:

```python
from app.services.program.style_override import apply_progression_style
```

Update `_load` to apply the stored style:

```python
async def _load(db: AsyncSession, user: User, program_id: int) -> tuple[WorkoutProgram, TemplateDefinition]:
    program = await get_program(db, user.id, program_id)
    if program is None:
        raise ProgramNotFoundError()
    template = await get_template(db, program.template_id)
    definition = TemplateDefinition.from_orm_template(template)
    style = program.constraints.get("progression_style", "consistent")
    return program, apply_progression_style(definition, style)
```

Update `draft()` to pass the requested style into `build_draft` and apply it to the definition used for the initial preview:

```python
    definition = TemplateDefinition.from_orm_template(template)
    ctx = await _ctx_for(db, user, environment)
    exercises = await list_exercises(db)
    program = build_draft(
        template,
        definition,
        ctx,
        exercises,
        user_id=user.id,
        environment_id=environment.id,
        days_per_week=data.days_per_week,
        duration_weeks=data.duration_weeks,
        weight_unit=data.weight_unit,
        required_inputs=data.required_inputs,
        progression_style=data.progression_style.value,
    )
    await save_program(db, program)
    saved = await get_program(db, user.id, program.id)
    assert saved is not None
    preview_definition = apply_progression_style(definition, data.progression_style.value)
    return await _preview_out(db, saved, preview_definition)
```

- [ ] **Step 12: Run the full backend suite**

Run: `docker-compose exec backend pytest -v`
Expected: PASS (all tests)

- [ ] **Step 13: Commit**

```bash
git add backend/app/schemas/program_api.py backend/app/services/program/drafting.py backend/app/api/v1/endpoints/programs.py backend/tests/test_drafting.py backend/tests/test_program_api_schemas.py backend/tests/test_programs_progression_style.py
git commit -m "feat(program-engine): wire per-program consistent/variable progression style end to end"
```

---

### Task 8: Frontend — collect `progression_style` in `ProgramCreationForm`

**Files:**
- Modify: `frontend/src/types/programCreation.ts`
- Modify: `frontend/src/types/program.ts`
- Modify: `frontend/src/components/ProgramCreationForm.tsx`
- Modify: `frontend/src/pages/ProgramBuilderPage.tsx`
- Modify: `frontend/src/tests/components/ProgramCreationForm.test.tsx`

**Interfaces:**
- Consumes: `ProgressionStyle`, `PROGRESSION_STYLE_OPTIONS` (already defined in `types/programCreation.ts`).
- Produces: `ProgramCreationForm`'s `onSubmit` payload now includes `progression_style: ProgressionStyle`; `types/programCreation.ts::MatchRequest` (form-local type) gains `progression_style: ProgressionStyle`; `types/program.ts::DraftRequest` gains `progression_style: ProgressionStyle`.

- [ ] **Step 1: Write the failing test**

Add to `frontend/src/tests/components/ProgramCreationForm.test.tsx`:

```tsx
it('should include progression_style in submitted values, defaulting to consistent', async () => {
    const onSubmit = vi.fn();
    const onCancel = vi.fn();

    render(<ProgramCreationForm environmentId={1} onSubmit={onSubmit} onCancel={onCancel} />);

    fireEvent.click(screen.getByRole('button', { name: /Next/i }));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({ progression_style: 'consistent' }),
      );
    });
  });

  it('should submit variable progression style when selected', async () => {
    const onSubmit = vi.fn();
    const onCancel = vi.fn();

    render(<ProgramCreationForm environmentId={1} onSubmit={onSubmit} onCancel={onCancel} />);

    fireEvent.change(screen.getByLabelText(/Progression Style/i), {
      target: { value: 'variable' },
    });
    fireEvent.click(screen.getByRole('button', { name: /Next/i }));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(
        expect.objectContaining({ progression_style: 'variable' }),
      );
    });
  });
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker-compose exec frontend npm run test:watch -- ProgramCreationForm --run`
Expected: FAIL — no element with label `/Progression Style/i`

- [ ] **Step 3: Extend the form-local `MatchRequest` type**

In `frontend/src/types/programCreation.ts`, extend the interface (the `ProgressionStyle` type and `PROGRESSION_STYLE_OPTIONS` already exist above it, unchanged):

```ts
export interface MatchRequest {
  environment_id: number;
  days_per_week: number;
  session_duration_min: number;
  weight_unit: WeightUnit;
  progression_style: ProgressionStyle;
}
```

- [ ] **Step 4: Add the field to `ProgramCreationForm`**

In `frontend/src/components/ProgramCreationForm.tsx`, add the import and state:

```tsx
import { WEIGHT_UNIT_OPTIONS, PROGRESSION_STYLE_OPTIONS } from '@/types/programCreation';
import type { MatchRequest, WeightUnit, ProgressionStyle } from '@/types/programCreation';
```

```tsx
  const [progressionStyle, setProgressionStyle] = useState<ProgressionStyle>(
    initialValues?.progression_style ?? 'consistent',
  );
```

Add to the `useEffect` sync block:

```tsx
      setProgressionStyle(initialValues.progression_style);
```

Add to `handleSubmit`'s `onSubmit` call:

```tsx
      progression_style: progressionStyle,
```

Add the control in the JSX, inside the existing grid, after the weight unit `<div className="input-group">`:

```tsx
        <div className="input-group">
          <label htmlFor="progression_style" className="input-label">
            Progression Style <span className="text-error-600">*</span>
          </label>
          <select
            id="progression_style"
            name="progression_style"
            value={progressionStyle}
            onChange={(e) => setProgressionStyle(e.target.value as ProgressionStyle)}
            required
          >
            {PROGRESSION_STYLE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
```

- [ ] **Step 5: Run test to verify it passes**

Run: `docker-compose exec frontend npm run test:watch -- ProgramCreationForm --run`
Expected: PASS (all tests including the 2 new ones)

- [ ] **Step 6: Thread the value through `ProgramBuilderPage` into `DraftRequest`**

In `frontend/src/types/program.ts`, add the import and field:

```ts
import type { ProgressionStyle } from '@/types/programCreation';

export interface DraftRequest extends MatchRequest {
  template_id: number;
  required_inputs: Record<string, number | string>;
  progression_style: ProgressionStyle;
}
```

In `frontend/src/pages/ProgramBuilderPage.tsx`, add state and thread it through:

```tsx
import type { ProgressionStyle } from '@/types/programCreation';
```

```tsx
  const [progressionStyle, setProgressionStyle] = useState<ProgressionStyle>('consistent');
```

Update `onPrefs`:

```tsx
  const onPrefs = (values: FormMatchRequest) => {
    const matchRequest: MatchRequest = {
      environment_id: values.environment_id,
      days_per_week: values.days_per_week,
      session_duration_min: values.session_duration_min,
      weight_unit: values.weight_unit,
      fitness_focus: 'full_body',
      duration_weeks: 8,
    };
    setPrefs(matchRequest);
    setProgressionStyle(values.progression_style);
    match.mutate(matchRequest, { onSuccess: () => setStep(1) });
  };
```

Update `makeDraft`:

```tsx
    const program = await createDraft.mutateAsync({
      ...prefs,
      template_id: m.template_id,
      required_inputs: requiredInputs,
      progression_style: progressionStyle,
    });
```

Update the `initialValues` passed to `ProgramCreationForm` to include the current style (so Back navigation preserves it):

```tsx
          initialValues={
            prefs
              ? {
                  environment_id: prefs.environment_id,
                  days_per_week: prefs.days_per_week,
                  session_duration_min: prefs.session_duration_min,
                  weight_unit: prefs.weight_unit as WeightUnit,
                  progression_style: progressionStyle,
                }
              : undefined
          }
```

- [ ] **Step 7: Run frontend type-check and full test suite**

Run: `docker-compose exec frontend npm run type-check && docker-compose exec frontend npm run test:watch -- --run`
Expected: both PASS

- [ ] **Step 8: Commit**

```bash
git add frontend/src/types/programCreation.ts frontend/src/types/program.ts frontend/src/components/ProgramCreationForm.tsx frontend/src/pages/ProgramBuilderPage.tsx frontend/src/tests/components/ProgramCreationForm.test.tsx
git commit -m "feat(program-ui): collect progression style per program in the creation wizard"
```

---

## Phase 3 — Effort measurement preference (per-program, lifting only)

### Task 9: `EffortMethod` enum + `SchemeDef` intensity fields

**Files:**
- Modify: `backend/app/schemas/program.py`
- Modify: `backend/app/schemas/template.py`
- Modify: `backend/app/db/seed/program_templates.py`
- Test: `backend/tests/test_effort_method.py`

**Interfaces:**
- Produces: `EffortMethod` enum (`rpe | rir | borg | percent_1rm`) in `app.schemas.program`; `SchemeDef.target_rpe: float | None = None`, `SchemeDef.intensity_pct: float | None = None`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_effort_method.py
from app.schemas.program import EffortMethod
from app.schemas.template import SchemeDef


def test_effort_method_values():
    assert {m.value for m in EffortMethod} == {"rpe", "rir", "borg", "percent_1rm"}


def test_scheme_def_effort_fields_default_to_none():
    scheme = SchemeDef(sets=3, reps_min=8, reps_max=12, rest_seconds=60)
    assert scheme.target_rpe is None
    assert scheme.intensity_pct is None


def test_scheme_def_accepts_effort_fields():
    scheme = SchemeDef(sets=4, reps_min=6, reps_max=8, rest_seconds=120, target_rpe=8.0, intensity_pct=0.8)
    assert scheme.target_rpe == 8.0
    assert scheme.intensity_pct == 0.8
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker-compose exec backend pytest tests/test_effort_method.py -v`
Expected: FAIL — `ImportError: cannot import name 'EffortMethod'`

- [ ] **Step 3: Add `EffortMethod`**

In `backend/app/schemas/program.py`, add after `ProgressionStyle`:

```python
class EffortMethod(str, enum.Enum):
    RPE = "rpe"
    RIR = "rir"
    BORG = "borg"
    PERCENT_1RM = "percent_1rm"
```

- [ ] **Step 4: Add fields to `SchemeDef`**

In `backend/app/schemas/template.py`, update:

```python
class SchemeDef(BaseModel):
    sets: int
    reps_min: int
    reps_max: int
    rest_seconds: int
    target_rpe: float | None = None
    intensity_pct: float | None = None
```

- [ ] **Step 5: Run test to verify it passes**

Run: `docker-compose exec backend pytest tests/test_effort_method.py -v`
Expected: PASS (3 tests)

- [ ] **Step 6: Populate seed templates with effort anchors**

In `backend/app/db/seed/program_templates.py`, for each of the 4 templates, update the `"main"` and `"accessory"` entries in `split.schemes` to add `target_rpe`/`intensity_pct`. Apply this exact change to all 4 occurrences of each key:

`"main": {"sets": ..., "reps_min": ..., "reps_max": ..., "rest_seconds": ...}` → add `, "target_rpe": 8.0, "intensity_pct": 0.8` before the closing brace.

`"accessory": {"sets": ..., "reps_min": ..., "reps_max": ..., "rest_seconds": ...}` → add `, "target_rpe": 7.0, "intensity_pct": 0.65` before the closing brace.

Concretely, for the first template (`full-body-x3`), the schemes block becomes:

```python
            "schemes": {
                "main": {"sets": 3, "reps_min": 5, "reps_max": 5, "rest_seconds": 120, "target_rpe": 8.0, "intensity_pct": 0.8},
                "accessory": {"sets": 3, "reps_min": 10, "reps_max": 12, "rest_seconds": 60, "target_rpe": 7.0, "intensity_pct": 0.65},
            },
```

Apply the same `target_rpe`/`intensity_pct` additions to the `main`/`accessory` scheme dicts in `bodyweight-full-body-x3`, `upper-lower-x4`, and `push-pull-legs-x6`.

- [ ] **Step 7: Add a regression test that seed templates parse with the new fields**

```python
# add to backend/tests/test_effort_method.py
import pytest

from app.db.seed.program_templates import PROGRAM_TEMPLATE_SEED
from app.schemas.template import SchemeDef


@pytest.mark.parametrize("template", PROGRAM_TEMPLATE_SEED, ids=lambda t: t["slug"])
def test_seed_template_schemes_define_effort_anchors(template):
    schemes = template["split"]["schemes"]
    for key, raw in schemes.items():
        scheme = SchemeDef(**raw)
        assert scheme.target_rpe is not None, f"{template['slug']}.{key} missing target_rpe"
        assert scheme.intensity_pct is not None, f"{template['slug']}.{key} missing intensity_pct"
```

- [ ] **Step 8: Run test to verify it passes**

Run: `docker-compose exec backend pytest tests/test_effort_method.py -v`
Expected: PASS (11 tests: 3 from step 5 + 8 parametrized, one per template/scheme pair)

- [ ] **Step 9: Run full backend suite to confirm no regression**

Run: `docker-compose exec backend pytest -v`
Expected: PASS

- [ ] **Step 10: Commit**

```bash
git add backend/app/schemas/program.py backend/app/schemas/template.py backend/app/db/seed/program_templates.py backend/tests/test_effort_method.py
git commit -m "feat(program-engine): add EffortMethod enum and per-scheme RPE/intensity anchors"
```

---

### Task 10: Denormalize effort targets onto `WorkoutExercise` + compute `%1RM` base load

**Files:**
- Modify: `backend/app/models/program.py`
- Create: `backend/alembic/versions/d4e5f6a7b8c9_add_effort_fields_to_workout_exercises.py`
- Modify: `backend/app/services/program/drafting.py`
- Modify: `backend/tests/test_drafting.py`

**Interfaces:**
- Consumes: `EffortMethod` (Task 9), `SchemeDef.target_rpe`/`intensity_pct` (Task 9).
- Produces: `WorkoutExercise.target_rpe: float | None`, `WorkoutExercise.intensity_pct: float | None`; `build_draft(..., effort_method: str | None = None)`.

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_drafting.py`:

```python
@pytest.mark.asyncio
async def test_build_draft_denormalizes_effort_targets_onto_workout_exercise(
    sample_template_orm, sample_exercises
):
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(
        equipment=["barbell", "bench", "squat_rack"], experience="intermediate", injuries=[], used_movement_slugs=set()
    )
    program = build_draft(
        sample_template_orm, definition, ctx, sample_exercises,
        user_id=1, environment_id=1, days_per_week=3, duration_weeks=8, weight_unit="kg",
        required_inputs={"squat_start": 80, "bench_start": 60},
    )
    main_scheme_exercises = [ex for w in program.workouts for ex in w.exercises if ex.scheme_key == "main"]
    assert main_scheme_exercises
    assert all(ex.target_rpe == 8.0 for ex in main_scheme_exercises)
    assert all(ex.intensity_pct == 0.8 for ex in main_scheme_exercises)


@pytest.mark.asyncio
async def test_build_draft_computes_percent_1rm_base_load(sample_template_orm, sample_exercises):
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(
        equipment=["barbell", "bench", "squat_rack"], experience="intermediate", injuries=[], used_movement_slugs=set()
    )
    program = build_draft(
        sample_template_orm, definition, ctx, sample_exercises,
        user_id=1, environment_id=1, days_per_week=3, duration_weeks=8, weight_unit="kg",
        required_inputs={"squat_start": 100, "bench_start": 60}, effort_method="percent_1rm",
    )
    squat_exercises = [ex for w in program.workouts for ex in w.exercises if ex.fills_rule.get("pattern") == "squat"]
    main_squats = [ex for ex in squat_exercises if ex.scheme_key == "main"]
    assert main_squats
    assert all(ex.base_load == 80.0 for ex in main_squats)  # 100 * 0.8 intensity_pct


@pytest.mark.asyncio
async def test_build_draft_base_load_unaffected_when_effort_method_unset(sample_template_orm, sample_exercises):
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(
        equipment=["barbell", "bench", "squat_rack"], experience="intermediate", injuries=[], used_movement_slugs=set()
    )
    program = build_draft(
        sample_template_orm, definition, ctx, sample_exercises,
        user_id=1, environment_id=1, days_per_week=3, duration_weeks=8, weight_unit="kg",
        required_inputs={"squat_start": 100, "bench_start": 60},
    )
    squat_exercises = [
        ex for w in program.workouts for ex in w.exercises
        if ex.fills_rule.get("pattern") == "squat" and ex.scheme_key == "main"
    ]
    assert squat_exercises
    assert all(ex.base_load == 100.0 for ex in squat_exercises)  # unchanged, backward compatible
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker-compose exec backend pytest tests/test_drafting.py -v`
Expected: FAIL — `WorkoutExercise` has no attribute `target_rpe`, and `build_draft()` has no `effort_method` kwarg

- [ ] **Step 3: Add columns to `WorkoutExercise`**

In `backend/app/models/program.py`, add after `scheme_key`:

```python
    target_rpe: Mapped[float | None] = mapped_column(Float)
    intensity_pct: Mapped[float | None] = mapped_column(Float)
```

- [ ] **Step 4: Write the migration**

```python
# backend/alembic/versions/d4e5f6a7b8c9_add_effort_fields_to_workout_exercises.py
"""add target_rpe and intensity_pct to workout_exercises

Revision ID: d4e5f6a7b8c9
Revises: c8d9e0f1a2b3
Create Date: 2026-07-16 09:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c8d9e0f1a2b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("workout_exercises", sa.Column("target_rpe", sa.Float(), nullable=True))
    op.add_column("workout_exercises", sa.Column("intensity_pct", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("workout_exercises", "intensity_pct")
    op.drop_column("workout_exercises", "target_rpe")
```

- [ ] **Step 5: Update `build_draft` and `_base_load_for`**

In `backend/app/services/program/drafting.py`:

```python
from app.models import Exercise, ProgramStatus, ProgramTemplate, Workout, WorkoutExercise, WorkoutProgram
from app.schemas.program import EffortMethod
from app.schemas.template import SchemeDef, SlotRule, TemplateDefinition
from app.services.program.selection import SelectionContext, select_for_slot


def _base_load_for(
    rule: SlotRule, scheme: SchemeDef, applies_to_values: dict[str, float], effort_method: str | None
) -> float | None:
    value = applies_to_values.get(rule.pattern) if rule.pattern else None
    if value is None and rule.region:
        value = applies_to_values.get(rule.region)
    if value is None:
        return None
    if effort_method == EffortMethod.PERCENT_1RM.value and scheme.intensity_pct is not None:
        return round(float(value) * scheme.intensity_pct, 2)
    return float(value)


def build_draft(
    template: ProgramTemplate,
    definition: TemplateDefinition,
    ctx: SelectionContext,
    exercises: list[Exercise],
    *,
    user_id: int,
    environment_id: int,
    days_per_week: int,
    duration_weeks: int,
    weight_unit: str,
    required_inputs: dict[str, float],
    progression_style: str = "consistent",
    effort_method: str | None = None,
) -> WorkoutProgram:
    applies_to_values = {
        ri.applies_to: required_inputs[ri.key]
        for ri in definition.required_inputs
        if ri.applies_to and ri.key in required_inputs
    }
    program = WorkoutProgram(
        user_id=user_id,
        template_id=template.id,
        environment_id=environment_id,
        name=template.name,
        focus=(template.goals[0] if template.goals else None),
        status=ProgramStatus.DRAFT,
        duration_weeks=duration_weeks,
        days_per_week=days_per_week,
        weight_unit=weight_unit,
        constraints={
            "locked_slots": [],
            "excluded_exercise_ids": [],
            "swaps": {},
            "volume_adjustments": {},
            "required_inputs": required_inputs,
            "progression_style": progression_style,
            "effort_method": effort_method,
        },
    )
    for session in definition.split.sessions:
        workout = Workout(
            key=session.key,
            name=session.name,
            focus=",".join(filter(None, [s.pattern or s.region for s in session.slots])),
            order=session.order,
        )
        for i, rule in enumerate(session.slots, start=1):
            scheme = definition.schemes[rule.scheme]
            chosen = select_for_slot(exercises, rule, ctx, None, set())
            if chosen is None:
                continue
            ctx.used_movement_slugs.add(chosen.movement_slug)
            ctx.used_unilateral_flags.append(chosen.is_unilateral)
            workout.exercises.append(
                WorkoutExercise(
                    order=i,
                    exercise_id=chosen.id,
                    fills_rule=rule.model_dump(),
                    sets=scheme.sets,
                    reps_min=scheme.reps_min,
                    reps_max=scheme.reps_max,
                    base_load=_base_load_for(rule, scheme, applies_to_values, effort_method),
                    rest_seconds=scheme.rest_seconds,
                    scheme_key=rule.scheme,
                    target_rpe=scheme.target_rpe,
                    intensity_pct=scheme.intensity_pct,
                    is_locked=False,
                    is_user_swapped=False,
                )
            )
        program.workouts.append(workout)
    return program
```

- [ ] **Step 6: Run test to verify it passes**

Run: `docker-compose exec backend pytest tests/test_drafting.py -v`
Expected: PASS (all tests)

- [ ] **Step 7: Verify migration reversibility**

Run: `docker-compose exec backend uv run alembic upgrade head && docker-compose exec backend uv run alembic downgrade -1 && docker-compose exec backend uv run alembic upgrade head`
Expected: all exit 0, `alembic heads` shows single head `d4e5f6a7b8c9`

- [ ] **Step 8: Commit**

```bash
git add backend/app/models/program.py backend/alembic/versions/d4e5f6a7b8c9_add_effort_fields_to_workout_exercises.py backend/app/services/program/drafting.py backend/tests/test_drafting.py
git commit -m "feat(program-engine): denormalize effort targets onto WorkoutExercise and compute %1RM base load"
```

---

### Task 11: Surface `effort_target` in preview + wire `effort_method` through the endpoint

**Files:**
- Modify: `backend/app/services/program/preview.py`
- Modify: `backend/app/schemas/program_api.py`
- Modify: `backend/app/api/v1/endpoints/programs.py`
- Modify: `backend/tests/test_preview.py`
- Modify: `backend/tests/test_program_api_schemas.py`

**Interfaces:**
- Consumes: `WorkoutExercise.target_rpe`/`intensity_pct` (Task 10), `WorkoutProgram.constraints["effort_method"]` (Task 10).
- Produces: `derive_week()` slot dicts gain an `effort_target: dict | None` key; `DraftRequest.effort_method: EffortMethod | None = None`; `SlotPreviewOut.effort_target: dict | None = None`.

- [ ] **Step 1: Write the failing preview tests**

Add to `backend/tests/test_preview.py`:

```python
@pytest.mark.asyncio
async def test_derive_week_includes_rpe_effort_target_when_requested(sample_template_orm, sample_exercises):
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(["barbell", "bench", "squat_rack"], "intermediate", [], set())
    program = build_draft(
        sample_template_orm, definition, ctx, sample_exercises,
        user_id=1, environment_id=1, days_per_week=3, duration_weeks=8, weight_unit="kg",
        required_inputs={"squat_start": 80}, effort_method="rpe",
    )
    for w in program.workouts:
        w.id = w.order
        for j, ex in enumerate(w.exercises, 1):
            ex.id = j
    exercise_map = {e.id: e for e in sample_exercises}
    week1 = derive_week(program, definition, 1, exercise_map)
    main_slots = [s for d in week1 for s in d["slots"] if s.get("effort_target") is not None]
    assert main_slots
    assert all(s["effort_target"]["method"] == "rpe" for s in main_slots)


@pytest.mark.asyncio
async def test_derive_week_converts_rpe_to_rir(sample_template_orm, sample_exercises):
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(["barbell", "bench", "squat_rack"], "intermediate", [], set())
    program = build_draft(
        sample_template_orm, definition, ctx, sample_exercises,
        user_id=1, environment_id=1, days_per_week=3, duration_weeks=8, weight_unit="kg",
        required_inputs={"squat_start": 80}, effort_method="rir",
    )
    for w in program.workouts:
        w.id = w.order
        for j, ex in enumerate(w.exercises, 1):
            ex.id = j
    exercise_map = {e.id: e for e in sample_exercises}
    week1 = derive_week(program, definition, 1, exercise_map)
    main_targets = [
        s["effort_target"] for d in week1 for s in d["slots"]
        if s.get("effort_target") is not None and s["effort_target"]["method"] == "rir"
    ]
    assert main_targets
    assert all(t["value"] == 2 for t in main_targets)  # target_rpe=8.0 -> rir = 10 - 8 = 2


@pytest.mark.asyncio
async def test_derive_week_percent_1rm_target_includes_load(sample_template_orm, sample_exercises):
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(["barbell", "bench", "squat_rack"], "intermediate", [], set())
    program = build_draft(
        sample_template_orm, definition, ctx, sample_exercises,
        user_id=1, environment_id=1, days_per_week=3, duration_weeks=8, weight_unit="kg",
        required_inputs={"squat_start": 100}, effort_method="percent_1rm",
    )
    for w in program.workouts:
        w.id = w.order
        for j, ex in enumerate(w.exercises, 1):
            ex.id = j
    exercise_map = {e.id: e for e in sample_exercises}
    week1 = derive_week(program, definition, 1, exercise_map)
    targets = [
        s["effort_target"] for d in week1 for s in d["slots"]
        if s.get("effort_target") is not None and s["effort_target"]["method"] == "percent_1rm"
    ]
    assert targets
    assert all(t["pct"] in (0.8, 0.65) for t in targets)  # main=0.8, accessory=0.65 intensity_pct
    assert all(t["target_load"] is not None for t in targets)


@pytest.mark.asyncio
async def test_derive_week_omits_effort_target_when_effort_method_unset(sample_template_orm, sample_exercises):
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(["barbell", "bench", "squat_rack"], "intermediate", [], set())
    program = build_draft(
        sample_template_orm, definition, ctx, sample_exercises,
        user_id=1, environment_id=1, days_per_week=3, duration_weeks=8, weight_unit="kg",
        required_inputs={"squat_start": 80},
    )
    for w in program.workouts:
        w.id = w.order
        for j, ex in enumerate(w.exercises, 1):
            ex.id = j
    exercise_map = {e.id: e for e in sample_exercises}
    week1 = derive_week(program, definition, 1, exercise_map)
    slots = [s for d in week1 for s in d["slots"]]
    assert slots
    assert all(s["effort_target"] is None for s in slots)  # backward compatible default
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker-compose exec backend pytest tests/test_preview.py -v`
Expected: FAIL — `KeyError: 'effort_target'`

- [ ] **Step 3: Add effort-target computation to `derive_week`**

In `backend/app/services/program/preview.py`:

```python
from typing import Any

from app.models import Exercise, WorkoutProgram
from app.schemas.template import TemplateDefinition
from app.services.program.progression.base import SetScheme, SlotBase, get_model
from app.services.program.progression.deload import apply_deload


def _effort_target(
    scheme: SetScheme, target_rpe: float | None, intensity_pct: float | None, effort_method: str | None
) -> dict[str, Any] | None:
    if effort_method is None or target_rpe is None:
        return None
    if effort_method == "rpe":
        return {"method": "rpe", "value": target_rpe}
    if effort_method == "rir":
        return {"method": "rir", "value": round(10 - target_rpe)}
    if effort_method == "borg":
        return {"method": "borg", "value": min(20, max(6, round(target_rpe * 2 + 2)))}
    if effort_method == "percent_1rm" and intensity_pct is not None:
        return {"method": "percent_1rm", "pct": intensity_pct, "target_load": scheme.load}
    return None


def derive_week(
    program: WorkoutProgram, definition: TemplateDefinition, week: int, exercises: dict[int, Exercise] | None = None
) -> list[dict[str, Any]]:
    model = get_model(definition.progression.model_key)
    every = definition.progression.deload_every
    params = definition.progression.params
    effort_method = program.constraints.get("effort_method")
    exercise_map = exercises or {}
    days: list[dict[str, Any]] = []
    for workout in program.workouts:
        slots = []
        for ex in workout.exercises:
            base = SlotBase(
                sets=ex.sets,
                reps_min=ex.reps_min,
                reps_max=ex.reps_max,
                rest_seconds=ex.rest_seconds,
                base_load=ex.base_load,
            )
            scheme = apply_deload(model.resolve(base, week, params), week, every)
            exercise = exercise_map.get(ex.exercise_id)
            exercise_name = exercise.name if exercise else f"Exercise #{ex.exercise_id}"
            slots.append(
                {
                    "workout_exercise_id": ex.id,
                    "exercise_id": ex.exercise_id,
                    "exercise_name": exercise_name,
                    "sets": scheme.sets,
                    "reps": scheme.reps,
                    "load": scheme.load,
                    "rest_seconds": scheme.rest_seconds,
                    "note": scheme.note,
                    "is_locked": ex.is_locked,
                    "is_user_swapped": ex.is_user_swapped,
                    "effort_target": _effort_target(scheme, ex.target_rpe, ex.intensity_pct, effort_method),
                }
            )
        days.append({"workout_id": workout.id, "key": workout.key, "name": workout.name, "slots": slots})
    return days
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker-compose exec backend pytest tests/test_preview.py -v`
Expected: PASS (all tests)

- [ ] **Step 5: Add `effort_method` to `DraftRequest` and `effort_target` to `SlotPreviewOut`**

In `backend/app/schemas/program_api.py`:

```python
from app.schemas.program import EffortMethod, ProgressionStyle


class DraftRequest(MatchRequest):
    template_id: int
    required_inputs: dict[str, float] = {}
    progression_style: ProgressionStyle = ProgressionStyle.CONSISTENT
    effort_method: EffortMethod | None = None


class SlotPreviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    workout_exercise_id: int
    exercise_id: int
    exercise_name: str
    sets: int
    reps: int
    load: float | None
    rest_seconds: int
    note: str | None
    is_locked: bool
    is_user_swapped: bool
    effort_target: dict[str, object] | None = None
```

Add to `backend/tests/test_program_api_schemas.py`:

```python
def test_draft_request_defaults_effort_method_to_none():
    r = DraftRequest(
        template_id=2, environment_id=1, days_per_week=4, session_duration_min=60,
        fitness_focus="strength", weight_unit="kg", duration_weeks=8,
    )
    assert r.effort_method is None


def test_draft_request_accepts_percent_1rm_effort_method():
    r = DraftRequest(
        template_id=2, environment_id=1, days_per_week=4, session_duration_min=60,
        fitness_focus="strength", weight_unit="kg", duration_weeks=8, effort_method="percent_1rm",
    )
    assert r.effort_method.value == "percent_1rm"
```

- [ ] **Step 6: Pass `effort_method` through the `/draft` endpoint**

In `backend/app/api/v1/endpoints/programs.py`, update the `build_draft` call in `draft()`:

```python
    program = build_draft(
        template,
        definition,
        ctx,
        exercises,
        user_id=user.id,
        environment_id=environment.id,
        days_per_week=data.days_per_week,
        duration_weeks=data.duration_weeks,
        weight_unit=data.weight_unit,
        required_inputs=data.required_inputs,
        progression_style=data.progression_style.value,
        effort_method=data.effort_method.value if data.effort_method else None,
    )
```

- [ ] **Step 7: Run the full backend suite**

Run: `docker-compose exec backend pytest -v`
Expected: PASS (all tests)

- [ ] **Step 8: Type-check and lint**

Run: `docker-compose exec backend mypy app/ && docker-compose exec backend ruff check .`
Expected: both clean

- [ ] **Step 9: Commit**

```bash
git add backend/app/services/program/preview.py backend/app/schemas/program_api.py backend/app/api/v1/endpoints/programs.py backend/tests/test_preview.py backend/tests/test_program_api_schemas.py
git commit -m "feat(program-engine): surface per-set effort targets in preview based on chosen effort method"
```

---

### Task 12: Frontend — collect `effort_method` and render `effort_target`

**Files:**
- Modify: `frontend/src/types/programCreation.ts`
- Modify: `frontend/src/types/program.ts`
- Modify: `frontend/src/components/ProgramCreationForm.tsx`
- Modify: `frontend/src/pages/ProgramBuilderPage.tsx`
- Modify: `frontend/src/components/SlotRow.tsx`
- Modify: `frontend/src/tests/components/ProgramCreationForm.test.tsx`
- Create: `frontend/src/tests/components/SlotRow.test.tsx`

**Interfaces:**
- Produces: `EffortMethod` type + `EFFORT_METHOD_OPTIONS` in `types/programCreation.ts`; `ProgramCreationForm` submits `effort_method: EffortMethod | ''`; `SlotPreview.effort_target` rendered in `SlotRow`.

- [ ] **Step 1: Write the failing form test**

Add to `frontend/src/tests/components/ProgramCreationForm.test.tsx`:

```tsx
it('should default effort_method to empty (no preference) and submit a chosen method', async () => {
    const onSubmit = vi.fn();
    const onCancel = vi.fn();

    render(<ProgramCreationForm environmentId={1} onSubmit={onSubmit} onCancel={onCancel} />);

    fireEvent.change(screen.getByLabelText(/Effort Tracking/i), {
      target: { value: 'rpe' },
    });
    fireEvent.click(screen.getByRole('button', { name: /Next/i }));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ effort_method: 'rpe' }));
    });
  });
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker-compose exec frontend npm run test:watch -- ProgramCreationForm --run`
Expected: FAIL — no element with label `/Effort Tracking/i`

- [ ] **Step 3: Add `EffortMethod` type + options**

In `frontend/src/types/programCreation.ts`, add after `PROGRESSION_STYLE_OPTIONS`:

```ts
export type EffortMethod = 'rpe' | 'rir' | 'borg' | 'percent_1rm';

export const EFFORT_METHOD_OPTIONS: { value: EffortMethod | ''; label: string }[] = [
  { value: '', label: "Not sure yet / skip" },
  { value: 'rpe', label: 'RPE — Rate of Perceived Exertion (1-10)' },
  { value: 'rir', label: 'RIR — Reps in Reserve' },
  { value: 'borg', label: 'Borg Scale (6-20)' },
  { value: 'percent_1rm', label: '% of 1-Rep Max' },
];
```

Update `MatchRequest` (form-local):

```ts
export interface MatchRequest {
  environment_id: number;
  days_per_week: number;
  session_duration_min: number;
  weight_unit: WeightUnit;
  progression_style: ProgressionStyle;
  effort_method: EffortMethod | '';
}
```

- [ ] **Step 4: Add the field to `ProgramCreationForm`**

In `frontend/src/components/ProgramCreationForm.tsx`:

```tsx
import { WEIGHT_UNIT_OPTIONS, PROGRESSION_STYLE_OPTIONS, EFFORT_METHOD_OPTIONS } from '@/types/programCreation';
import type { MatchRequest, WeightUnit, ProgressionStyle, EffortMethod } from '@/types/programCreation';
```

```tsx
  const [effortMethod, setEffortMethod] = useState<EffortMethod | ''>(
    initialValues?.effort_method ?? '',
  );
```

Add to the `useEffect` sync block:

```tsx
      setEffortMethod(initialValues.effort_method);
```

Add to `handleSubmit`'s `onSubmit` call:

```tsx
      effort_method: effortMethod,
```

Add the control after the progression-style `<div className="input-group">`:

```tsx
        <div className="input-group">
          <label htmlFor="effort_method" className="input-label">
            Effort Tracking Style
          </label>
          <select
            id="effort_method"
            name="effort_method"
            value={effortMethod}
            onChange={(e) => setEffortMethod(e.target.value as EffortMethod | '')}
          >
            {EFFORT_METHOD_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
```

- [ ] **Step 5: Run test to verify it passes**

Run: `docker-compose exec frontend npm run test:watch -- ProgramCreationForm --run`
Expected: PASS (all tests including the 2 new ones from Task 8 and this task)

- [ ] **Step 6: Thread `effort_method` through `ProgramBuilderPage` into `DraftRequest`**

In `frontend/src/types/program.ts`:

```ts
import type { EffortMethod, ProgressionStyle } from '@/types/programCreation';

export interface EffortTarget {
  method: 'rpe' | 'rir' | 'borg' | 'percent_1rm';
  value?: number;
  pct?: number;
  target_load?: number | null;
}

export interface SlotPreview {
  workout_exercise_id: number;
  exercise_id: number;
  exercise_name: string;
  sets: number;
  reps: number;
  load: number | null;
  rest_seconds: number;
  note: string | null;
  is_locked: boolean;
  is_user_swapped: boolean;
  effort_target: EffortTarget | null;
}

export interface DraftRequest extends MatchRequest {
  template_id: number;
  required_inputs: Record<string, number | string>;
  progression_style: ProgressionStyle;
  effort_method: EffortMethod | null;
}
```

In `frontend/src/pages/ProgramBuilderPage.tsx`:

```tsx
import type { EffortMethod, ProgressionStyle } from '@/types/programCreation';
```

```tsx
  const [effortMethod, setEffortMethod] = useState<EffortMethod | null>(null);
```

Update `onPrefs`:

```tsx
    setProgressionStyle(values.progression_style);
    setEffortMethod(values.effort_method || null);
```

Update `makeDraft`:

```tsx
    const program = await createDraft.mutateAsync({
      ...prefs,
      template_id: m.template_id,
      required_inputs: requiredInputs,
      progression_style: progressionStyle,
      effort_method: effortMethod,
    });
```

Update `initialValues`:

```tsx
                  progression_style: progressionStyle,
                  effort_method: effortMethod ?? '',
```

- [ ] **Step 7: Write the failing `SlotRow` test**

```tsx
// frontend/src/tests/components/SlotRow.test.tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { SlotRow } from '@/components/SlotRow';
import type { SlotPreview } from '@/types/program';

const baseSlot: SlotPreview = {
  workout_exercise_id: 1,
  exercise_id: 1,
  exercise_name: 'Barbell Back Squat',
  sets: 3,
  reps: 5,
  load: 100,
  rest_seconds: 120,
  note: null,
  is_locked: false,
  is_user_swapped: false,
  effort_target: null,
};

describe('SlotRow', () => {
  it('renders nothing extra when effort_target is null', () => {
    render(<SlotRow slot={baseSlot} onAction={vi.fn()} onSwap={vi.fn()} />);
    expect(screen.queryByText(/RPE|RIR|Borg|%/)).not.toBeInTheDocument();
  });

  it('renders an RPE effort target', () => {
    const slot = { ...baseSlot, effort_target: { method: 'rpe' as const, value: 8 } };
    render(<SlotRow slot={slot} onAction={vi.fn()} onSwap={vi.fn()} />);
    expect(screen.getByText(/RPE 8/i)).toBeInTheDocument();
  });

  it('renders a percent_1rm effort target as a percentage', () => {
    const slot = {
      ...baseSlot,
      effort_target: { method: 'percent_1rm' as const, pct: 0.8, target_load: 80 },
    };
    render(<SlotRow slot={slot} onAction={vi.fn()} onSwap={vi.fn()} />);
    expect(screen.getByText(/80%/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 8: Run test to verify it fails**

Run: `docker-compose exec frontend npm run test:watch -- SlotRow --run`
Expected: FAIL — effort target text not rendered

- [ ] **Step 9: Render `effort_target` in `SlotRow`**

In `frontend/src/components/SlotRow.tsx`:

```tsx
import type { FeedbackAction, SlotPreview } from '@/types/program';
import { SlotFeedbackMenu } from './SlotFeedbackMenu';

function formatEffortTarget(target: SlotPreview['effort_target']): string | null {
  if (!target) return null;
  if (target.method === 'percent_1rm') {
    return `${Math.round((target.pct ?? 0) * 100)}%`;
  }
  return `${target.method.toUpperCase()} ${target.value}`;
}

export function SlotRow({
  slot,
  onAction,
  onSwap,
}: {
  slot: SlotPreview;
  onAction: (a: FeedbackAction) => void;
  onSwap: () => void;
}) {
  const effortLabel = formatEffortTarget(slot.effort_target);
  return (
    <div className="flex items-center justify-between py-2 border-b">
      <div className="flex items-center gap-2">
        {slot.is_locked && <span aria-label="locked">🔒</span>}
        {slot.is_user_swapped && (
          <span aria-label="swapped" className="text-xs text-blue-600">
            swapped
          </span>
        )}
        <span>{slot.exercise_name}</span>
      </div>
      <div className="flex items-center gap-3 text-sm text-gray-700">
        <span>
          {slot.sets} × {slot.reps}
          {slot.load != null ? ` @ ${slot.load}` : ''}
        </span>
        {effortLabel && <span className="text-xs text-neutral-500">{effortLabel}</span>}
        {slot.note && <span className="text-amber-600">{slot.note}</span>}
        <SlotFeedbackMenu slot={slot} onAction={onAction} onSwap={onSwap} />
      </div>
    </div>
  );
}
```

- [ ] **Step 10: Run test to verify it passes**

Run: `docker-compose exec frontend npm run test:watch -- SlotRow --run`
Expected: PASS (3 tests)

- [ ] **Step 11: Run the full frontend suite and type-check**

Run: `docker-compose exec frontend npm run test:watch -- --run && docker-compose exec frontend npm run type-check`
Expected: both PASS

- [ ] **Step 12: Commit**

```bash
git add frontend/src/types/programCreation.ts frontend/src/types/program.ts frontend/src/components/ProgramCreationForm.tsx frontend/src/pages/ProgramBuilderPage.tsx frontend/src/components/SlotRow.tsx frontend/src/tests/components/ProgramCreationForm.test.tsx frontend/src/tests/components/SlotRow.test.tsx
git commit -m "feat(program-ui): collect effort tracking preference and show per-set effort targets"
```

---

## Final Verification (after all tasks)

- [ ] Run the complete backend suite: `docker-compose exec backend pytest -v` — all green.
- [ ] Run backend quality gates: `docker-compose exec backend ruff check . && docker-compose exec backend mypy app/`.
- [ ] Run the complete frontend suite: `docker-compose exec frontend npm run test:watch -- --run` — all green.
- [ ] Run frontend quality gates: `docker-compose exec frontend npm run lint && docker-compose exec frontend npm run type-check`.
- [ ] `docker-compose exec backend uv run alembic heads` shows exactly one head.
- [ ] `docker-compose exec backend uv run python -m app.db.seed.seed_exercises` runs clean (validates and classifies all 148 exercises without error).
- [ ] Manual walkthrough at http://localhost:5173: onboarding → program creation, selecting each progression style × effort method combination; confirm week 1 vs. week 4 preview differs for "variable" but stays flat (besides load increments) for "consistent"; confirm the effort target shown next to each set matches the chosen method; confirm a `%1RM` program's required-input step still collects a number (semantics shift to "1RM" is a copy-only change, not required for this plan).
