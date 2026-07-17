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
