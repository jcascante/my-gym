from app.models.exercise import BodyRegion, Exercise, ExperienceLevel, MovementPattern
from app.models.program import ProgramTemplate, Workout, WorkoutExercise, WorkoutProgram
from app.schemas.template import ProgressionRef, SplitDef, TemplateDefinition
from app.services.program.explain import explain_slot, explain_template
from app.services.program.matching import MatchInput
from app.services.program.selection import ActiveInjuryProvocation, SelectionContext

FEATURE_KEYS = {
    "variety",
    "priority_fit",
    "muscle_fit",
    "difficulty",
    "unilateral_balance",
    "movement_preference",
    "complementary_coverage",
}


def _exercise(
    id_: int,
    slug: str,
    *,
    movement_slug: str,
    primary_muscles: list[str],
    contraindications: list[str] | None = None,
    provocation_tags: list[str] | None = None,
) -> Exercise:
    return Exercise(
        id=id_,
        name=slug,
        slug=slug,
        movement_slug=movement_slug,
        body_region=BodyRegion.LOWER_BODY,
        movement_pattern=MovementPattern.SQUAT,
        primary_muscles=primary_muscles,
        secondary_muscles=[],
        equipment_tags=[],
        difficulty_level=ExperienceLevel.INTERMEDIATE,
        instructions="Do the thing.",
        form_cues=[],
        contraindications=contraindications or [],
        provocation_tags=provocation_tags or [],
        is_unilateral=False,
        is_compound=True,
        is_active=True,
    )


def _workout_exercise(
    id_: int, order: int, exercise_id: int, *, sets: int, scheme_key: str = "main"
) -> WorkoutExercise:
    return WorkoutExercise(
        id=id_,
        order=order,
        exercise_id=exercise_id,
        fills_rule={"pattern": "squat", "priority": "primary"},
        sets=sets,
        reps_min=5,
        reps_max=8,
        base_load=None,
        rest_seconds=120,
        scheme_key=scheme_key,
        target_rpe=None,
        intensity_pct=None,
        is_locked=False,
        is_user_swapped=False,
        rotation_pool=[],
    )


def _ctx(**kwargs: object) -> SelectionContext:
    defaults: dict = {
        "equipment": [],
        "experience": "intermediate",
        "injuries": [],
        "used_movement_slugs": set(),
    }
    defaults.update(kwargs)
    return SelectionContext(**defaults)


def test_explain_template_scores_the_single_template_as_best_tier():
    template = ProgramTemplate(
        id=1,
        name="Solo Template",
        slug="solo-template",
        goals=["strength"],
        experience_levels=["intermediate"],
        days_per_week_min=3,
        days_per_week_max=5,
        session_duration_min=45,
        session_duration_max=75,
    )
    definition = TemplateDefinition(
        split=SplitDef(sessions=[]), progression=ProgressionRef(model_key="linear_load"), schemes={}
    )
    match_input = MatchInput(
        fitness_focus="strength",
        experience_level="intermediate",
        days_per_week=4,
        session_duration_min=60,
        environment_equipment=[],
    )

    match = explain_template(template, definition, [], match_input)

    assert match.template_id == 1
    assert match.tier == "best"
    assert set(match.factors.keys()) == {
        "goal",
        "experience",
        "days",
        "duration",
        "movement_preference",
        "focus_complement",
        "periodization",
    }


def test_explain_slot_replays_prior_picks_so_variety_reflects_accumulated_state():
    ex1 = _exercise(1, "back-squat", movement_slug="squat_slug", primary_muscles=["quads"])
    ex2 = _exercise(2, "front-squat", movement_slug="squat_slug", primary_muscles=["hamstrings"])
    we1 = _workout_exercise(1, 1, ex1.id, sets=3, scheme_key="main")
    we2 = _workout_exercise(2, 2, ex2.id, sets=4, scheme_key="accessory")
    workout = Workout(id=1, program_id=1, key="day_1", name="Day 1", order=1, exercises=[we1, we2])
    program = WorkoutProgram(
        id=1,
        user_id=1,
        template_id=1,
        environment_id=1,
        name="p",
        duration_weeks=8,
        days_per_week=3,
        constraints={},
        workouts=[workout],
    )

    explanation = explain_slot(program, workout_exercise_id=2, ctx=_ctx(), exercises=[ex1, ex2])

    assert explanation is not None
    assert explanation.factors["variety"] == 0.0  # squat_slug already used by we1's replay
    assert {c.group: c.effective_sets for c in explanation.ledger_contributions} == {"hamstrings": 4.0}


def test_explain_slot_first_slot_has_no_prior_state_so_variety_is_full():
    ex1 = _exercise(1, "back-squat", movement_slug="squat_slug", primary_muscles=["quads"])
    we1 = _workout_exercise(1, 1, ex1.id, sets=3)
    workout = Workout(id=1, program_id=1, key="day_1", name="Day 1", order=1, exercises=[we1])
    program = WorkoutProgram(
        id=1,
        user_id=1,
        template_id=1,
        environment_id=1,
        name="p",
        duration_weeks=8,
        days_per_week=3,
        constraints={},
        workouts=[workout],
    )

    explanation = explain_slot(program, workout_exercise_id=1, ctx=_ctx(), exercises=[ex1])

    assert explanation is not None
    assert explanation.factors["variety"] == 1.0
    assert set(explanation.factors.keys()) == FEATURE_KEYS


def test_explain_slot_returns_none_for_unknown_workout_exercise_id():
    ex1 = _exercise(1, "back-squat", movement_slug="squat_slug", primary_muscles=["quads"])
    we1 = _workout_exercise(1, 1, ex1.id, sets=3)
    workout = Workout(id=1, program_id=1, key="day_1", name="Day 1", order=1, exercises=[we1])
    program = WorkoutProgram(
        id=1,
        user_id=1,
        template_id=1,
        environment_id=1,
        name="p",
        duration_weeks=8,
        days_per_week=3,
        constraints={},
        workouts=[workout],
    )

    assert explain_slot(program, workout_exercise_id=999, ctx=_ctx(), exercises=[ex1]) is None


def test_explain_slot_safety_note_flags_hard_excluded_contraindication():
    ex1 = _exercise(1, "back-squat", movement_slug="squat_slug", primary_muscles=["quads"], contraindications=["knee"])
    we1 = _workout_exercise(1, 1, ex1.id, sets=3)
    workout = Workout(id=1, program_id=1, key="day_1", name="Day 1", order=1, exercises=[we1])
    program = WorkoutProgram(
        id=1,
        user_id=1,
        template_id=1,
        environment_id=1,
        name="p",
        duration_weeks=8,
        days_per_week=3,
        constraints={},
        workouts=[workout],
    )

    explanation = explain_slot(program, workout_exercise_id=1, ctx=_ctx(injuries=["knee"]), exercises=[ex1])

    assert explanation is not None
    assert explanation.safety_note is not None
    assert "hard-excluded" in explanation.safety_note


def test_explain_slot_safety_note_flags_active_provocation_overlap():
    ex1 = _exercise(
        1,
        "back-squat",
        movement_slug="squat_slug",
        primary_muscles=["quads"],
        provocation_tags=["deep_knee_flexion"],
    )
    we1 = _workout_exercise(1, 1, ex1.id, sets=3)
    workout = Workout(id=1, program_id=1, key="day_1", name="Day 1", order=1, exercises=[we1])
    program = WorkoutProgram(
        id=1,
        user_id=1,
        template_id=1,
        environment_id=1,
        name="p",
        duration_weeks=8,
        days_per_week=3,
        constraints={},
        workouts=[workout],
    )
    ctx = _ctx(injury_provocations=[ActiveInjuryProvocation(provocation="deep_knee_flexion", is_rehabilitating=False)])

    explanation = explain_slot(program, workout_exercise_id=1, ctx=ctx, exercises=[ex1])

    assert explanation is not None
    assert explanation.safety_note is not None
    assert "provocation" in explanation.safety_note


def test_explain_slot_safety_note_flags_active_amber_penalty():
    ex1 = _exercise(1, "back-squat", movement_slug="squat_slug", primary_muscles=["quads"], contraindications=["knee"])
    we1 = _workout_exercise(1, 1, ex1.id, sets=3)
    workout = Workout(id=1, program_id=1, key="day_1", name="Day 1", order=1, exercises=[we1])
    program = WorkoutProgram(
        id=1,
        user_id=1,
        template_id=1,
        environment_id=1,
        name="p",
        duration_weeks=8,
        days_per_week=3,
        constraints={},
        workouts=[workout],
    )
    ctx = _ctx(region_score_penalties={"knee": -0.15})

    explanation = explain_slot(program, workout_exercise_id=1, ctx=ctx, exercises=[ex1])

    assert explanation is not None
    assert explanation.safety_note is not None
    assert "amber" in explanation.safety_note


def test_explain_slot_safety_note_is_none_when_no_hazard_active():
    ex1 = _exercise(1, "back-squat", movement_slug="squat_slug", primary_muscles=["quads"])
    we1 = _workout_exercise(1, 1, ex1.id, sets=3)
    workout = Workout(id=1, program_id=1, key="day_1", name="Day 1", order=1, exercises=[we1])
    program = WorkoutProgram(
        id=1,
        user_id=1,
        template_id=1,
        environment_id=1,
        name="p",
        duration_weeks=8,
        days_per_week=3,
        constraints={},
        workouts=[workout],
    )

    explanation = explain_slot(program, workout_exercise_id=1, ctx=_ctx(), exercises=[ex1])

    assert explanation is not None
    assert explanation.safety_note is None
