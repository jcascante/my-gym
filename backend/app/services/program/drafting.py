from app.models import Exercise, ProgramStatus, ProgramTemplate, Workout, WorkoutExercise, WorkoutProgram
from app.schemas.template import SlotRule, TemplateDefinition
from app.services.program.selection import SelectionContext, select_for_slot


def _base_load_for(rule: SlotRule, applies_to_values: dict[str, float]) -> float | None:
    value = applies_to_values.get(rule.pattern) if rule.pattern else None
    if value is None and rule.region:
        value = applies_to_values.get(rule.region)
    return float(value) if value is not None else None


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
                    base_load=_base_load_for(rule, applies_to_values),
                    rest_seconds=scheme.rest_seconds,
                    scheme_key=rule.scheme,
                    is_locked=False,
                    is_user_swapped=False,
                )
            )
        program.workouts.append(workout)
    return program
