from datetime import date
from typing import Any

from app.core.constants import DELOAD_LOAD_FACTOR
from app.models import Exercise, WorkoutExercise, WorkoutProgram
from app.models.logging import UserWorkoutLog, WorkoutSetLog
from app.schemas.template import TemplateDefinition
from app.services.program.progression.base import SetScheme, SlotBase, get_model
from app.services.program.progression.deload import apply_deload
from app.services.program.progression.ramp_guard import apply_ramp_guard, population_for
from app.services.progression.autoregulation import compute_adjustment
from app.services.progression.deload import compute_deload_trigger

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


def _apply_reactive_deload(scheme: SetScheme, triggered: bool) -> SetScheme:
    """Wraps a resolved (and possibly scheduled-deloaded) scheme with the readiness-
    triggered load reduction (Task 4.3), before `_apply_autoregulation` and
    `apply_ramp_guard` run - same "wrap model.resolve() output" shape `apply_deload`
    already uses. A no-op when the trigger hasn't fired or the slot has no load
    (bodyweight). `apply_ramp_guard` only caps growth (`min(scheme.load, max_load)`),
    never decreases, so this reduction always passes through it unclamped."""
    if not triggered or scheme.load is None:
        return scheme
    return SetScheme(
        sets=scheme.sets,
        reps=scheme.reps,
        load=round(scheme.load * DELOAD_LOAD_FACTOR, 2),
        rest_seconds=scheme.rest_seconds,
        note="reactive_deload",
    )


def _apply_autoregulation(scheme: SetScheme, factor: float) -> SetScheme:
    """Wraps a resolved+deloaded scheme with the EWMA autoregulation factor, before
    `apply_ramp_guard` runs (plan Task 4.2) - same "wrap model.resolve() output" shape
    `apply_deload` already uses. A no-op when there's nothing to adjust (factor==1.0,
    e.g. insufficient history) or the slot has no load (bodyweight)."""
    if factor == 1.0 or scheme.load is None:
        return scheme
    return SetScheme(
        sets=scheme.sets,
        reps=scheme.reps,
        load=round(scheme.load * factor, 2),
        rest_seconds=scheme.rest_seconds,
        note=scheme.note or "autoregulated",
    )


def _resolved_exercise_id(ex: WorkoutExercise, week: int) -> int:
    pool = ex.rotation_pool
    if pool and len(pool) > 1:
        return pool[(week - 1) % len(pool)]
    return ex.exercise_id


def derive_week(
    program: WorkoutProgram,
    definition: TemplateDefinition,
    week: int,
    exercises: dict[int, Exercise] | None = None,
    set_logs_by_exercise: dict[int, list[WorkoutSetLog]] | None = None,
    readiness_logs: list[UserWorkoutLog] | None = None,
    reference_date: date | None = None,
) -> list[dict[str, Any]]:
    model = get_model(definition.progression.model_key)
    every = definition.progression.deload_every
    params = definition.progression.params
    effort_method = program.constraints.get("effort_method")
    check_in_load_adjustments = program.constraints.get("check_in_load_adjustments", {})
    experience = program.constraints.get("experience_level", "intermediate")
    exercise_map = exercises or {}
    reactive_deload_triggered = False
    if readiness_logs:
        reactive_deload_triggered, _reactive_deload_reason = compute_deload_trigger(
            readiness_logs, reference_date or date.today()
        )
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
            resolved_exercise_id = _resolved_exercise_id(ex, week)
            exercise = exercise_map.get(resolved_exercise_id)
            population = population_for(
                exercise.contraindications if exercise else [], check_in_load_adjustments, experience
            )
            autoreg_factor = 1.0
            if ex.target_rpe is not None and set_logs_by_exercise:
                logs_for_slot = set_logs_by_exercise.get(ex.id, [])
                if logs_for_slot:
                    autoreg_factor, _reason = compute_adjustment(
                        logs_for_slot, ex.id, definition.progression.model_key, ex.target_rpe
                    )
            prior_scheme = None
            if population != "unrestricted" and week > 1:
                # Autoregulated, not nominal: the ramp cap must bound against what was
                # *actually* prescribed last week, or a load cut from autoregulation
                # silently widens this week's allowed ramp (see task 4.2 review).
                prior_scheme = _apply_autoregulation(
                    apply_deload(model.resolve(base, week - 1, params), week - 1, every), autoreg_factor
                )
            scheduled_scheme = apply_deload(model.resolve(base, week, params), week, every)
            deloaded_scheme = _apply_reactive_deload(scheduled_scheme, reactive_deload_triggered)
            resolved_scheme = _apply_autoregulation(deloaded_scheme, autoreg_factor)
            scheme = apply_ramp_guard(resolved_scheme, prior_scheme, population)
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
