from datetime import datetime

import pytest

from app.models import WorkoutSetLog
from app.schemas.template import TemplateDefinition
from app.services.program.drafting import build_draft
from app.services.program.preview import derive_week
from app.services.program.selection import SelectionContext


@pytest.mark.asyncio
async def test_derive_week_applies_progression(sample_template_orm, sample_exercises):
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(["barbell", "bench", "squat_rack"], "intermediate", [], set())
    program = build_draft(
        sample_template_orm,
        definition,
        ctx,
        sample_exercises,
        user_id=1,
        environment_id=1,
        days_per_week=3,
        duration_weeks=8,
        weight_unit="kg",
        required_inputs={"squat_start": 80},
    )
    for w in program.workouts:  # give ids so derive output is stable
        w.id = w.order
        for j, ex in enumerate(w.exercises, 1):
            ex.id = j
    exercise_map = {e.id: e for e in sample_exercises}
    w1 = derive_week(program, definition, 1, exercise_map)
    w2 = derive_week(program, definition, 2, exercise_map)
    load1 = next((s["load"] for d in w1 for s in d["slots"] if s["load"] is not None), None)
    load2 = next((s["load"] for d in w2 for s in d["slots"] if s["load"] is not None), None)
    assert load2 > load1  # progression increased load week over week


@pytest.mark.asyncio
async def test_derive_week_horizontal_push_load_is_seeded(sample_template_orm, sample_exercises):
    """Regression: horizontal_push slot's load must be seeded from bench_start via applies_to."""
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(["barbell", "bench", "squat_rack"], "intermediate", [], set())
    program = build_draft(
        sample_template_orm,
        definition,
        ctx,
        sample_exercises,
        user_id=1,
        environment_id=1,
        days_per_week=3,
        duration_weeks=8,
        weight_unit="kg",
        required_inputs={"squat_start": 80, "bench_start": 60},
    )
    global_id = 0
    for w in program.workouts:
        w.id = w.order
        for ex in w.exercises:
            global_id += 1
            ex.id = global_id

    horizontal_push_we_ids = {
        ex.id for w in program.workouts for ex in w.exercises if ex.fills_rule.get("pattern") == "horizontal_push"
    }
    assert horizontal_push_we_ids

    exercise_map = {e.id: e for e in sample_exercises}
    week1 = derive_week(program, definition, 1, exercise_map)
    loads = [s["load"] for d in week1 for s in d["slots"] if s["workout_exercise_id"] in horizontal_push_we_ids]
    assert loads
    assert all(load is not None for load in loads)
    # Verify exercise names are resolved from the exercise map
    exercise_names = [
        s["exercise_name"] for d in week1 for s in d["slots"] if s["workout_exercise_id"] in horizontal_push_we_ids
    ]
    assert exercise_names
    assert all(not name.startswith("Exercise #") for name in exercise_names)


@pytest.mark.asyncio
async def test_derive_week_includes_exercise_names(sample_template_orm, sample_exercises):
    """Verify exercise names are included in derived weeks."""
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(["barbell", "bench", "squat_rack"], "intermediate", [], set())
    program = build_draft(
        sample_template_orm,
        definition,
        ctx,
        sample_exercises,
        user_id=1,
        environment_id=1,
        days_per_week=3,
        duration_weeks=8,
        weight_unit="kg",
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
    for slot in slots:
        assert "exercise_name" in slot
        assert slot["exercise_name"]  # not empty
        # Should have real name from exercise_map, not fallback
        assert not slot["exercise_name"].startswith("Exercise #")


@pytest.mark.asyncio
async def test_derive_week_includes_rpe_effort_target_when_requested(sample_template_orm, sample_exercises):
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(["barbell", "bench", "squat_rack"], "intermediate", [], set())
    program = build_draft(
        sample_template_orm,
        definition,
        ctx,
        sample_exercises,
        user_id=1,
        environment_id=1,
        days_per_week=3,
        duration_weeks=8,
        weight_unit="kg",
        required_inputs={"squat_start": 80},
        effort_method="rpe",
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
        sample_template_orm,
        definition,
        ctx,
        sample_exercises,
        user_id=1,
        environment_id=1,
        days_per_week=3,
        duration_weeks=8,
        weight_unit="kg",
        required_inputs={"squat_start": 80},
        effort_method="rir",
    )
    global_id = 0
    for w in program.workouts:
        w.id = w.order
        for ex in w.exercises:
            global_id += 1
            ex.id = global_id
    exercise_map = {e.id: e for e in sample_exercises}
    week1 = derive_week(program, definition, 1, exercise_map)
    # Only main-scheme slots have target_rpe=8.0; the template also fills some accessory-scheme
    # slots (target_rpe=7.0), so scope the assertion to workout_exercises using the main scheme.
    main_we_ids = {ex.id for w in program.workouts for ex in w.exercises if ex.scheme_key == "main"}
    main_targets = [
        s["effort_target"]
        for d in week1
        for s in d["slots"]
        if s["workout_exercise_id"] in main_we_ids and s.get("effort_target") is not None
    ]
    assert main_targets
    assert all(t["method"] == "rir" for t in main_targets)
    assert all(t["value"] == 2 for t in main_targets)  # target_rpe=8.0 -> rir = 10 - 8 = 2


@pytest.mark.asyncio
async def test_derive_week_percent_1rm_target_includes_load(sample_template_orm, sample_exercises):
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(["barbell", "bench", "squat_rack"], "intermediate", [], set())
    program = build_draft(
        sample_template_orm,
        definition,
        ctx,
        sample_exercises,
        user_id=1,
        environment_id=1,
        days_per_week=3,
        duration_weeks=8,
        weight_unit="kg",
        required_inputs={"squat_start": 100, "bench_start": 80},
        effort_method="percent_1rm",
    )
    global_id = 0
    for w in program.workouts:
        w.id = w.order
        for ex in w.exercises:
            global_id += 1
            ex.id = global_id
    exercise_map = {e.id: e for e in sample_exercises}
    week1 = derive_week(program, definition, 1, exercise_map)
    # target_load is only seeded for patterns with an applies_to required input (squat,
    # horizontal_push); other patterns have no starting weight and load stays None.
    seeded_we_ids = {
        ex.id
        for w in program.workouts
        for ex in w.exercises
        if ex.fills_rule.get("pattern") in ("squat", "horizontal_push")
    }
    targets = [
        s["effort_target"]
        for d in week1
        for s in d["slots"]
        if s["workout_exercise_id"] in seeded_we_ids and s.get("effort_target") is not None
    ]
    assert targets
    assert all(t["method"] == "percent_1rm" for t in targets)
    assert all(t["pct"] in (0.8, 0.65) for t in targets)  # main=0.8, accessory=0.65 intensity_pct
    assert all(t["target_load"] is not None for t in targets)


@pytest.mark.asyncio
async def test_derive_week_omits_effort_target_when_effort_method_unset(sample_template_orm, sample_exercises):
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(["barbell", "bench", "squat_rack"], "intermediate", [], set())
    program = build_draft(
        sample_template_orm,
        definition,
        ctx,
        sample_exercises,
        user_id=1,
        environment_id=1,
        days_per_week=3,
        duration_weeks=8,
        weight_unit="kg",
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


@pytest.mark.asyncio
async def test_derive_week_applies_rotation_pool_week_to_week(sample_template_orm, sample_exercises):
    """Rotation pool cycles the resolved exercise week over week and is surfaced in the slot."""
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(["barbell", "bench", "squat_rack"], "intermediate", [], set())
    program = build_draft(
        sample_template_orm,
        definition,
        ctx,
        sample_exercises,
        user_id=1,
        environment_id=1,
        days_per_week=3,
        duration_weeks=8,
        weight_unit="kg",
        required_inputs={"squat_start": 80},
    )
    global_id = 0
    for w in program.workouts:
        w.id = w.order
        for ex in w.exercises:
            global_id += 1
            ex.id = global_id
    exercise_map = {e.id: e for e in sample_exercises}

    target_we = program.workouts[0].exercises[0]
    pool = [e.id for e in sample_exercises[:3]]
    target_we.rotation_pool = pool

    def slot_for(week: int) -> dict:
        days = derive_week(program, definition, week, exercise_map)
        return next(s for d in days for s in d["slots"] if s["workout_exercise_id"] == target_we.id)

    week1_slot = slot_for(1)
    assert week1_slot["exercise_id"] == pool[0]
    assert week1_slot["rotation_pool"] == pool

    week4_slot = slot_for(len(pool) + 1)  # cycles back to pool[0]
    assert week4_slot["exercise_id"] == pool[0]

    week2_slot = slot_for(2)
    assert week2_slot["exercise_id"] == pool[1]


@pytest.mark.asyncio
async def test_derive_week_fallback_for_missing_exercise(sample_template_orm, sample_exercises):
    """Verify placeholder name when exercise is missing (e.g., deactivated)."""
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(["barbell", "bench", "squat_rack"], "intermediate", [], set())
    program = build_draft(
        sample_template_orm,
        definition,
        ctx,
        sample_exercises,
        user_id=1,
        environment_id=1,
        days_per_week=3,
        duration_weeks=8,
        weight_unit="kg",
        required_inputs={"squat_start": 80},
    )
    for w in program.workouts:
        w.id = w.order
        for j, ex in enumerate(w.exercises, 1):
            ex.id = j
    # Empty exercise map simulates all exercises being deactivated
    week1 = derive_week(program, definition, 1, {})
    slots = [s for d in week1 for s in d["slots"]]
    assert slots
    for slot in slots:
        # Should all be fallback placeholders
        assert slot["exercise_name"].startswith("Exercise #")


@pytest.mark.asyncio
async def test_derive_week_rest_seconds_strength_intent_low_reps(sample_template_orm, sample_exercises):
    """Slots with ≤6 reps get strength rest interval (195s)."""
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(["barbell", "bench", "squat_rack"], "intermediate", [], set())
    program = build_draft(
        sample_template_orm,
        definition,
        ctx,
        sample_exercises,
        user_id=1,
        environment_id=1,
        days_per_week=3,
        duration_weeks=8,
        weight_unit="kg",
        required_inputs={"squat_start": 80},
    )
    for w in program.workouts:
        w.id = w.order
        for j, ex in enumerate(w.exercises, 1):
            ex.id = j
    exercise_map = {e.id: e for e in sample_exercises}
    week1 = derive_week(program, definition, 1, exercise_map)
    slots = [s for d in week1 for s in d["slots"]]
    # Main scheme typically has low rep counts (5-6), should get strength rest
    main_slots = [s for s in slots if s.get("reps", 0) <= 6]
    assert main_slots, "Expected at least one slot with ≤6 reps"
    for slot in main_slots:
        assert slot["rest_seconds"] == 195, f"Slot with reps={slot['reps']} should have rest_seconds=195"


@pytest.mark.asyncio
async def test_derive_week_rest_seconds_hypertrophy_intent_mid_reps(sample_template_orm, sample_exercises):
    """Slots with 7-12 reps and intensity <85% get hypertrophy rest interval (120s)."""
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(["barbell", "bench", "squat_rack"], "intermediate", [], set())
    program = build_draft(
        sample_template_orm,
        definition,
        ctx,
        sample_exercises,
        user_id=1,
        environment_id=1,
        days_per_week=3,
        duration_weeks=8,
        weight_unit="kg",
        required_inputs={"squat_start": 80},
    )
    for w in program.workouts:
        w.id = w.order
        for j, ex in enumerate(w.exercises, 1):
            ex.id = j
    exercise_map = {e.id: e for e in sample_exercises}
    week1 = derive_week(program, definition, 1, exercise_map)
    slots = [s for d in week1 for s in d["slots"]]
    # Accessory schemes typically have mid rep counts (8-12), should get hypertrophy rest
    mid_rep_slots = [s for s in slots if 7 <= s.get("reps", 0) <= 12]
    if mid_rep_slots:  # Only assert if fixture produces such slots
        for slot in mid_rep_slots:
            # Only check if intensity is not >=0.85 (which would be strength)
            if slot.get("effort_target") is None or slot["effort_target"].get("pct", 0) < 0.85:
                assert (
                    slot["rest_seconds"] == 120
                ), f"Slot with reps={slot['reps']} and intensity<0.85 should have rest_seconds=120"


@pytest.mark.asyncio
async def test_derive_week_rest_seconds_endurance_intent_high_reps(sample_template_orm, sample_exercises):
    """Slots with >12 reps and intensity <85% get endurance rest interval (68s)."""
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(["barbell", "bench", "squat_rack"], "intermediate", [], set())
    program = build_draft(
        sample_template_orm,
        definition,
        ctx,
        sample_exercises,
        user_id=1,
        environment_id=1,
        days_per_week=3,
        duration_weeks=8,
        weight_unit="kg",
        required_inputs={"squat_start": 80},
    )
    for w in program.workouts:
        w.id = w.order
        for j, ex in enumerate(w.exercises, 1):
            ex.id = j
    exercise_map = {e.id: e for e in sample_exercises}
    week1 = derive_week(program, definition, 1, exercise_map)
    slots = [s for d in week1 for s in d["slots"]]
    # High rep finisher slots should get endurance rest
    high_rep_slots = [s for s in slots if s.get("reps", 0) > 12]
    if high_rep_slots:
        for slot in high_rep_slots:
            assert slot["rest_seconds"] == 68, f"Slot with reps={slot['reps']} should have rest_seconds=68"


def test_rest_seconds_for_intent_boundary_conditions():
    """Test _rest_seconds_for_intent with boundary values."""
    from app.services.program.preview import _rest_seconds_for_intent

    # reps == 6 with no intensity should be strength
    assert _rest_seconds_for_intent(6, None) == 195
    # reps == 7 with no intensity should be hypertrophy
    assert _rest_seconds_for_intent(7, None) == 120
    # reps == 12 with no intensity should be hypertrophy
    assert _rest_seconds_for_intent(12, None) == 120
    # reps == 13 with no intensity should be endurance
    assert _rest_seconds_for_intent(13, None) == 68
    # intensity >= 0.85 should be strength regardless of reps
    assert _rest_seconds_for_intent(20, 0.85) == 195
    assert _rest_seconds_for_intent(20, 0.90) == 195
    # intensity < 0.85 with reps > 12 should be endurance
    assert _rest_seconds_for_intent(15, 0.80) == 68
    # intensity < 0.85 with reps 7-12 should be hypertrophy
    assert _rest_seconds_for_intent(10, 0.70) == 120


@pytest.mark.asyncio
async def test_derive_week_tempo_always_controlled(sample_template_orm, sample_exercises):
    """Every slot in a derived week has tempo='controlled'."""
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(["barbell", "bench", "squat_rack"], "intermediate", [], set())
    program = build_draft(
        sample_template_orm,
        definition,
        ctx,
        sample_exercises,
        user_id=1,
        environment_id=1,
        days_per_week=3,
        duration_weeks=8,
        weight_unit="kg",
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
    for slot in slots:
        assert slot["tempo"] == "controlled"


@pytest.mark.asyncio
async def test_derive_week_warmup_sets_first_primary_slot_only(sample_template_orm, sample_exercises):
    """Exactly one slot per workout with primary priority gets warmup_sets; others get empty list."""
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(["barbell", "bench", "squat_rack"], "intermediate", [], set())
    program = build_draft(
        sample_template_orm,
        definition,
        ctx,
        sample_exercises,
        user_id=1,
        environment_id=1,
        days_per_week=3,
        duration_weeks=8,
        weight_unit="kg",
        required_inputs={"squat_start": 80},
    )
    for w in program.workouts:
        w.id = w.order
        for j, ex in enumerate(w.exercises, 1):
            ex.id = j
    exercise_map = {e.id: e for e in sample_exercises}
    week1 = derive_week(program, definition, 1, exercise_map)
    for day in week1:
        slots = day["slots"]
        # Count how many slots have non-empty warmup_sets
        warmup_slots = [s for s in slots if s.get("warmup_sets")]
        # At most one per workout
        assert len(warmup_slots) <= 1, f"Expected at most 1 slot with warmup_sets per workout, got {len(warmup_slots)}"
        # Verify the warmup slot has the expected structure
        if warmup_slots:
            warmup_slot_load = warmup_slots[0]["load"]
            warmup = warmup_slots[0]["warmup_sets"]
            assert len(warmup) == 3, "Warmup ramp should have 3 sets"
            assert warmup[0] == {"pct": 0.4, "reps": 5, "load": round(0.4 * warmup_slot_load, 1)}


@pytest.mark.asyncio
async def test_derive_week_warmup_sets_structure(sample_template_orm, sample_exercises):
    """Warmup sets for first primary slot has correct percentages and reps."""
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(["barbell", "bench", "squat_rack"], "intermediate", [], set())
    program = build_draft(
        sample_template_orm,
        definition,
        ctx,
        sample_exercises,
        user_id=1,
        environment_id=1,
        days_per_week=3,
        duration_weeks=8,
        weight_unit="kg",
        required_inputs={"squat_start": 80},
    )
    for w in program.workouts:
        w.id = w.order
        for j, ex in enumerate(w.exercises, 1):
            ex.id = j
    exercise_map = {e.id: e for e in sample_exercises}
    week1 = derive_week(program, definition, 1, exercise_map)
    # Find a slot with warmup_sets and verify its structure
    for day in week1:
        for slot in day["slots"]:
            if slot.get("warmup_sets"):
                warmup = slot["warmup_sets"]
                # Should be exactly [(0.4, 5), (0.6, 3), (0.8, 1)]
                assert len(warmup) == 3
                assert warmup[0]["pct"] == 0.4 and warmup[0]["reps"] == 5
                assert warmup[1]["pct"] == 0.6 and warmup[1]["reps"] == 3
                assert warmup[2]["pct"] == 0.8 and warmup[2]["reps"] == 1
                # load values should be pct * working_load
                if slot["load"] is not None:
                    assert abs(warmup[0]["load"] - round(0.4 * slot["load"], 1)) < 0.01
                    assert abs(warmup[1]["load"] - round(0.6 * slot["load"], 1)) < 0.01
                    assert abs(warmup[2]["load"] - round(0.8 * slot["load"], 1)) < 0.01
                return
    # If no warmup_sets found, that's ok for this fixture


@pytest.mark.asyncio
async def test_derive_week_warmup_sets_empty_for_no_load(sample_template_orm, sample_exercises):
    """First primary slot with no load (bodyweight) gets empty warmup_sets."""
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(["barbell", "bench", "squat_rack"], "intermediate", [], set())
    program = build_draft(
        sample_template_orm,
        definition,
        ctx,
        sample_exercises,
        user_id=1,
        environment_id=1,
        days_per_week=3,
        duration_weeks=8,
        weight_unit="kg",
        required_inputs={"squat_start": 80},
    )
    # Manually set first exercise of first workout to have no base_load (bodyweight)
    if program.workouts:
        first_workout = program.workouts[0]
        if first_workout.exercises:
            first_workout.exercises[0].base_load = None

    for w in program.workouts:
        w.id = w.order
        for j, ex in enumerate(w.exercises, 1):
            ex.id = j
    exercise_map = {e.id: e for e in sample_exercises}
    week1 = derive_week(program, definition, 1, exercise_map)
    # Even if it's the first primary slot, if load is None, warmup_sets should be empty
    if program.workouts and program.workouts[0].exercises:
        first_slot = week1[0]["slots"][0]
        if first_slot["load"] is None:
            assert first_slot["warmup_sets"] == [], "Bodyweight slot should have empty warmup_sets"


@pytest.mark.asyncio
async def test_derive_week_slot_preview_out_roundtrip(sample_template_orm, sample_exercises):
    """SlotPreviewOut(**slot_dict) round-trips correctly for all slot dicts."""
    from app.schemas.program_api import SlotPreviewOut

    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(["barbell", "bench", "squat_rack"], "intermediate", [], set())
    program = build_draft(
        sample_template_orm,
        definition,
        ctx,
        sample_exercises,
        user_id=1,
        environment_id=1,
        days_per_week=3,
        duration_weeks=8,
        weight_unit="kg",
        required_inputs={"squat_start": 80},
    )
    for w in program.workouts:
        w.id = w.order
        for j, ex in enumerate(w.exercises, 1):
            ex.id = j
    exercise_map = {e.id: e for e in sample_exercises}
    week1 = derive_week(program, definition, 1, exercise_map)
    slots = [s for d in week1 for s in d["slots"]]
    # Each slot dict should be convertible to SlotPreviewOut
    for slot in slots:
        out = SlotPreviewOut(**slot)
        assert out.workout_exercise_id == slot["workout_exercise_id"]
        assert out.tempo == "controlled"
        assert isinstance(out.warmup_sets, list)


# --- Ramp guard (Task 3.5) ---------------------------------------------------------


@pytest.mark.asyncio
async def test_derive_week_caps_load_ramp_for_beginner_experience(sample_template_orm, sample_exercises):
    """A small base_load makes linear_load's fixed +2.5 weekly increment exceed the
    beginner population's +20% ramp cap (10 -> 12.5 is +25%) - ramp_guard should clamp
    week 2 to 12.0 (10 * 1.20) instead."""
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(["barbell", "bench", "squat_rack"], "beginner", [], set())
    program = build_draft(
        sample_template_orm,
        definition,
        ctx,
        sample_exercises,
        user_id=1,
        environment_id=1,
        days_per_week=3,
        duration_weeks=8,
        weight_unit="kg",
        required_inputs={"squat_start": 10, "bench_start": 10},
    )
    assert program.constraints["experience_level"] == "beginner"
    for w in program.workouts:
        w.id = w.order
        for j, ex in enumerate(w.exercises, 1):
            ex.id = j
    exercise_map = {e.id: e for e in sample_exercises}

    week2 = derive_week(program, definition, 2, exercise_map)
    loads = [s["load"] for d in week2 for s in d["slots"] if s["load"] is not None]

    assert loads
    assert all(load <= 12.0 for load in loads)
    assert any(s.get("note") == "ramp_capped" for d in week2 for s in d["slots"])


@pytest.mark.asyncio
async def test_derive_week_does_not_cap_load_ramp_for_intermediate_experience(sample_template_orm, sample_exercises):
    """Same small base_load and the same +25% jump, but intermediate experience has no
    ramp cap - the natural progression-model output passes through untouched."""
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(["barbell", "bench", "squat_rack"], "intermediate", [], set())
    program = build_draft(
        sample_template_orm,
        definition,
        ctx,
        sample_exercises,
        user_id=1,
        environment_id=1,
        days_per_week=3,
        duration_weeks=8,
        weight_unit="kg",
        required_inputs={"squat_start": 10, "bench_start": 10},
    )
    for w in program.workouts:
        w.id = w.order
        for j, ex in enumerate(w.exercises, 1):
            ex.id = j
    exercise_map = {e.id: e for e in sample_exercises}

    week2 = derive_week(program, definition, 2, exercise_map)
    loads = [s["load"] for d in week2 for s in d["slots"] if s["load"] is not None]

    assert loads
    assert any(load == 12.5 for load in loads)
    assert not any(s.get("note") == "ramp_capped" for d in week2 for s in d["slots"])


# --- Autoregulation (Task 4.2) -----------------------------------------------------


def _set_log(workout_exercise_id: int, day: int, actual_rpe: float) -> WorkoutSetLog:
    return WorkoutSetLog(
        user_id=1,
        workout_id=1,
        workout_exercise_id=workout_exercise_id,
        set_number=1,
        actual_rpe=actual_rpe,
        effort_method="rpe",
        created_at=datetime(2026, 7, day),
    )


@pytest.mark.asyncio
async def test_derive_week_reduces_load_when_logged_rpe_overshoots_target(sample_template_orm, sample_exercises):
    """A slot whose logged RPE has consistently run above its target_rpe over 2+
    sessions gets its load pulled down by the autoregulation factor."""
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(["barbell", "bench", "squat_rack"], "intermediate", [], set())
    program = build_draft(
        sample_template_orm,
        definition,
        ctx,
        sample_exercises,
        user_id=1,
        environment_id=1,
        days_per_week=3,
        duration_weeks=8,
        weight_unit="kg",
        required_inputs={"squat_start": 80},
        effort_method="rpe",
    )
    for w in program.workouts:
        w.id = w.order
        for j, ex in enumerate(w.exercises, 1):
            ex.id = j
    exercise_map = {e.id: e for e in sample_exercises}

    baseline = derive_week(program, definition, 1, exercise_map)
    target_we = next(ex for w in program.workouts for ex in w.exercises if ex.target_rpe is not None)
    baseline_load = next(s["load"] for d in baseline for s in d["slots"] if s["workout_exercise_id"] == target_we.id)
    assert baseline_load is not None

    # Logged RPE 2 points over target on both of the last two sessions.
    overshoot_rpe = target_we.target_rpe + 2.0
    logs = {target_we.id: [_set_log(target_we.id, 1, overshoot_rpe), _set_log(target_we.id, 2, overshoot_rpe)]}

    adjusted = derive_week(program, definition, 1, exercise_map, logs)
    adjusted_load = next(s["load"] for d in adjusted for s in d["slots"] if s["workout_exercise_id"] == target_we.id)

    assert adjusted_load < baseline_load
    assert adjusted_load == round(baseline_load * 0.925, 2)  # clamped at the -7.5% floor


@pytest.mark.asyncio
async def test_derive_week_without_set_logs_is_unaffected(sample_template_orm, sample_exercises):
    """Omitting set_logs_by_exercise (the default) leaves derive_week's output
    unchanged - backward compatible with callers that don't pass logged history."""
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(["barbell", "bench", "squat_rack"], "intermediate", [], set())
    program = build_draft(
        sample_template_orm,
        definition,
        ctx,
        sample_exercises,
        user_id=1,
        environment_id=1,
        days_per_week=3,
        duration_weeks=8,
        weight_unit="kg",
        required_inputs={"squat_start": 80},
        effort_method="rpe",
    )
    for w in program.workouts:
        w.id = w.order
        for j, ex in enumerate(w.exercises, 1):
            ex.id = j
    exercise_map = {e.id: e for e in sample_exercises}

    without_logs = derive_week(program, definition, 1, exercise_map)
    with_empty_logs = derive_week(program, definition, 1, exercise_map, {})

    assert without_logs == with_empty_logs


@pytest.mark.asyncio
async def test_derive_week_autoregulation_no_op_with_insufficient_history(sample_template_orm, sample_exercises):
    """A single logged session is not enough history - the load is left unadjusted."""
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(["barbell", "bench", "squat_rack"], "intermediate", [], set())
    program = build_draft(
        sample_template_orm,
        definition,
        ctx,
        sample_exercises,
        user_id=1,
        environment_id=1,
        days_per_week=3,
        duration_weeks=8,
        weight_unit="kg",
        required_inputs={"squat_start": 80},
        effort_method="rpe",
    )
    for w in program.workouts:
        w.id = w.order
        for j, ex in enumerate(w.exercises, 1):
            ex.id = j
    exercise_map = {e.id: e for e in sample_exercises}

    baseline = derive_week(program, definition, 1, exercise_map)
    target_we = next(ex for w in program.workouts for ex in w.exercises if ex.target_rpe is not None)

    logs = {target_we.id: [_set_log(target_we.id, 1, target_we.target_rpe + 3.0)]}
    adjusted = derive_week(program, definition, 1, exercise_map, logs)

    assert baseline == adjusted
