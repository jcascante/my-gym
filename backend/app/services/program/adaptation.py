from pydantic import BaseModel

from app.core.exceptions import ValidationError
from app.models.exercise import Exercise
from app.models.program import Workout, WorkoutExercise, WorkoutProgram
from app.schemas.template import SlotRule, TemplateDefinition
from app.services.program.selection import SelectionContext, _matches_rule, _passes_filters, select_for_slot


class FeedbackAction(BaseModel):
    type: str
    workout_exercise_id: int | None = None
    exercise_id: int | None = None
    workout_key: str | None = None
    delta: int | None = None


def _find_slot(program: WorkoutProgram, we_id: int) -> tuple[Workout | None, WorkoutExercise | None]:
    for w in program.workouts:
        for ex in w.exercises:
            if ex.id == we_id:
                return w, ex
    return None, None


def _reselect_exercise(
    program: WorkoutProgram, ex: WorkoutExercise, ctx: SelectionContext, exercises: list[Exercise]
) -> None:
    """Core reselection logic, operating directly on an already-located WorkoutExercise
    object rather than looking it up by id -- id-based lookup breaks for unsaved drafts,
    where every row's id is None until the program is persisted (see _find_slot)."""
    if ex.is_locked:
        return
    rule = SlotRule(**ex.fills_rule)
    excluded = set(program.constraints.get("excluded_exercise_ids", []))
    locked = program.constraints.get("swaps", {}).get(str(ex.id))
    chosen = select_for_slot(exercises, rule, ctx, locked, excluded)
    if chosen is not None:
        ex.exercise_id = chosen.id


def _reselect(program: WorkoutProgram, we_id: int, ctx: SelectionContext, exercises: list[Exercise]) -> None:
    _, ex = _find_slot(program, we_id)
    if ex is None:
        return
    _reselect_exercise(program, ex, ctx, exercises)


def apply_feedback(
    program: WorkoutProgram,
    definition: TemplateDefinition,
    action: FeedbackAction,
    ctx: SelectionContext,
    exercises: list[Exercise],
) -> WorkoutProgram:
    c = program.constraints
    c.setdefault("locked_slots", [])
    c.setdefault("excluded_exercise_ids", [])
    c.setdefault("swaps", {})
    c.setdefault("volume_adjustments", {})

    if action.type == "lock" and action.workout_exercise_id is not None:
        _, ex = _find_slot(program, action.workout_exercise_id)
        if ex is not None:
            ex.is_locked = True
            if action.workout_exercise_id not in c["locked_slots"]:
                c["locked_slots"].append(action.workout_exercise_id)

    elif action.type == "swap" and action.workout_exercise_id is not None and action.exercise_id is not None:
        _, ex = _find_slot(program, action.workout_exercise_id)
        if ex is not None and not ex.is_locked:
            rule = SlotRule(**ex.fills_rule)
            candidate = next((e for e in exercises if e.id == action.exercise_id), None)
            if candidate is None or not (_matches_rule(candidate, rule) and _passes_filters(candidate, ctx)):
                raise ValidationError(f"Exercise {action.exercise_id} is not a valid substitute for this slot")
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
        c["volume_adjustments"][action.workout_key] = c["volume_adjustments"].get(action.workout_key, 0) + action.delta
        for w in program.workouts:
            if w.key == action.workout_key:
                for ex in w.exercises:
                    ex.sets = max(1, ex.sets + action.delta)

    # SQLAlchemy needs a new dict object to detect the JSON mutation
    program.constraints = dict(c)
    return program


def alternatives_for_slot(
    program: WorkoutProgram,
    definition: TemplateDefinition,
    workout_exercise_id: int,
    ctx: SelectionContext,
    exercises: list[Exercise],
) -> list[Exercise]:
    _, ex = _find_slot(program, workout_exercise_id)
    if ex is None:
        return []
    rule = SlotRule(**ex.fills_rule)
    return [e for e in exercises if _matches_rule(e, rule) and _passes_filters(e, ctx) and e.id != ex.exercise_id]
