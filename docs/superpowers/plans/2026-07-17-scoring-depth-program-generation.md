# Scoring-Depth Program Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make template matching and exercise selection in MyGym's program engine substantially smarter — movement preferences, focus + complementary balance, periodization alignment, and week-to-week variety — while staying deterministic, fast (<500ms), and ML-ready.

**Architecture:** Rewrite the two existing lexicographic/fixed-weight scorers (`selection.py`'s tuple `_score`, `matching.py`'s 4-factor `WEIGHTS` dict) into weighted-linear-sum scorers behind `ExerciseScorer`/`TemplateScorer` protocols, fed by pure feature-extraction functions. Add two new small modules (`preferences.py` for equipment-family mapping, `complementation.py` for muscle-coverage balancing) and one new column (`rotation_pool`) for week-to-week rotation. All new signals are per-program, stored in `WorkoutProgram.constraints`, and default to values that reproduce today's exact output.

**Tech Stack:** FastAPI + Pydantic V2 + SQLAlchemy 2.0 async + Alembic (backend), React + TypeScript + Vitest (frontend), pytest + pytest-asyncio (backend tests).

## Global Constraints

- TDD: write the failing test before the implementation for every step below.
- Backend: `docker-compose exec backend pytest`, `docker-compose exec backend ruff check . --fix`, `docker-compose exec backend mypy app/`.
- Frontend: `docker-compose exec frontend npm run test:watch`, `docker-compose exec frontend npm run type-check`.
- Backward compatible: omitting a new request field must reproduce today's exact output. Existing tests in `test_matching.py`, `test_selection.py`, `test_drafting.py`, `test_preview.py`, `test_program_api_schemas.py` must keep passing **unmodified** except where a task explicitly extends them.
- Soft over hard: preferences are weights, never filters. Equipment feasibility and injury contraindications remain the only hard gates.
- Alembic migrations must be reversible (`upgrade` and `downgrade` both implemented).
- Commit after every task (not every step) with a `feat(program-engine): ...` prefix, matching this repo's existing commit style.
- **Docs decision (confirmed with user):** Phase 6 documentation updates the *existing* `docs/user/PROGRAM_BUILDER.html` and `docs/technical/PROGRAM_GENERATION_TECHNICAL.html` in place — it does **not** create new `PROGRAM_GENERATION.html` / `WORKOUT_PROGRAMS_TECHNICAL.html` files as the spec's §15 literally names them, to avoid two docs covering the same feature.

---

## Phase 1 — Signals & schema (no behavior change yet)

### Task 1: `EquipmentFamily` enum + equipment-family map (`preferences.py`)

**Files:**
- Create: `backend/app/services/program/preferences.py`
- Test: `backend/tests/test_preferences.py`

**Interfaces:**
- Produces: `EquipmentFamily` (str enum: `barbell, dumbbell, kettlebell, machine, cable, bodyweight, bands`), `EQUIPMENT_FAMILY: dict[str, EquipmentFamily]` (all 38 seeded `Equipment` tag values), `movement_preference_weight(ex, prefs: dict[str, float]) -> float`.

**Context:** This is the single authority mapping the granular `Exercise.equipment_tags` (38 values, see `backend/app/models/exercise.py:38-76`) up to 7 coarse families. `bench` and `squat_rack` are support furniture, not a movement family of their own — mapped to `bodyweight` (neutral by default); since `movement_preference_weight` takes the **max** across an exercise's tags, this never drags down a barbell-tagged compound lift.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_preferences.py
from app.services.program.preferences import EQUIPMENT_FAMILY, movement_preference_weight


class _Ex:
    def __init__(self, equipment_tags):
        self.equipment_tags = equipment_tags


def test_all_seeded_equipment_tags_have_a_family():
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
    assert seeded <= set(EQUIPMENT_FAMILY.keys())


def test_neutral_weight_when_prefs_empty():
    ex = _Ex(["barbell"])
    assert movement_preference_weight(ex, {}) == 1.0


def test_takes_max_family_weight_among_tags_not_mean():
    ex = _Ex(["barbell", "bench"])  # bench -> bodyweight, left unset -> neutral 1.0
    prefs = {"barbell": 1.8, "bodyweight": 0.2}
    assert movement_preference_weight(ex, prefs) == 1.8


def test_missing_family_in_prefs_is_neutral():
    ex = _Ex(["kettlebell"])
    prefs = {"barbell": 2.0}  # kettlebell family unset
    assert movement_preference_weight(ex, prefs) == 1.0


def test_bodyweight_none_tag_reads_neutral_family_by_default():
    ex = _Ex(["none"])
    assert movement_preference_weight(ex, {"bodyweight": 1.7}) == 1.7
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker-compose exec backend pytest tests/test_preferences.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.program.preferences'`

- [ ] **Step 3: Write the implementation**

```python
# backend/app/services/program/preferences.py
import enum

from app.models.exercise import Exercise


class EquipmentFamily(str, enum.Enum):
    BARBELL = "barbell"
    DUMBBELL = "dumbbell"
    KETTLEBELL = "kettlebell"
    MACHINE = "machine"
    CABLE = "cable"
    BODYWEIGHT = "bodyweight"
    BANDS = "bands"


EQUIPMENT_FAMILY: dict[str, EquipmentFamily] = {
    "barbell": EquipmentFamily.BARBELL,
    "ez_bar": EquipmentFamily.BARBELL,
    "dumbbells": EquipmentFamily.DUMBBELL,
    "kettlebell": EquipmentFamily.KETTLEBELL,
    "cable_machine": EquipmentFamily.CABLE,
    "resistance_bands": EquipmentFamily.BANDS,
    "none": EquipmentFamily.BODYWEIGHT,
    "bench": EquipmentFamily.BODYWEIGHT,
    "squat_rack": EquipmentFamily.BODYWEIGHT,
    "pull_up_bar": EquipmentFamily.BODYWEIGHT,
    "gymnastic_rings": EquipmentFamily.BODYWEIGHT,
    "ab_wheel": EquipmentFamily.BODYWEIGHT,
    "plyo_box": EquipmentFamily.BODYWEIGHT,
    "jump_rope": EquipmentFamily.BODYWEIGHT,
    "battle_ropes": EquipmentFamily.BODYWEIGHT,
    "medicine_ball": EquipmentFamily.BODYWEIGHT,
    "sandbag": EquipmentFamily.BODYWEIGHT,
    "assisted_dip_machine": EquipmentFamily.MACHINE,
    "assisted_pullup_machine": EquipmentFamily.MACHINE,
    "calf_raise_machine": EquipmentFamily.MACHINE,
    "chest_press_machine": EquipmentFamily.MACHINE,
    "hack_squat_machine": EquipmentFamily.MACHINE,
    "hip_abduction_machine": EquipmentFamily.MACHINE,
    "hip_adduction_machine": EquipmentFamily.MACHINE,
    "lat_pulldown_machine": EquipmentFamily.MACHINE,
    "leg_curl_machine": EquipmentFamily.MACHINE,
    "leg_extension_machine": EquipmentFamily.MACHINE,
    "leg_press_machine": EquipmentFamily.MACHINE,
    "pec_deck_machine": EquipmentFamily.MACHINE,
    "seated_row_machine": EquipmentFamily.MACHINE,
    "shoulder_press_machine": EquipmentFamily.MACHINE,
    "rowing_machine": EquipmentFamily.MACHINE,
    "stair_climber": EquipmentFamily.MACHINE,
    "stationary_bike": EquipmentFamily.MACHINE,
    "treadmill": EquipmentFamily.MACHINE,
    "assault_bike": EquipmentFamily.MACHINE,
    "sled": EquipmentFamily.MACHINE,
    "smith_machine": EquipmentFamily.MACHINE,
}


def movement_preference_weight(ex: Exercise, prefs: dict[str, float]) -> float:
    if not prefs:
        return 1.0
    weights = []
    for tag in ex.equipment_tags:
        family = EQUIPMENT_FAMILY.get(tag)
        if family is not None:
            weights.append(prefs.get(family.value, 1.0))
    return max(weights) if weights else 1.0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker-compose exec backend pytest tests/test_preferences.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/program/preferences.py backend/tests/test_preferences.py
git commit -m "feat(program-engine): add equipment-family map for movement preferences"
```

---

### Task 2: New request/constraints fields (`VarietyPreference`, `MatchRequest`, `DraftRequest`, `ProgramCreationRequest`)

**Files:**
- Modify: `backend/app/schemas/program.py`
- Modify: `backend/app/schemas/program_api.py`
- Test: `backend/tests/test_program_api_schemas.py`

**Interfaces:**
- Produces: `VarietyPreference` enum (`low`/`medium`/`high`) in `app.schemas.program`. `MatchRequest` gains `progression_style: ProgressionStyle = ProgressionStyle.CONSISTENT`, `movement_preferences: dict[str, float] = {}`, `complementary_focus: bool = True`, `variety_preference: VarietyPreference = VarietyPreference.LOW`. `DraftRequest` inherits all of these (its own duplicate `progression_style` declaration is removed since it now comes from `MatchRequest`).
- Consumes: nothing new.

**Context:** `progression_style` moves from `DraftRequest`-only to `MatchRequest` (backward compatible — it has a default) because Phase 4's periodization matching factor needs it at **match** time, before a template is chosen. `movement_preferences` is validated for numeric range only (`[0.0, 2.0]`) — not against known family names — because schemas must not import from `app.services` (checked: no existing schema imports `app.services`, keeping that one-directional). An unknown family key is harmless: `movement_preference_weight` just never looks it up, consistent with "soft, never a hard filter."

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_program_api_schemas.py — add these, keep existing tests unmodified
import pytest
from pydantic import ValidationError

from app.schemas.program_api import MatchRequest


def _base_kwargs():
    return dict(environment_id=1, days_per_week=3, session_duration_min=60, fitness_focus="strength")


def test_match_request_defaults_new_signals():
    req = MatchRequest(**_base_kwargs())
    assert req.movement_preferences == {}
    assert req.complementary_focus is True
    assert req.variety_preference.value == "low"
    assert req.progression_style.value == "consistent"


def test_match_request_rejects_out_of_range_movement_preference():
    with pytest.raises(ValidationError):
        MatchRequest(**_base_kwargs(), movement_preferences={"barbell": 2.5})


def test_match_request_accepts_movement_preferences_in_range():
    req = MatchRequest(**_base_kwargs(), movement_preferences={"kettlebell": 1.5, "machine": 0.0})
    assert req.movement_preferences == {"kettlebell": 1.5, "machine": 0.0}


def test_draft_request_inherits_new_signals():
    from app.schemas.program_api import DraftRequest

    req = DraftRequest(
        template_id=2, environment_id=1, days_per_week=4, session_duration_min=60,
        fitness_focus="strength", weight_unit="kg", duration_weeks=8,
        variety_preference="high",
    )
    assert req.variety_preference.value == "high"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker-compose exec backend pytest tests/test_program_api_schemas.py -v`
Expected: FAIL — `MatchRequest` has no field `movement_preferences`

- [ ] **Step 3: Write the implementation**

```python
# backend/app/schemas/program.py — add this enum near ProgressionStyle/EffortMethod
class VarietyPreference(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
```

```python
# backend/app/schemas/program_api.py — full new file content
from pydantic import BaseModel, ConfigDict, field_validator

from app.schemas.program import EffortMethod, ProgressionStyle, VarietyPreference


class MatchRequest(BaseModel):
    environment_id: int
    days_per_week: int
    session_duration_min: int
    fitness_focus: str
    weight_unit: str = "kg"
    duration_weeks: int = 8
    progression_style: ProgressionStyle = ProgressionStyle.CONSISTENT
    movement_preferences: dict[str, float] = {}
    complementary_focus: bool = True
    variety_preference: VarietyPreference = VarietyPreference.LOW

    @field_validator("movement_preferences")
    @classmethod
    def _validate_weight_range(cls, v: dict[str, float]) -> dict[str, float]:
        for family, weight in v.items():
            if not 0.0 <= weight <= 2.0:
                raise ValueError(f"movement_preferences weight for '{family}' must be in [0.0, 2.0], got {weight}")
        return v


class TemplateMatchOut(BaseModel):
    template_id: int
    slug: str
    name: str
    fit_pct: int
    factors: dict[str, float]
    required_inputs: list[dict[str, object]]


class DraftRequest(MatchRequest):
    template_id: int
    required_inputs: dict[str, float] = {}
    effort_method: EffortMethod | None = None


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
    exercise_name: str
    sets: int
    reps: int
    load: float | None
    rest_seconds: int
    note: str | None
    is_locked: bool
    is_user_swapped: bool
    effort_target: dict[str, object] | None = None
    rotation_pool: list[int] = []


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

```python
# backend/app/schemas/program.py — extend ProgramCreationRequest (currently unused by any route,
# but the spec names it explicitly; keep it in sync for when it's wired up)
class ProgramCreationRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    environment_id: int
    days_per_week: int
    preferred_days: list[DayOfWeek]
    session_duration_min: int
    start_date: date
    focus_areas: list[FocusArea] = []
    weight_unit: WeightUnit
    available_weight_increments: list[float] = []
    progression_style: ProgressionStyle
    movement_preferences: dict[str, float] = {}
    complementary_focus: bool = True
    variety_preference: VarietyPreference = VarietyPreference.LOW
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker-compose exec backend pytest tests/test_program_api_schemas.py -v`
Expected: PASS (all tests, including the 5 pre-existing ones unmodified)

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/program.py backend/app/schemas/program_api.py backend/tests/test_program_api_schemas.py
git commit -m "feat(program-engine): add movement/complementary/variety signals to program request schemas"
```

---

### Task 3: `rotation_pool` column + migration

**Files:**
- Modify: `backend/app/models/program.py`
- Create: `backend/alembic/versions/e1f2a3b4c5d6_add_rotation_pool_to_workout_exercises.py`
- Test: `backend/tests/test_program_models.py`

**Interfaces:**
- Produces: `WorkoutExercise.rotation_pool: list[int]` (JSON, default `[]`).

**Context:** Current alembic head is `d4e5f6a7b8c9` (confirmed via `down_revision` chain — no other heads exist). This is a plain additive column; no data backfill needed since `default=list` at the Python level and `server_default="[]"` at the DB level both produce an empty list for existing/new rows.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_program_models.py — add this test, keep the existing one unmodified
@pytest.mark.asyncio
async def test_workout_exercise_rotation_pool_defaults_to_empty_list(db_session: AsyncSession, test_user):
    template = ProgramTemplate(
        name="Rotation Test", slug="rotation-test", description="", goals=["strength"],
        experience_levels=["intermediate"], days_per_week_min=3, days_per_week_max=3,
        session_duration_min=45, session_duration_max=75, split={"sessions": []},
        progression_ref={"model_key": "linear_load", "params": {}}, required_inputs=[],
    )
    db_session.add(template)
    await db_session.flush()

    program = WorkoutProgram(
        user_id=test_user.id, template_id=template.id, environment_id=1, name="P",
        status=ProgramStatus.DRAFT, duration_weeks=8, days_per_week=3, weight_unit="kg",
        constraints={},
    )
    db_session.add(program)
    await db_session.flush()

    workout = Workout(program_id=program.id, key="a", name="A", order=1)
    db_session.add(workout)
    await db_session.flush()

    slot = WorkoutExercise(
        workout_id=workout.id, order=1, exercise_id=1, fills_rule={"pattern": "squat"},
        sets=3, reps_min=5, reps_max=5, rest_seconds=120, scheme_key="main",
        is_locked=False, is_user_swapped=False,
    )
    db_session.add(slot)
    await db_session.commit()
    await db_session.refresh(slot)

    assert slot.rotation_pool == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker-compose exec backend pytest tests/test_program_models.py -v`
Expected: FAIL — `TypeError: 'rotation_pool' is an invalid keyword argument` or `AttributeError`

- [ ] **Step 3: Write the implementation**

```python
# backend/app/models/program.py — add to WorkoutExercise, right after is_user_swapped
    rotation_pool: Mapped[list[int]] = mapped_column(JSON, nullable=False, default=list)
```

```python
# backend/alembic/versions/e1f2a3b4c5d6_add_rotation_pool_to_workout_exercises.py
"""add rotation_pool to workout_exercises

Revision ID: e1f2a3b4c5d6
Revises: d4e5f6a7b8c9
Create Date: 2026-07-17 09:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "workout_exercises",
        sa.Column("rotation_pool", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.alter_column("workout_exercises", "rotation_pool", server_default=None)


def downgrade() -> None:
    op.drop_column("workout_exercises", "rotation_pool")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker-compose exec backend pytest tests/test_program_models.py -v`
Expected: PASS (both tests)

Also verify the migration applies cleanly against Postgres:
Run: `docker-compose exec backend alembic upgrade head` then `docker-compose exec backend alembic downgrade -1 && docker-compose exec backend alembic upgrade head`
Expected: no errors in either direction

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/program.py backend/alembic/versions/e1f2a3b4c5d6_add_rotation_pool_to_workout_exercises.py backend/tests/test_program_models.py
git commit -m "feat(program-engine): add rotation_pool column to workout_exercises"
```

---

## Phase 2 — Selection depth (weighted scoring + movement preference)

### Task 4: `SelectionWeights` + `ExerciseScorer` + weighted rewrite of `select_for_slot`

**Files:**
- Modify: `backend/app/services/program/selection.py`
- Test: `backend/tests/test_selection.py`

**Interfaces:**
- Produces: `SelectionWeights` (frozen dataclass), `ExerciseScorer` (Protocol), `HeuristicExerciseScorer`, extended `SelectionContext` (adds `movement_preferences: dict[str, float]`, `muscle_coverage: Counter[str]`, `complementary_focus: bool`, `weights: SelectionWeights` — all with neutral defaults, positional signature unchanged), `ranked_pool_for_slot(candidates, rule, ctx, excluded_ids) -> list[Exercise]` (descending by score).
- Consumes: `movement_preference_weight` from `app.services.program.preferences` (Task 1).

**Context:** This replaces the tuple `_score` with a weighted linear sum of a normalized feature dict. Manually verifying against the 5 existing `test_selection.py` cases with default weights (`priority_fit=1.5`, `unilateral_balance=0.5`, others tied at 1.0 given empty/neutral context) shows every existing assertion still resolves to the same winner — **no re-baselining needed for this fixture set**. Still run the full suite in Step 4 to confirm; if any assertion legitimately flips due to a genuine tie-break change under the new formula, update that one assertion with a comment `# re-baselined for weighted scoring (docs/superpowers/plans/2026-07-17-scoring-depth-program-generation.md)` — do not touch assertions that still pass.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_selection.py — add these new tests below the existing 5 (which stay unmodified)
def test_movement_preference_biases_selection_without_excluding_others():
    from app.services.program.selection import SelectionContext, select_for_slot
    from app.schemas.template import SlotRule

    barbell_ex = _Ex(1, "bb-row", "row", "horizontal_pull", "upper_body", ["lats"], ["barbell"], "intermediate", [])
    kb_ex = _Ex(2, "kb-row", "kb_row", "horizontal_pull", "upper_body", ["lats"], ["kettlebell"], "intermediate", [])
    rule = SlotRule(pattern="horizontal_pull", priority="accessory", scheme="accessory")
    ctx = SelectionContext(
        ["barbell", "kettlebell"], "intermediate", [], set(),
        movement_preferences={"kettlebell": 2.0, "barbell": 0.2},
    )
    chosen = select_for_slot([barbell_ex, kb_ex], rule, ctx, None, set())
    assert chosen.id == 2  # kettlebell strongly preferred


def test_movement_preference_never_empties_a_slot():
    # even with barbell fully deprioritized, it must still be selectable if it's the only candidate
    from app.services.program.selection import SelectionContext, select_for_slot
    from app.schemas.template import SlotRule

    only_option = _Ex(1, "bb-row", "row", "horizontal_pull", "upper_body", ["lats"], ["barbell"], "intermediate", [])
    rule = SlotRule(pattern="horizontal_pull", priority="accessory", scheme="accessory")
    ctx = SelectionContext(["barbell"], "intermediate", [], set(), movement_preferences={"barbell": 0.0})
    chosen = select_for_slot([only_option], rule, ctx, None, set())
    assert chosen.id == 1


def test_ranked_pool_for_slot_returns_descending_order():
    from app.services.program.selection import SelectionContext, ranked_pool_for_slot
    from app.schemas.template import SlotRule

    preferred = _Ex(1, "kb-row", "kb_row", "horizontal_pull", "upper_body", ["lats"], ["kettlebell"], "intermediate", [])
    other = _Ex(2, "bb-row", "row", "horizontal_pull", "upper_body", ["lats"], ["barbell"], "intermediate", [])
    rule = SlotRule(pattern="horizontal_pull", priority="accessory", scheme="accessory")
    ctx = SelectionContext(
        ["barbell", "kettlebell"], "intermediate", [], set(), movement_preferences={"kettlebell": 2.0}
    )
    ranked = ranked_pool_for_slot([other, preferred], rule, ctx, set())
    assert [ex.id for ex in ranked] == [1, 2]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker-compose exec backend pytest tests/test_selection.py -v`
Expected: FAIL — `SelectionContext.__init__() got an unexpected keyword argument 'movement_preferences'`

- [ ] **Step 3: Write the implementation**

```python
# backend/app/services/program/selection.py — full new file content
from collections import Counter
from dataclasses import dataclass, field
from typing import Protocol

from app.models.exercise import Exercise
from app.schemas.template import SlotRule
from app.services.program.complementation import coverage_deficit
from app.services.program.preferences import movement_preference_weight

EXPERIENCE_ORDER = {"beginner": 0, "intermediate": 1, "advanced": 2}


@dataclass(frozen=True)
class SelectionWeights:
    variety: float = 1.0
    priority_fit: float = 1.5
    muscle_fit: float = 1.0
    difficulty: float = 0.75
    unilateral_balance: float = 0.5
    movement_preference: float = 1.25
    complementary_coverage: float = 1.25


class ExerciseScorer(Protocol):
    def score(self, features: dict[str, float]) -> float: ...


@dataclass(frozen=True)
class HeuristicExerciseScorer:
    weights: SelectionWeights = field(default_factory=SelectionWeights)

    def score(self, features: dict[str, float]) -> float:
        w = self.weights
        return (
            w.variety * features["variety"]
            + w.priority_fit * features["priority_fit"]
            + w.muscle_fit * features["muscle_fit"]
            + w.difficulty * features["difficulty"]
            + w.unilateral_balance * features["unilateral_balance"]
            + w.movement_preference * features["movement_preference"]
            + w.complementary_coverage * features["complementary_coverage"]
        )


@dataclass
class SelectionContext:
    equipment: list[str]
    experience: str
    injuries: list[str]
    used_movement_slugs: set[str]
    used_unilateral_flags: list[bool] = field(default_factory=list)
    movement_preferences: dict[str, float] = field(default_factory=dict)
    muscle_coverage: "Counter[str]" = field(default_factory=Counter)
    complementary_focus: bool = True
    weights: SelectionWeights = field(default_factory=SelectionWeights)


def _matches_rule(ex: Exercise, rule: SlotRule) -> bool:
    if rule.pattern and ex.movement_pattern.value != rule.pattern:
        return False
    if rule.region and ex.body_region.value != rule.region:
        return False
    if rule.muscles and not (set(rule.muscles) & set(ex.primary_muscles)):
        return False
    return True


def _passes_filters(ex: Exercise, ctx: SelectionContext, tolerance: int = 1) -> bool:
    if not set(ex.equipment_tags) <= set(ctx.equipment):
        return False
    if EXPERIENCE_ORDER[ex.difficulty_level.value] > EXPERIENCE_ORDER[ctx.experience] + tolerance:
        return False
    if set(ex.contraindications) & set(ctx.injuries):
        return False
    return True


def _extract_features(ex: Exercise, rule: SlotRule, ctx: SelectionContext) -> dict[str, float]:
    muscle_fit = (
        len(set(rule.muscles) & set(ex.primary_muscles)) / max(1, len(rule.muscles)) if rule.muscles else 0.0
    )
    variety = 0.0 if ex.movement_slug in ctx.used_movement_slugs else 1.0
    difficulty = 1.0 - abs(EXPERIENCE_ORDER[ex.difficulty_level.value] - EXPERIENCE_ORDER[ctx.experience]) / 2
    priority_fit = 1.0 if (rule.priority == "primary") == ex.is_compound else 0.0
    unilateral_balance = 1.0
    if ctx.used_unilateral_flags and ctx.used_unilateral_flags[-1] == ex.is_unilateral:
        unilateral_balance = 0.0
    movement_preference = movement_preference_weight(ex, ctx.movement_preferences) / 2
    if rule.priority == "primary" or not ctx.complementary_focus:
        complementary_coverage = 0.5
    else:
        complementary_coverage = coverage_deficit(ex.primary_muscles, ctx.muscle_coverage)
    return {
        "variety": variety,
        "priority_fit": priority_fit,
        "muscle_fit": muscle_fit,
        "difficulty": difficulty,
        "unilateral_balance": unilateral_balance,
        "movement_preference": movement_preference,
        "complementary_coverage": complementary_coverage,
    }


def _ranked_pool(
    candidates: list[Exercise], rule: SlotRule, ctx: SelectionContext, excluded_ids: set[int]
) -> list[Exercise]:
    pool = [
        ex for ex in candidates if ex.id not in excluded_ids and _matches_rule(ex, rule) and _passes_filters(ex, ctx)
    ]
    if not pool:  # fallback: relax difficulty tolerance
        pool = [
            ex
            for ex in candidates
            if ex.id not in excluded_ids and _matches_rule(ex, rule) and _passes_filters(ex, ctx, tolerance=99)
        ]
    if not pool:
        return []
    scorer = HeuristicExerciseScorer(ctx.weights)
    return sorted(pool, key=lambda ex: scorer.score(_extract_features(ex, rule, ctx)), reverse=True)


def ranked_pool_for_slot(
    candidates: list[Exercise], rule: SlotRule, ctx: SelectionContext, excluded_ids: set[int]
) -> list[Exercise]:
    return _ranked_pool(candidates, rule, ctx, excluded_ids)


def select_for_slot(
    candidates: list[Exercise],
    rule: SlotRule,
    ctx: SelectionContext,
    locked_exercise_id: int | None,
    excluded_ids: set[int],
) -> Exercise | None:
    if locked_exercise_id is not None:
        for ex in candidates:
            if ex.id == locked_exercise_id:
                return ex
    ranked = _ranked_pool(candidates, rule, ctx, excluded_ids)
    return ranked[0] if ranked else None


def template_is_feasible(sessions: list[object], all_exercises: list[Exercise], equipment: list[str]) -> bool:
    ctx = SelectionContext(list(equipment), "advanced", [], set())
    for session in sessions:
        for slot in getattr(session, "slots"):
            if select_for_slot(all_exercises, slot, ctx, None, set()) is None:
                return False
    return True
```

Note: this imports `coverage_deficit` from `app.services.program.complementation`, which does not exist yet — Task 6 (Phase 3) creates it. To keep Task 4 shippable on its own, create a minimal stub now (Task 6 replaces it with the full implementation):

```python
# backend/app/services/program/complementation.py — minimal stub for this task; Task 6 extends it
from collections import Counter


def coverage_deficit(muscles: list[str], coverage: "Counter[str]") -> float:
    if not muscles:
        return 0.5
    mean_cov = sum(coverage[m] for m in muscles) / len(muscles)
    max_cov = max(coverage.values(), default=0)
    return 1 - mean_cov / (1 + max_cov)
```

(This is in fact the complete, correct formula from spec §14.3 — Task 6 only *adds* `is_core`/`antagonist_pattern` to this file, it does not change this function.)

- [ ] **Step 4: Run test to verify it passes**

Run: `docker-compose exec backend pytest tests/test_selection.py -v`
Expected: PASS (all 8 tests: 5 pre-existing + 3 new). If a pre-existing test fails, inspect whether the new winner is a legitimate pick under the weighted formula (not a logic bug) before updating its assertion.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/program/selection.py backend/app/services/program/complementation.py backend/tests/test_selection.py
git commit -m "feat(program-engine): weighted exercise scoring with movement-preference feature"
```

---

### Task 5: Wire `movement_preferences` from API into selection context + persist in constraints

**Files:**
- Modify: `backend/app/api/v1/endpoints/programs.py`
- Modify: `backend/app/services/program/drafting.py`
- Test: `backend/tests/test_drafting.py`

**Interfaces:**
- Consumes: `SelectionContext.movement_preferences` (Task 4), `DraftRequest.movement_preferences` (Task 2).
- Produces: `build_draft(...)` output now includes `"movement_preferences"` in `program.constraints`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_drafting.py — add this test
@pytest.mark.asyncio
async def test_build_draft_stores_movement_preferences_in_constraints(sample_template_orm, sample_exercises):
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(
        equipment=["barbell", "bench", "squat_rack"], experience="intermediate", injuries=[], used_movement_slugs=set(),
        movement_preferences={"kettlebell": 1.5},
    )
    program = build_draft(
        sample_template_orm, definition, ctx, sample_exercises,
        user_id=1, environment_id=1, days_per_week=3, duration_weeks=8, weight_unit="kg",
        required_inputs={"squat_start": 80, "bench_start": 60},
    )
    assert program.constraints["movement_preferences"] == {"kettlebell": 1.5}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker-compose exec backend pytest tests/test_drafting.py -v -k movement_preferences`
Expected: FAIL — `KeyError: 'movement_preferences'`

- [ ] **Step 3: Write the implementation**

```python
# backend/app/services/program/drafting.py — modify the constraints dict inside build_draft
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
            "movement_preferences": ctx.movement_preferences,
        },
    )
```

```python
# backend/app/api/v1/endpoints/programs.py — update _ctx_for signature and its callers
async def _ctx_for(
    db: AsyncSession,
    user: User,
    environment: TrainingEnvironment,
    *,
    movement_preferences: dict[str, float] | None = None,
) -> SelectionContext:
    profile = user.profile
    injuries = []
    if profile and profile.injuries_limitations:
        injuries = [w.strip().lower() for w in profile.injuries_limitations.split(",") if w.strip()]
    experience = profile.experience_level.value if profile and profile.experience_level else "beginner"
    return SelectionContext(
        list(environment.equipment_tags), experience, injuries, set(),
        movement_preferences=movement_preferences or {},
    )
```

```python
# backend/app/api/v1/endpoints/programs.py — in draft(), pass the request's preferences
    ctx = await _ctx_for(db, user, environment, movement_preferences=data.movement_preferences)
```

```python
# backend/app/api/v1/endpoints/programs.py — in feedback() and alternatives(), read from the
# already-persisted program constraints instead (the request body doesn't carry these fields)
    ctx = await _ctx_for(
        db, user, environment,
        movement_preferences=program.constraints.get("movement_preferences", {}),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker-compose exec backend pytest tests/test_drafting.py backend/tests/test_programs_flow.py -v`
Expected: PASS (all tests, including all pre-existing ones)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/program/drafting.py backend/app/api/v1/endpoints/programs.py backend/tests/test_drafting.py
git commit -m "feat(program-engine): wire movement_preferences through draft/feedback endpoints"
```

---

## Phase 3 — Smart complementation

### Task 6: `complementation.py` — `is_core`, antagonist grouping (full module)

**Files:**
- Modify: `backend/app/services/program/complementation.py` (replaces Task 4's stub)
- Test: `backend/tests/test_complementation.py`

**Interfaces:**
- Produces: `coverage_deficit(muscles, coverage) -> float` (unchanged from the Task 4 stub), `is_core(ex) -> bool`, `antagonist_pattern(pattern: str) -> str | None`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_complementation.py
from collections import Counter

from app.services.program.complementation import antagonist_pattern, coverage_deficit, is_core


class _Ex:
    def __init__(self, region):
        self.body_region = type("R", (), {"value": region})


def test_coverage_deficit_uniform_when_session_empty():
    coverage = Counter()
    assert coverage_deficit(["chest"], coverage) == 1.0
    assert coverage_deficit(["lats"], coverage) == 1.0


def test_coverage_deficit_favors_undercovered_muscles():
    coverage = Counter({"chest": 3, "shoulders_anterior": 2})
    undercovered = coverage_deficit(["lats"], coverage)
    overcovered = coverage_deficit(["chest"], coverage)
    assert undercovered > overcovered


def test_coverage_deficit_neutral_when_muscles_empty():
    assert coverage_deficit([], Counter()) == 0.5


def test_is_core_true_for_core_region():
    assert is_core(_Ex("core")) is True
    assert is_core(_Ex("upper_body")) is False


def test_antagonist_pattern_pairs():
    assert antagonist_pattern("horizontal_push") == "horizontal_pull"
    assert antagonist_pattern("horizontal_pull") == "horizontal_push"
    assert antagonist_pattern("squat") == "hinge"
    assert antagonist_pattern("hinge") == "squat"
    assert antagonist_pattern("isolation") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker-compose exec backend pytest tests/test_complementation.py -v`
Expected: FAIL — `ImportError: cannot import name 'is_core'`

- [ ] **Step 3: Write the implementation**

```python
# backend/app/services/program/complementation.py — full new file content
from collections import Counter

from app.models.exercise import Exercise


def coverage_deficit(muscles: list[str], coverage: "Counter[str]") -> float:
    if not muscles:
        return 0.5
    mean_cov = sum(coverage[m] for m in muscles) / len(muscles)
    max_cov = max(coverage.values(), default=0)
    return 1 - mean_cov / (1 + max_cov)


def is_core(ex: Exercise) -> bool:
    return ex.body_region.value == "core"


ANTAGONIST_PATTERNS: dict[str, str] = {
    "horizontal_push": "horizontal_pull",
    "horizontal_pull": "horizontal_push",
    "vertical_push": "vertical_pull",
    "vertical_pull": "vertical_push",
    "squat": "hinge",
    "hinge": "squat",
}


def antagonist_pattern(pattern: str) -> str | None:
    return ANTAGONIST_PATTERNS.get(pattern)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker-compose exec backend pytest tests/test_complementation.py tests/test_selection.py -v`
Expected: PASS (complementation tests + selection tests still green, since `_extract_features` already used `coverage_deficit` from this module)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/program/complementation.py backend/tests/test_complementation.py
git commit -m "feat(program-engine): add is_core + antagonist-pattern grouping to complementation module"
```

---

### Task 7: Wire `complementary_focus` + live muscle-coverage tracking in `build_draft`

**Files:**
- Modify: `backend/app/services/program/drafting.py`
- Modify: `backend/app/api/v1/endpoints/programs.py`
- Test: `backend/tests/test_drafting.py`

**Interfaces:**
- Consumes: `SelectionContext.muscle_coverage`, `SelectionContext.complementary_focus` (Task 4).
- Produces: `build_draft` updates `ctx.muscle_coverage` after every pick and persists `complementary_focus` in constraints.

**Context:** This is the piece that turns "focus upper body" into "upper-body primary + balanced pull/rear-delt/core accessories" — after each slot is filled, the chosen exercise's `primary_muscles` are added to a running `Counter`, so later accessory slots in the same session see which muscles are already well-trained and the `complementary_coverage` feature (Task 4) rewards the under-trained ones.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_drafting.py — add these two tests
@pytest.mark.asyncio
async def test_build_draft_stores_complementary_focus_in_constraints(sample_template_orm, sample_exercises):
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(
        equipment=["barbell", "bench", "squat_rack"], experience="intermediate", injuries=[], used_movement_slugs=set(),
        complementary_focus=False,
    )
    program = build_draft(
        sample_template_orm, definition, ctx, sample_exercises,
        user_id=1, environment_id=1, days_per_week=3, duration_weeks=8, weight_unit="kg",
        required_inputs={"squat_start": 80, "bench_start": 60},
    )
    assert program.constraints["complementary_focus"] is False


@pytest.mark.asyncio
async def test_build_draft_updates_muscle_coverage_after_each_pick(sample_template_orm, sample_exercises):
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(
        equipment=["barbell", "bench", "squat_rack"], experience="intermediate", injuries=[], used_movement_slugs=set(),
    )
    assert sum(ctx.muscle_coverage.values()) == 0
    build_draft(
        sample_template_orm, definition, ctx, sample_exercises,
        user_id=1, environment_id=1, days_per_week=3, duration_weeks=8, weight_unit="kg",
        required_inputs={"squat_start": 80, "bench_start": 60},
    )
    assert sum(ctx.muscle_coverage.values()) > 0  # at least one primary muscle was tallied
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker-compose exec backend pytest tests/test_drafting.py -v -k "complementary_focus or muscle_coverage"`
Expected: FAIL — `KeyError: 'complementary_focus'` / coverage assertion fails (still 0)

- [ ] **Step 3: Write the implementation**

```python
# backend/app/services/program/drafting.py — full new file content
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
            "movement_preferences": ctx.movement_preferences,
            "complementary_focus": ctx.complementary_focus,
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
            for muscle in chosen.primary_muscles:
                ctx.muscle_coverage[muscle] += 1
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

```python
# backend/app/api/v1/endpoints/programs.py — extend _ctx_for and its call sites again
async def _ctx_for(
    db: AsyncSession,
    user: User,
    environment: TrainingEnvironment,
    *,
    movement_preferences: dict[str, float] | None = None,
    complementary_focus: bool = True,
) -> SelectionContext:
    profile = user.profile
    injuries = []
    if profile and profile.injuries_limitations:
        injuries = [w.strip().lower() for w in profile.injuries_limitations.split(",") if w.strip()]
    experience = profile.experience_level.value if profile and profile.experience_level else "beginner"
    return SelectionContext(
        list(environment.equipment_tags), experience, injuries, set(),
        movement_preferences=movement_preferences or {},
        complementary_focus=complementary_focus,
    )
```

```python
# backend/app/api/v1/endpoints/programs.py — in draft()
    ctx = await _ctx_for(
        db, user, environment,
        movement_preferences=data.movement_preferences,
        complementary_focus=data.complementary_focus,
    )
```

```python
# backend/app/api/v1/endpoints/programs.py — in feedback() and alternatives(), read from constraints
    ctx = await _ctx_for(
        db, user, environment,
        movement_preferences=program.constraints.get("movement_preferences", {}),
        complementary_focus=program.constraints.get("complementary_focus", True),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker-compose exec backend pytest tests/test_drafting.py tests/test_programs_flow.py -v`
Expected: PASS (all tests, including all pre-existing ones)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/program/drafting.py backend/app/api/v1/endpoints/programs.py backend/tests/test_drafting.py
git commit -m "feat(program-engine): track live muscle coverage and wire complementary_focus through draft"
```

---

## Phase 4 — Matching depth

### Task 8: `MatchWeights` + `TemplateScorer` + three new matching factors

**Files:**
- Modify: `backend/app/services/program/matching.py`
- Test: `backend/tests/test_matching.py`

**Interfaces:**
- Produces: `MatchWeights` (frozen dataclass), `TemplateScorer` (Protocol), `HeuristicTemplateScorer`, extended `MatchInput` (adds `movement_preferences: dict[str, float] = {}`, `complementary_focus: bool = True`, `progression_style: str = "consistent"`), extended `rank_templates(templates, inp, feasibility, definitions=None, all_exercises=None, scorer=None)`.
- Consumes: `TemplateDefinition` (from `app.schemas.template`, already used by `drafting.py`/`preview.py`), `_matches_rule` from `app.services.program.selection` (Task 4), `movement_preference_weight` from `app.services.program.preferences` (Task 1).

**Context:** `rank_templates` gains an optional `definitions: dict[int, TemplateDefinition]` parameter rather than re-parsing `ProgramTemplate.split`/`progression_ref` raw JSON itself — this mirrors how `drafting.py`/`preview.py`/`adaptation.py` already consume the parsed `TemplateDefinition`, and the `match()` endpoint already builds this dict today for feasibility checking (`programs.py:73-78`). When `definitions` is omitted (as in today's tests, which use a bare `_T` fixture with no `split`), the three new factors default to neutral values (`0.5`, `0.5`, `0.3`) — identical for every template, so relative ranking is unaffected and existing assertions hold.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_matching.py — add these tests below the existing 2 (which stay unmodified)
from app.schemas.template import TemplateDefinition


class _TWithSplit(_T):
    def __init__(self, id, slug, goals, exps, dmin, dmax, smin, smax, split, progression_ref):
        super().__init__(id, slug, goals, exps, dmin, dmax, smin, smax)
        self.split = split
        self.progression_ref = progression_ref
        self.required_inputs = []


def _definition_for(t) -> TemplateDefinition:
    return TemplateDefinition.from_orm_template(t)


def test_missing_definitions_produce_neutral_new_factors_for_every_template():
    templates = [
        _T(1, "ul", ["strength"], ["intermediate"], 4, 4, 45, 75),
        _T(2, "fb", ["endurance"], ["beginner"], 3, 3, 30, 45),
    ]
    inp = MatchInput("strength", "intermediate", 4, 60, ["barbell"])
    ranked = rank_templates(templates, inp, feasibility={1: True, 2: True})
    assert ranked[0].factors["movement_preference"] == 0.5
    assert ranked[0].factors["focus_complement"] == 0.5
    assert ranked[0].factors["periodization"] == 0.3


def test_periodization_rewards_matching_progression_style():
    split = {"sessions": [{"key": "a", "name": "A", "order": 1, "slots": [
        {"pattern": "squat", "priority": "primary", "scheme": "main"},
    ]}], "schemes": {"main": {"sets": 3, "reps_min": 5, "reps_max": 5, "rest_seconds": 120}}}
    consistent_t = _TWithSplit(
        1, "linear", ["strength"], ["intermediate"], 4, 4, 45, 75,
        split, {"model_key": "linear_load", "params": {}},
    )
    variable_t = _TWithSplit(
        2, "undulating", ["strength"], ["intermediate"], 4, 4, 45, 75,
        split, {"model_key": "weekly_undulating", "params": {}},
    )
    definitions = {1: _definition_for(consistent_t), 2: _definition_for(variable_t)}
    inp = MatchInput("strength", "intermediate", 4, 60, ["barbell"], progression_style="consistent")
    ranked = rank_templates(
        [consistent_t, variable_t], inp, feasibility={1: True, 2: True}, definitions=definitions
    )
    by_id = {m.template_id: m for m in ranked}
    assert by_id[1].factors["periodization"] == 1.0
    assert by_id[2].factors["periodization"] == 0.3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker-compose exec backend pytest tests/test_matching.py -v`
Expected: FAIL — `KeyError: 'movement_preference'` (factors dict doesn't have the new keys yet)

- [ ] **Step 3: Write the implementation**

```python
# backend/app/services/program/matching.py — full new file content
import logging
from dataclasses import dataclass, field
from typing import Any, Protocol

from app.schemas.template import SlotRule, TemplateDefinition
from app.services.program.preferences import movement_preference_weight
from app.services.program.selection import _matches_rule

logger = logging.getLogger(__name__)

_PATTERN_REGION: dict[str, str] = {
    "squat": "lower_body",
    "hinge": "lower_body",
    "lunge": "lower_body",
    "horizontal_push": "upper_body",
    "vertical_push": "upper_body",
    "horizontal_pull": "upper_body",
    "vertical_pull": "upper_body",
    "rotation": "core",
    "anti_rotation": "core",
    "carry": "full_body",
    "isolation": "upper_body",
    "locomotion": "full_body",
    "mobility": "full_body",
}

_PERIODIZATION_CONSISTENT_MODELS = {"linear_load", "double_progression"}
_PERIODIZATION_VARIABLE_MODELS = {"weekly_undulating"}


@dataclass(frozen=True)
class MatchWeights:
    goal: float = 0.25
    experience: float = 0.20
    days: float = 0.12
    duration: float = 0.08
    movement_preference: float = 0.15
    focus_complement: float = 0.12
    periodization: float = 0.08


class TemplateScorer(Protocol):
    def score(self, features: dict[str, float]) -> float: ...


@dataclass(frozen=True)
class HeuristicTemplateScorer:
    weights: MatchWeights = field(default_factory=MatchWeights)

    def score(self, features: dict[str, float]) -> float:
        w = self.weights
        return (
            w.goal * features["goal"]
            + w.experience * features["experience"]
            + w.days * features["days"]
            + w.duration * features["duration"]
            + w.movement_preference * features["movement_preference"]
            + w.focus_complement * features["focus_complement"]
            + w.periodization * features["periodization"]
        )


@dataclass(frozen=True)
class MatchInput:
    fitness_focus: str
    experience_level: str
    days_per_week: int
    session_duration_min: int
    environment_equipment: list[str]
    movement_preferences: dict[str, float] = field(default_factory=dict)
    complementary_focus: bool = True
    progression_style: str = "consistent"


@dataclass(frozen=True)
class TemplateMatch:
    template_id: int
    slug: str
    name: str
    fit_pct: int
    factors: dict[str, float]


def _range_fit(value: int, low: int, high: int) -> float:
    if low <= value <= high:
        return 1.0
    distance = low - value if value < low else value - high
    return max(0.0, 1.0 - distance / max(low, 1))


def _slot_region(slot: SlotRule) -> str:
    if slot.region:
        return slot.region
    return _PATTERN_REGION.get(slot.pattern or "", "full_body")


def _region_diversity(sessions: list[Any]) -> float:
    regions = {_slot_region(slot) for session in sessions for slot in session.slots}
    return min(1.0, len(regions) / 3)


def _movement_preference_feature(
    sessions: list[Any], all_exercises: list[Any], equipment: list[str], prefs: dict[str, float]
) -> float:
    candidates = [
        ex
        for session in sessions
        for slot in session.slots
        if slot.priority == "primary"
        for ex in all_exercises
        if _matches_rule(ex, slot) and set(ex.equipment_tags) <= set(equipment)
    ]
    if not candidates:
        return 0.5
    return (sum(movement_preference_weight(ex, prefs) for ex in candidates) / len(candidates)) / 2


def _focus_complement_feature(sessions: list[Any], complementary_focus: bool) -> float:
    diversity = _region_diversity(sessions)
    return diversity if complementary_focus else 1.0 - diversity


def _periodization_feature(model_key: str, progression_style: str) -> float:
    if progression_style == "consistent" and model_key in _PERIODIZATION_CONSISTENT_MODELS:
        return 1.0
    if progression_style == "variable" and model_key in _PERIODIZATION_VARIABLE_MODELS:
        return 1.0
    return 0.3


def rank_templates(
    templates: list[Any],
    inp: MatchInput,
    feasibility: dict[int, bool],
    definitions: dict[int, TemplateDefinition] | None = None,
    all_exercises: list[Any] | None = None,
    scorer: TemplateScorer | None = None,
) -> list[TemplateMatch]:
    scorer = scorer or HeuristicTemplateScorer()
    definitions = definitions or {}
    exercises = all_exercises or []
    logger.info(
        f"Matching templates for: fitness_focus={inp.fitness_focus}, experience={inp.experience_level}, "
        f"days_per_week={inp.days_per_week}, session_duration_min={inp.session_duration_min}, "
        f"equipment={inp.environment_equipment}"
    )
    matches: list[TemplateMatch] = []
    for t in templates:
        is_feasible = feasibility.get(t.id, False)
        definition = definitions.get(t.id)
        if definition is not None:
            sessions = definition.split.sessions
            movement_preference = _movement_preference_feature(
                sessions, exercises, inp.environment_equipment, inp.movement_preferences
            )
            focus_complement = _focus_complement_feature(sessions, inp.complementary_focus)
            periodization = _periodization_feature(definition.progression.model_key, inp.progression_style)
        else:
            movement_preference = 0.5
            focus_complement = 0.5
            periodization = 0.3
        factors = {
            "goal": 1.0 if inp.fitness_focus in t.goals else 0.0,
            "experience": 1.0 if inp.experience_level in t.experience_levels else 0.3,
            "days": _range_fit(inp.days_per_week, t.days_per_week_min, t.days_per_week_max),
            "duration": _range_fit(inp.session_duration_min, t.session_duration_min, t.session_duration_max),
            "movement_preference": movement_preference,
            "focus_complement": focus_complement,
            "periodization": periodization,
        }
        score = scorer.score(factors)
        matches.append(TemplateMatch(t.id, t.slug, t.name, round(score * 100), factors))
        logger.debug(f"Template {t.slug}: score={round(score * 100)}, feasible={is_feasible}, factors={factors}")
    matches.sort(key=lambda m: m.fit_pct, reverse=True)
    top_3 = matches[:3]
    logger.info(f"Top 3 matches: {[(m.slug, m.fit_pct) for m in top_3]}")
    return top_3
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker-compose exec backend pytest tests/test_matching.py -v`
Expected: PASS (all 4 tests: 2 pre-existing + 2 new)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/program/matching.py backend/tests/test_matching.py
git commit -m "feat(program-engine): weighted template matching with movement/focus/periodization factors"
```

---

### Task 9: Wire the new matching factors into the `/programs/match` endpoint

**Files:**
- Modify: `backend/app/api/v1/endpoints/programs.py`
- Test: `backend/tests/test_programs_flow.py`

**Interfaces:**
- Consumes: `MatchRequest.movement_preferences`/`complementary_focus`/`progression_style` (Task 2), `rank_templates(..., definitions=..., all_exercises=...)` (Task 8).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_programs_flow.py — add this test; check the existing file first for
# the exact authenticated_client + environment fixture pattern already used by other tests there,
# and mirror it (this file already has a working /programs/match request in it).
@pytest.mark.asyncio
async def test_match_returns_new_factor_keys(authenticated_client, user_environment):
    resp = await authenticated_client.post(
        "/api/v1/programs/match",
        json={
            "environment_id": user_environment.id,
            "days_per_week": 3,
            "session_duration_min": 60,
            "fitness_focus": "strength",
            "movement_preferences": {"kettlebell": 1.5},
            "complementary_focus": True,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body
    assert "movement_preference" in body[0]["factors"]
    assert "focus_complement" in body[0]["factors"]
    assert "periodization" in body[0]["factors"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker-compose exec backend pytest tests/test_programs_flow.py -v -k new_factor_keys`
Expected: FAIL — `KeyError: 'movement_preference'` (endpoint doesn't pass `definitions`/`all_exercises` to `rank_templates` yet)

- [ ] **Step 3: Write the implementation**

```python
# backend/app/api/v1/endpoints/programs.py — replace the body of match()
@router.post("/match", response_model=list[TemplateMatchOut])
async def match(
    data: MatchRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[TemplateMatchOut]:
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
        feasibility[t.id] = template_is_feasible(
            cast(list[object], d.split.sessions), exercises, environment.equipment_tags
        )
    profile = user.profile
    inp = MatchInput(
        data.fitness_focus,
        profile.experience_level.value if profile and profile.experience_level else "beginner",
        data.days_per_week,
        data.session_duration_min,
        list(environment.equipment_tags),
        movement_preferences=data.movement_preferences,
        complementary_focus=data.complementary_focus,
        progression_style=data.progression_style.value,
    )
    ranked = rank_templates(templates, inp, feasibility, definitions=definitions, all_exercises=exercises)
    return [
        TemplateMatchOut(
            **m.__dict__,
            required_inputs=[r.model_dump() for r in definitions[m.template_id].required_inputs],
        )
        for m in ranked
    ]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker-compose exec backend pytest tests/test_programs_flow.py -v`
Expected: PASS (all tests, including all pre-existing ones)

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/v1/endpoints/programs.py backend/tests/test_programs_flow.py
git commit -m "feat(program-engine): wire movement/complementary/periodization signals into /programs/match"
```

---

## Phase 5 — Week-to-week variety

### Task 10: `variety.py` — rotation pool sizing

**Files:**
- Create: `backend/app/services/program/variety.py`
- Test: `backend/tests/test_variety.py`

**Interfaces:**
- Produces: `pool_size_for(variety_preference: str) -> int` (`low`→1, `medium`→2, `high`→3, unknown→1), `rotation_pool_ids(ranked: list, n: int) -> list[int]`.
- Consumes: nothing new (works on any object with an `.id` attribute, e.g. `Exercise`).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_variety.py
from app.services.program.variety import pool_size_for, rotation_pool_ids


class _Ex:
    def __init__(self, id):
        self.id = id


def test_pool_size_for_each_variety_level():
    assert pool_size_for("low") == 1
    assert pool_size_for("medium") == 2
    assert pool_size_for("high") == 3


def test_pool_size_defaults_to_one_for_unknown_level():
    assert pool_size_for("bogus") == 1


def test_rotation_pool_ids_takes_top_n():
    ranked = [_Ex(1), _Ex(2), _Ex(3), _Ex(4)]
    assert rotation_pool_ids(ranked, 2) == [1, 2]


def test_rotation_pool_ids_handles_pool_smaller_than_n():
    ranked = [_Ex(1)]
    assert rotation_pool_ids(ranked, 3) == [1]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker-compose exec backend pytest tests/test_variety.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.program.variety'`

- [ ] **Step 3: Write the implementation**

```python
# backend/app/services/program/variety.py
from typing import Any

VARIETY_POOL_SIZE: dict[str, int] = {"low": 1, "medium": 2, "high": 3}


def pool_size_for(variety_preference: str) -> int:
    return VARIETY_POOL_SIZE.get(variety_preference, 1)


def rotation_pool_ids(ranked: list[Any], n: int) -> list[int]:
    return [ex.id for ex in ranked[:n]]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker-compose exec backend pytest tests/test_variety.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/program/variety.py backend/tests/test_variety.py
git commit -m "feat(program-engine): add variety-level rotation pool sizing"
```

---

### Task 11: `build_draft` populates `rotation_pool` per slot

**Files:**
- Modify: `backend/app/services/program/drafting.py`
- Modify: `backend/app/api/v1/endpoints/programs.py`
- Modify: `backend/app/schemas/program_api.py` (no change needed — `variety_preference` already added in Task 2)
- Test: `backend/tests/test_drafting.py`

**Interfaces:**
- Consumes: `ranked_pool_for_slot` (Task 4), `pool_size_for`/`rotation_pool_ids` (Task 10).
- Produces: `build_draft(..., variety_preference: str = "low")`, `WorkoutExercise.rotation_pool` populated for non-primary slots; primary slots always get a single-entry pool (never rotate).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_drafting.py — add these tests
@pytest.mark.asyncio
async def test_build_draft_primary_slots_never_get_a_rotating_pool(sample_template_orm, sample_exercises):
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(
        equipment=["barbell", "bench", "squat_rack"], experience="intermediate", injuries=[], used_movement_slugs=set(),
    )
    program = build_draft(
        sample_template_orm, definition, ctx, sample_exercises,
        user_id=1, environment_id=1, days_per_week=3, duration_weeks=8, weight_unit="kg",
        required_inputs={"squat_start": 80, "bench_start": 60},
        variety_preference="high",
    )
    main_scheme_exercises = [ex for w in program.workouts for ex in w.exercises if ex.scheme_key == "main"]
    assert main_scheme_exercises
    assert all(len(ex.rotation_pool) == 1 for ex in main_scheme_exercises)
    assert all(ex.rotation_pool == [ex.exercise_id] for ex in main_scheme_exercises)


@pytest.mark.asyncio
async def test_build_draft_accessory_slots_get_rotation_pool_sized_by_variety(sample_template_orm, sample_exercises):
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(
        equipment=["barbell", "bench", "squat_rack"], experience="intermediate", injuries=[], used_movement_slugs=set(),
    )
    program = build_draft(
        sample_template_orm, definition, ctx, sample_exercises,
        user_id=1, environment_id=1, days_per_week=3, duration_weeks=8, weight_unit="kg",
        required_inputs={"squat_start": 80, "bench_start": 60},
        variety_preference="high",
    )
    accessory_exercises = [ex for w in program.workouts for ex in w.exercises if ex.scheme_key != "main"]
    assert accessory_exercises
    assert all(1 <= len(ex.rotation_pool) <= 3 for ex in accessory_exercises)


@pytest.mark.asyncio
async def test_build_draft_defaults_variety_preference_to_low(sample_template_orm, sample_exercises):
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(
        equipment=["barbell", "bench", "squat_rack"], experience="intermediate", injuries=[], used_movement_slugs=set(),
    )
    program = build_draft(
        sample_template_orm, definition, ctx, sample_exercises,
        user_id=1, environment_id=1, days_per_week=3, duration_weeks=8, weight_unit="kg",
        required_inputs={"squat_start": 80, "bench_start": 60},
    )
    assert program.constraints["variety_preference"] == "low"
    assert all(len(ex.rotation_pool) == 1 for w in program.workouts for ex in w.exercises)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker-compose exec backend pytest tests/test_drafting.py -v -k rotation_pool`
Expected: FAIL — `AttributeError`/`KeyError` (rotation_pool not populated, variety_preference not in constraints)

- [ ] **Step 3: Write the implementation**

```python
# backend/app/services/program/drafting.py — full new file content
from app.models import Exercise, ProgramStatus, ProgramTemplate, Workout, WorkoutExercise, WorkoutProgram
from app.schemas.program import EffortMethod
from app.schemas.template import SchemeDef, SlotRule, TemplateDefinition
from app.services.program.selection import SelectionContext, ranked_pool_for_slot
from app.services.program.variety import pool_size_for, rotation_pool_ids


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
    variety_preference: str = "low",
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
            "movement_preferences": ctx.movement_preferences,
            "complementary_focus": ctx.complementary_focus,
            "variety_preference": variety_preference,
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
            ranked = ranked_pool_for_slot(exercises, rule, ctx, set())
            chosen = ranked[0] if ranked else None
            if chosen is None:
                continue
            ctx.used_movement_slugs.add(chosen.movement_slug)
            ctx.used_unilateral_flags.append(chosen.is_unilateral)
            for muscle in chosen.primary_muscles:
                ctx.muscle_coverage[muscle] += 1
            n = 1 if rule.priority == "primary" else pool_size_for(variety_preference)
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
                    rotation_pool=rotation_pool_ids(ranked, n),
                )
            )
        program.workouts.append(workout)
    return program
```

```python
# backend/app/api/v1/endpoints/programs.py — in draft(), pass variety_preference through
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
        variety_preference=data.variety_preference.value,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker-compose exec backend pytest tests/test_drafting.py tests/test_programs_flow.py -v`
Expected: PASS (all tests, including all pre-existing ones)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/program/drafting.py backend/app/api/v1/endpoints/programs.py backend/tests/test_drafting.py
git commit -m "feat(program-engine): populate rotation_pool at draft time by variety preference"
```

---

### Task 12: `derive_week` applies rotation; surface `rotation_pool` in preview

**Files:**
- Modify: `backend/app/services/program/preview.py`
- Test: `backend/tests/test_preview.py`

**Interfaces:**
- Produces: `derive_week(...)` output's per-slot dict gains `"rotation_pool"` (the stored pool) and `"exercise_id"`/`"exercise_name"` now reflect the week's **resolved** rotated exercise, not always the stored `exercise_id`.

**Context:** `SlotPreviewOut.rotation_pool` was already added to the schema in Task 2. Rotation is a pure function of the week index: `rotation_pool[(week - 1) % len(pool)]` when `len(pool) > 1`, else the stored `exercise_id` — today's exact behavior, since every existing `WorkoutExercise` has `rotation_pool == []` (Task 3's default) or a single-entry pool (Task 11, when `variety_preference="low"`).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_preview.py — add this test
@pytest.mark.asyncio
async def test_derive_week_rotates_through_pool_by_week_index(sample_template_orm, sample_exercises):
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(["barbell", "bench", "squat_rack"], "intermediate", [], set())
    program = build_draft(
        sample_template_orm, definition, ctx, sample_exercises,
        user_id=1, environment_id=1, days_per_week=3, duration_weeks=8, weight_unit="kg",
        required_inputs={"squat_start": 80}, variety_preference="high",
    )
    global_id = 0
    for w in program.workouts:
        w.id = w.order
        for ex in w.exercises:
            global_id += 1
            ex.id = global_id
    exercise_map = {e.id: e for e in sample_exercises}
    # find a slot with a rotation pool of more than one entry
    rotating = next(
        (ex for w in program.workouts for ex in w.exercises if len(ex.rotation_pool) > 1), None
    )
    assert rotating is not None, "expected at least one accessory slot with a rotation pool > 1 at 'high' variety"
    week1 = derive_week(program, definition, 1, exercise_map)
    week2 = derive_week(program, definition, len(rotating.rotation_pool) + 1, exercise_map)
    slot1 = next(s for d in week1 for s in d["slots"] if s["workout_exercise_id"] == rotating.id)
    slot2 = next(s for d in week2 for s in d["slots"] if s["workout_exercise_id"] == rotating.id)
    assert slot1["exercise_id"] == rotating.rotation_pool[0]
    assert slot2["exercise_id"] == rotating.rotation_pool[0]  # cycles back after a full period
    assert slot1["rotation_pool"] == rotating.rotation_pool
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker-compose exec backend pytest tests/test_preview.py -v -k rotates_through_pool`
Expected: FAIL — `KeyError: 'rotation_pool'`

- [ ] **Step 3: Write the implementation**

```python
# backend/app/services/program/preview.py — full new file content
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


def _resolved_exercise_id(ex: Any, week: int) -> int:
    if ex.rotation_pool and len(ex.rotation_pool) > 1:
        return ex.rotation_pool[(week - 1) % len(ex.rotation_pool)]
    return ex.exercise_id


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
            resolved_exercise_id = _resolved_exercise_id(ex, week)
            exercise = exercise_map.get(resolved_exercise_id)
            exercise_name = exercise.name if exercise else f"Exercise #{resolved_exercise_id}"
            slots.append(
                {
                    "workout_exercise_id": ex.id,
                    "exercise_id": resolved_exercise_id,
                    "exercise_name": exercise_name,
                    "sets": scheme.sets,
                    "reps": scheme.reps,
                    "load": scheme.load,
                    "rest_seconds": scheme.rest_seconds,
                    "note": scheme.note,
                    "is_locked": ex.is_locked,
                    "is_user_swapped": ex.is_user_swapped,
                    "effort_target": _effort_target(scheme, ex.target_rpe, ex.intensity_pct, effort_method),
                    "rotation_pool": ex.rotation_pool,
                }
            )
        days.append({"workout_id": workout.id, "key": workout.key, "name": workout.name, "slots": slots})
    return days
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker-compose exec backend pytest tests/test_preview.py -v`
Expected: PASS (all tests, including all pre-existing ones)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/program/preview.py backend/tests/test_preview.py
git commit -m "feat(program-engine): apply week-to-week rotation pools in derive_week"
```

---

## Phase 6 — Frontend + docs

### Task 13: Collect movement preferences, complementary focus, and variety in the creation wizard

**Files:**
- Modify: `frontend/src/types/programCreation.ts`
- Modify: `frontend/src/types/program.ts`
- Modify: `frontend/src/components/ProgramCreationForm.tsx`
- Modify: `frontend/src/pages/ProgramBuilderPage.tsx`
- Test: `frontend/src/tests/components/ProgramCreationForm.test.tsx`

**Interfaces:**
- Produces: `EquipmentFamily` type + `EQUIPMENT_FAMILY_OPTIONS`, `VarietyPreference` type + `VARIETY_PREFERENCE_OPTIONS` in `types/programCreation.ts`. `MatchRequest` (both `programCreation.ts`'s wizard-facing shape and `program.ts`'s API-facing shape) gain `movement_preferences: Partial<Record<EquipmentFamily, number>>`, `complementary_focus: boolean`, `variety_preference: VarietyPreference`.

**Context:** `TemplateMatchCard.tsx` already renders `Object.entries(match.factors)` generically (verified: no hardcoded factor-key list), so Phase 4's three new backend factors (`movement_preference`, `focus_complement`, `periodization`) show up in the "why this fits" UI automatically — **no frontend change needed there**.

- [ ] **Step 1: Write the failing test**

```typescript
// frontend/src/tests/components/ProgramCreationForm.test.tsx — add this test
it('should include movement preferences, complementary focus, and variety in submitted values', async () => {
  const onSubmit = vi.fn();
  const onCancel = vi.fn();

  render(<ProgramCreationForm environmentId={1} onSubmit={onSubmit} onCancel={onCancel} />);

  fireEvent.click(screen.getByRole('button', { name: /Next/i }));

  await waitFor(() => {
    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        movement_preferences: {},
        complementary_focus: true,
        variety_preference: 'low',
      }),
    );
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker-compose exec frontend npx vitest run src/tests/components/ProgramCreationForm.test.tsx`
Expected: FAIL — `onSubmit` called without `movement_preferences`/`complementary_focus`/`variety_preference` keys

- [ ] **Step 3: Write the implementation**

```typescript
// frontend/src/types/programCreation.ts — add these exports (keep everything else in the file)
export type EquipmentFamily =
  'barbell' | 'dumbbell' | 'kettlebell' | 'machine' | 'cable' | 'bodyweight' | 'bands';

export const EQUIPMENT_FAMILY_OPTIONS: { value: EquipmentFamily; label: string }[] = [
  { value: 'barbell', label: 'Barbell' },
  { value: 'dumbbell', label: 'Dumbbell' },
  { value: 'kettlebell', label: 'Kettlebell' },
  { value: 'machine', label: 'Machines' },
  { value: 'cable', label: 'Cable' },
  { value: 'bodyweight', label: 'Bodyweight' },
  { value: 'bands', label: 'Resistance Bands' },
];

export type VarietyPreference = 'low' | 'medium' | 'high';

export const VARIETY_PREFERENCE_OPTIONS: { value: VarietyPreference; label: string }[] = [
  { value: 'low', label: 'Low — same accessories every week' },
  { value: 'medium', label: 'Medium — some rotation' },
  { value: 'high', label: 'High — more variety week to week' },
];
```

```typescript
// frontend/src/types/programCreation.ts — extend ProgramCreationPayload and MatchRequest
export interface ProgramCreationPayload {
  environment_id: number;
  days_per_week: number;
  preferred_days: DayOfWeek[];
  session_duration_min: number;
  start_date: string;
  focus_areas: FocusArea[];
  weight_unit: WeightUnit;
  available_weight_increments: number[];
  progression_style: ProgressionStyle;
  movement_preferences: Partial<Record<EquipmentFamily, number>>;
  complementary_focus: boolean;
  variety_preference: VarietyPreference;
}

export interface MatchRequest {
  environment_id: number;
  days_per_week: number;
  session_duration_min: number;
  weight_unit: WeightUnit;
  progression_style: ProgressionStyle;
  effort_method: EffortMethod | '';
  movement_preferences: Partial<Record<EquipmentFamily, number>>;
  complementary_focus: boolean;
  variety_preference: VarietyPreference;
}
```

```typescript
// frontend/src/types/program.ts — extend MatchRequest/DraftRequest (top of file, keep the rest)
import type { ProgressionStyle, EffortMethod, EquipmentFamily, VarietyPreference } from '@/types/programCreation';

// ... existing interfaces unchanged until MatchRequest ...

export interface MatchRequest {
  environment_id: number;
  days_per_week: number;
  session_duration_min: number;
  fitness_focus: string;
  weight_unit: string;
  duration_weeks: number;
  movement_preferences: Partial<Record<EquipmentFamily, number>>;
  complementary_focus: boolean;
  variety_preference: VarietyPreference;
}

export interface DraftRequest extends MatchRequest {
  template_id: number;
  required_inputs: Record<string, number | string>;
  progression_style: ProgressionStyle;
  effort_method: EffortMethod | null;
}
```

```typescript
// frontend/src/components/ProgramCreationForm.tsx — full new file content
import { useState, useEffect } from 'react';
import { Button } from './Button';
import { FormField } from './FormField';
import {
  WEIGHT_UNIT_OPTIONS,
  PROGRESSION_STYLE_OPTIONS,
  EFFORT_METHOD_OPTIONS,
  EQUIPMENT_FAMILY_OPTIONS,
  VARIETY_PREFERENCE_OPTIONS,
} from '@/types/programCreation';
import type {
  MatchRequest,
  WeightUnit,
  ProgressionStyle,
  EffortMethod,
  EquipmentFamily,
  VarietyPreference,
} from '@/types/programCreation';

interface ProgramCreationFormProps {
  environmentId: number;
  onSubmit: (values: MatchRequest) => void;
  onCancel: () => void;
  initialValues?: MatchRequest;
}

export function ProgramCreationForm({
  environmentId,
  onSubmit,
  onCancel,
  initialValues,
}: ProgramCreationFormProps) {
  const [daysPerWeek, setDaysPerWeek] = useState(initialValues?.days_per_week.toString() ?? '3');
  const [sessionDurationMin, setSessionDurationMin] = useState(
    initialValues?.session_duration_min.toString() ?? '60',
  );
  const [weightUnit, setWeightUnit] = useState<WeightUnit>(initialValues?.weight_unit ?? 'kg');
  const [progressionStyle, setProgressionStyle] = useState<ProgressionStyle>(
    initialValues?.progression_style ?? 'consistent',
  );
  const [effortMethod, setEffortMethod] = useState<EffortMethod | ''>(
    initialValues?.effort_method ?? '',
  );
  const [movementPreferences, setMovementPreferences] = useState<
    Partial<Record<EquipmentFamily, number>>
  >(initialValues?.movement_preferences ?? {});
  const [complementaryFocus, setComplementaryFocus] = useState(
    initialValues?.complementary_focus ?? true,
  );
  const [varietyPreference, setVarietyPreference] = useState<VarietyPreference>(
    initialValues?.variety_preference ?? 'low',
  );

  useEffect(() => {
    if (initialValues) {
      setDaysPerWeek(initialValues.days_per_week.toString());
      setSessionDurationMin(initialValues.session_duration_min.toString());
      setWeightUnit(initialValues.weight_unit);
      setProgressionStyle(initialValues.progression_style);
      setEffortMethod(initialValues.effort_method);
      setMovementPreferences(initialValues.movement_preferences);
      setComplementaryFocus(initialValues.complementary_focus);
      setVarietyPreference(initialValues.variety_preference);
    }
  }, [initialValues]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      environment_id: environmentId,
      days_per_week: parseInt(daysPerWeek, 10),
      session_duration_min: parseInt(sessionDurationMin, 10),
      weight_unit: weightUnit,
      progression_style: progressionStyle,
      effort_method: effortMethod,
      movement_preferences: movementPreferences,
      complementary_focus: complementaryFocus,
      variety_preference: varietyPreference,
    });
  };

  const setFamilyWeight = (family: EquipmentFamily, value: string) => {
    setMovementPreferences((prev) => ({ ...prev, [family]: parseFloat(value) }));
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-50">
        Generate a Program
      </h3>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <FormField
          label="Days per Week"
          type="number"
          name="days_per_week"
          value={daysPerWeek}
          onChange={(e) => setDaysPerWeek(e.target.value)}
          min="1"
          max="7"
          required
        />
        <FormField
          label="Session Duration (minutes)"
          type="number"
          name="session_duration_min"
          value={sessionDurationMin}
          onChange={(e) => setSessionDurationMin(e.target.value)}
          min="15"
          max="300"
          step="15"
          required
        />
        <div className="input-group">
          <label htmlFor="weight_unit" className="input-label">
            Weight Unit <span className="text-error-600">*</span>
          </label>
          <select
            id="weight_unit"
            name="weight_unit"
            value={weightUnit}
            onChange={(e) => setWeightUnit(e.target.value as WeightUnit)}
            required
          >
            {WEIGHT_UNIT_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
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
        <div className="input-group">
          <label htmlFor="variety_preference" className="input-label">
            Weekly Variety
          </label>
          <select
            id="variety_preference"
            name="variety_preference"
            value={varietyPreference}
            onChange={(e) => setVarietyPreference(e.target.value as VarietyPreference)}
          >
            {VARIETY_PREFERENCE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="input-group">
        <label className="input-label flex items-center gap-2">
          <input
            type="checkbox"
            checked={complementaryFocus}
            onChange={(e) => setComplementaryFocus(e.target.checked)}
          />
          Balance my focus with complementary + core work
        </label>
      </div>

      <div>
        <p className="input-label mb-2">Equipment Preferences (0 = avoid, 1 = neutral, 2 = prefer)</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {EQUIPMENT_FAMILY_OPTIONS.map((option) => (
            <div key={option.value} className="input-group">
              <label htmlFor={`pref_${option.value}`} className="input-label">
                {option.label}
              </label>
              <input
                id={`pref_${option.value}`}
                type="range"
                min="0"
                max="2"
                step="0.25"
                value={movementPreferences[option.value] ?? 1}
                onChange={(e) => setFamilyWeight(option.value, e.target.value)}
              />
            </div>
          ))}
        </div>
      </div>

      <div className="mt-6 flex gap-3 justify-between">
        <Button type="button" variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" variant="primary">
          Next
        </Button>
      </div>
    </form>
  );
}
```

```typescript
// frontend/src/pages/ProgramBuilderPage.tsx — in onPrefs(), carry the three new fields through
  const onPrefs = (values: FormMatchRequest) => {
    const matchRequest: MatchRequest = {
      environment_id: values.environment_id,
      days_per_week: values.days_per_week,
      session_duration_min: values.session_duration_min,
      weight_unit: values.weight_unit,
      fitness_focus: 'full_body',
      duration_weeks: 8,
      movement_preferences: values.movement_preferences,
      complementary_focus: values.complementary_focus,
      variety_preference: values.variety_preference,
    };
    setPrefs(matchRequest);
    setProgressionStyle(values.progression_style);
    setEffortMethod(values.effort_method || null);
    match.mutate(matchRequest, { onSuccess: () => setStep(1) });
  };
```

Also update the `initialValues` object passed to `<ProgramCreationForm>` in the same file (step 0 render block) to include the three new fields read back from `prefs`:

```typescript
          initialValues={
            prefs
              ? {
                  environment_id: prefs.environment_id,
                  days_per_week: prefs.days_per_week,
                  session_duration_min: prefs.session_duration_min,
                  weight_unit: prefs.weight_unit as WeightUnit,
                  progression_style: progressionStyle,
                  effort_method: effortMethod ?? '',
                  movement_preferences: prefs.movement_preferences,
                  complementary_focus: prefs.complementary_focus,
                  variety_preference: prefs.variety_preference,
                }
              : undefined
          }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker-compose exec frontend npx vitest run src/tests/components/ProgramCreationForm.test.tsx`
Expected: PASS (all tests, including all pre-existing ones)

Then: `docker-compose exec frontend npm run type-check`
Expected: no errors

- [ ] **Step 5: Commit**

```bash
git add frontend/src/types/programCreation.ts frontend/src/types/program.ts frontend/src/components/ProgramCreationForm.tsx frontend/src/pages/ProgramBuilderPage.tsx frontend/src/tests/components/ProgramCreationForm.test.tsx
git commit -m "feat(program-ui): collect movement preferences, complementary focus, and variety in wizard"
```

---

### Task 14: Show a rotation indicator on slots that vary week to week

**Files:**
- Modify: `frontend/src/types/program.ts`
- Modify: `frontend/src/components/SlotRow.tsx`
- Test: `frontend/src/tests/components/SlotRow.test.tsx`

**Interfaces:**
- Produces: `SlotPreview.rotation_pool: number[]` type field; `SlotRow` renders a small "🔁 rotates weekly" badge when `slot.rotation_pool.length > 1`.

- [ ] **Step 1: Write the failing test**

```typescript
// frontend/src/tests/components/SlotRow.test.tsx — add this test; update baseSlot to include
// rotation_pool: [] (required field, so the existing baseSlot object literal must gain this key
// or every existing test will fail to type-check — add it once at the top of the file)
it('shows a rotation badge when the slot has more than one exercise in its pool', () => {
  const slot = { ...baseSlot, rotation_pool: [1, 2, 3] };
  render(<SlotRow slot={slot} onAction={vi.fn()} onSwap={vi.fn()} />);
  expect(screen.getByText(/rotates weekly/i)).toBeInTheDocument();
});

it('does not show a rotation badge for a single-exercise pool', () => {
  const slot = { ...baseSlot, rotation_pool: [1] };
  render(<SlotRow slot={slot} onAction={vi.fn()} onSwap={vi.fn()} />);
  expect(screen.queryByText(/rotates weekly/i)).not.toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker-compose exec frontend npx vitest run src/tests/components/SlotRow.test.tsx`
Expected: FAIL — type error (`rotation_pool` missing on `SlotPreview`) / badge text not found

- [ ] **Step 3: Write the implementation**

```typescript
// frontend/src/types/program.ts — add to SlotPreview
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
  rotation_pool: number[];
}
```

```typescript
// frontend/src/tests/components/SlotRow.test.tsx — add rotation_pool to the existing baseSlot fixture
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
  rotation_pool: [1],
};
```

```typescript
// frontend/src/components/SlotRow.tsx — full new file content
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
  readOnly = false,
}: {
  slot: SlotPreview;
  onAction?: (a: FeedbackAction) => void;
  onSwap?: () => void;
  readOnly?: boolean;
}) {
  const effortLabel = formatEffortTarget(slot.effort_target);
  const rotates = slot.rotation_pool.length > 1;
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
        {rotates && (
          <span aria-label="rotates weekly" className="text-xs text-purple-600">
            🔁 rotates weekly
          </span>
        )}
      </div>
      <div className="flex items-center gap-3 text-sm text-gray-700">
        <span>
          {slot.sets} × {slot.reps}
          {slot.load != null ? ` @ ${slot.load}` : ''}
        </span>
        {effortLabel && <span className="text-xs text-neutral-500">{effortLabel}</span>}
        {slot.note && <span className="text-amber-600">{slot.note}</span>}
        {!readOnly && onAction && onSwap && (
          <SlotFeedbackMenu slot={slot} onAction={onAction} onSwap={onSwap} />
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `docker-compose exec frontend npx vitest run src/tests/components/SlotRow.test.tsx`
Expected: PASS (all tests, including all pre-existing ones)

Then: `docker-compose exec frontend npm run type-check`
Expected: no errors

- [ ] **Step 5: Commit**

```bash
git add frontend/src/types/program.ts frontend/src/components/SlotRow.tsx frontend/src/tests/components/SlotRow.test.tsx
git commit -m "feat(program-ui): show a rotation badge on slots with more than one exercise in their pool"
```

---

### Task 15: Update docs — user guide + technical reference

**Files:**
- Modify: `docs/user/PROGRAM_BUILDER.html`
- Modify: `docs/technical/PROGRAM_GENERATION_TECHNICAL.html`

**Interfaces:**
- Produces: no code interfaces — this is documentation content only, following `.claude/skills/documentation/SKILL.md`'s existing navy (user) / blue (technical) theme conventions already used by these two files.

**Context:** Per the confirmed decision at the top of this plan, this task extends the two docs that already cover program generation rather than creating the spec's literally-named new files, to avoid two overlapping docs for the same feature. Read both files first to match their existing heading structure, CSS classes, and tone before adding sections.

- [ ] **Step 1: Read the existing docs to match their structure**

Read `docs/user/PROGRAM_BUILDER.html` and `docs/technical/PROGRAM_GENERATION_TECHNICAL.html` in full. Note the existing `<h2>` section order, the CSS classes in use (`.step`, `.faq-item`, `.tip`, `.endpoint`, `.code-block`, `.diagram`, `.troubleshooting-item`), and the nav anchor list in the technical doc's `<nav>` — new sections must slot into both without breaking the existing anchors.

- [ ] **Step 2: Add a new user-facing section to `docs/user/PROGRAM_BUILDER.html`**

Add a new `<h2>` section (placed after the existing template-selection walkthrough, before "Troubleshooting") titled something like "Fine-Tuning Your Program", written in the second-person, non-technical, analogy-driven style the skill requires (e.g. "we favor your preferred equipment but still mix in what balances your body"). Cover, in plain language and with no formulas:
- What picking equipment preferences does (biases exercise choice, never removes an option entirely).
- What "balance my focus with complementary work" does (fills non-focus slots with the muscles your session hasn't hit yet, instead of five variations of the same lift).
- What the weekly variety setting does (how many different exercises rotate through an accessory slot across the weeks of the program) — and mention the new "🔁 rotates weekly" badge they'll see in their program preview.
Add one `.faq-item` covering "Why did I get a barbell exercise when I said I prefer kettlebells?" (soft preference, not a filter — equipment feasibility and injury safety always come first).

- [ ] **Step 3: Add a new technical section to `docs/technical/PROGRAM_GENERATION_TECHNICAL.html`**

Add a new `<h2 id="scoring-depth">` section (and a matching `<nav>` anchor) rendering spec §14 verbatim in the doc's existing `.diagram`/`.code-block`/table styling:
- The end-to-end pipeline diagram (§14.1).
- The feasibility-gate and match-score formulas with the factor table, including the three new factors and their weights (§14.2).
- The selection filters → weighted-score diagram and feature table, including the two new features (§14.3).
- The rotation formula (§14.4).
- File-path references: `matching.py`, `selection.py`, `complementation.py`, `preferences.py`, `variety.py`, `preview.py` (all under `backend/app/services/program/`).
- The `TemplateScorer`/`ExerciseScorer` protocol seam table from spec §9, framed as "what would change if a learned model replaced the heuristic."
Update `docs/technical/index.html`'s quick-link card and `docs/README.md` if that file references program-generation docs, per the documentation skill's checklist.

- [ ] **Step 4: Verify links and rendering**

Run: `grep -r 'href="' docs/user/PROGRAM_BUILDER.html docs/technical/PROGRAM_GENERATION_TECHNICAL.html`
Expected: all internal links resolve to existing files (no broken anchors)

Open both files in a browser (`open docs/user/PROGRAM_BUILDER.html`, `open docs/technical/PROGRAM_GENERATION_TECHNICAL.html`) and visually confirm the new sections render with the existing theme (navy/slate for user, blue for technical), are responsive, and the technical doc's nav scrolls to the new anchor.

- [ ] **Step 5: Commit**

```bash
git add docs/user/PROGRAM_BUILDER.html docs/technical/PROGRAM_GENERATION_TECHNICAL.html docs/technical/index.html docs/README.md
git commit -m "docs(program-engine): document movement preferences, complementary focus, and variety"
```

---

## Self-Review Notes

- **Spec coverage:** §3/§4 → Task 1–2; §5 (weighted selection + movement preference) → Task 4–5; §6 (complementation) → Task 6–7; §7 (matching depth) → Task 8–9; §8 (variety) → Task 10–12; §10 (migrations) → Task 3; §11 (endpoint wiring) → threaded through Tasks 5/7/9/11; §12 (phasing) → this plan's phase structure; §13 (performance) → no new DB/network calls added per candidate, stays in-memory; §14 (algorithm reference) → implemented verbatim in Tasks 4/6/8/10/12; §15 (docs) → Task 15 (with the confirmed in-place-update deviation noted at the top).
- **Type consistency checked:** `SelectionContext` fields introduced in Task 4 (`movement_preferences`, `muscle_coverage`, `complementary_focus`, `weights`) are the exact set consumed in Tasks 5/7/11; `ranked_pool_for_slot` (Task 4) is the exact name consumed by Task 11's `build_draft`; `MatchInput`'s three new fields (Task 8) are the exact names populated in Task 9's endpoint; `pool_size_for`/`rotation_pool_ids` (Task 10) are the exact names consumed in Task 11; `rotation_pool` (Task 3's column, Task 2's schema field) is the exact name read in Task 12's `derive_week` and Task 14's `SlotRow`.
- **No placeholders:** every step above contains runnable code, not a description of code.
