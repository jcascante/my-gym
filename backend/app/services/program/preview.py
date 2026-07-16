from typing import Any

from app.models import WorkoutProgram
from app.schemas.template import TemplateDefinition
from app.services.program.progression.base import SlotBase, get_model
from app.services.program.progression.deload import apply_deload


def derive_week(program: WorkoutProgram, definition: TemplateDefinition, week: int) -> list[dict[str, Any]]:
    model = get_model(definition.progression.model_key)
    every = definition.progression.deload_every
    params = definition.progression.params
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
            slots.append(
                {
                    "workout_exercise_id": ex.id,
                    "exercise_id": ex.exercise_id,
                    "sets": scheme.sets,
                    "reps": scheme.reps,
                    "load": scheme.load,
                    "rest_seconds": scheme.rest_seconds,
                    "note": scheme.note,
                    "is_locked": ex.is_locked,
                    "is_user_swapped": ex.is_user_swapped,
                }
            )
        days.append({"workout_id": workout.id, "key": workout.key, "name": workout.name, "slots": slots})
    return days
