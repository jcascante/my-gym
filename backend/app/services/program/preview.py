from typing import Any

from app.models import Exercise, WorkoutExercise, WorkoutProgram
from app.schemas.template import TemplateDefinition
from app.services.program.progression.base import SetScheme, SlotBase, get_model
from app.services.program.progression.deload import apply_deload

_STRENGTH_REST_SECONDS = 195
_HYPERTROPHY_REST_SECONDS = 120
_ENDURANCE_REST_SECONDS = 68

_WARMUP_RAMP: list[tuple[float, int]] = [(0.4, 5), (0.6, 3), (0.8, 1)]


def _rest_seconds_for_intent(reps: int, intensity_pct: float | None) -> int:
    if reps <= 6 or (intensity_pct is not None and intensity_pct >= 0.85):
        return _STRENGTH_REST_SECONDS
    if reps <= 12:
        return _HYPERTROPHY_REST_SECONDS
    return _ENDURANCE_REST_SECONDS


def _warmup_sets(load: float | None) -> list[dict[str, object]]:
    if load is None:
        return []
    return [{"pct": pct, "reps": reps, "load": round(pct * load, 1)} for pct, reps in _WARMUP_RAMP]


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


def _resolved_exercise_id(ex: WorkoutExercise, week: int) -> int:
    pool = ex.rotation_pool
    if pool and len(pool) > 1:
        return pool[(week - 1) % len(pool)]
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
        first_primary_assigned = False
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
            rest_seconds = _rest_seconds_for_intent(scheme.reps, ex.intensity_pct)
            is_first_primary = not first_primary_assigned and ex.fills_rule.get("priority") == "primary"
            if is_first_primary:
                first_primary_assigned = True
            warmup_sets = _warmup_sets(scheme.load) if is_first_primary else []
            slots.append(
                {
                    "workout_exercise_id": ex.id,
                    "exercise_id": resolved_exercise_id,
                    "exercise_name": exercise_name,
                    "sets": scheme.sets,
                    "reps": scheme.reps,
                    "load": scheme.load,
                    "rest_seconds": rest_seconds,
                    "note": scheme.note,
                    "is_locked": ex.is_locked,
                    "is_user_swapped": ex.is_user_swapped,
                    "effort_target": _effort_target(scheme, ex.target_rpe, ex.intensity_pct, effort_method),
                    "rotation_pool": ex.rotation_pool,
                    "tempo": "controlled",
                    "warmup_sets": warmup_sets,
                }
            )
        days.append({"workout_id": workout.id, "key": workout.key, "name": workout.name, "slots": slots})
    return days
