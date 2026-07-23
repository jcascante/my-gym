"""EWMA-based autoregulation controller (Phase 4 plan, Task 4.2).

Reactively adjusts prescribed load based on how actual per-set RPE compares to an
exercise slot's target RPE across recent training sessions. Wraps
`model.resolve()`/`apply_deload()` in `derive_week`, applied *before* `apply_ramp_guard`
(see `preview.py`) so the ramp cap still bounds the final week-over-week change - this
mirrors the existing `apply_deload(model.resolve(...))` wrapper shape rather than
introducing a new integration pattern.

This module is intentionally a sibling of `app.services.program.progression` (which
holds the deterministic, model-based progressions: linear_load, double_progression,
etc.) rather than nested under it: those models are purely prescriptive (week number in,
scheme out); this one is reactive (depends on logged history), and keeping the two apart
avoids conflating "what the plan calls for" with "what the user's actual performance
says to do about it".

`session_logs` need not be pre-filtered to one exercise or pre-grouped into sessions:
the caller (typically a single `WorkoutSetLog` query scoped to a user/program) may pass
rows for other exercises too, and this function does the filtering and grouping itself.
`target_rpe` is deliberately not read off `WorkoutSetLog` - it isn't a column there. It's
the program's designed effort anchor for the slot (`WorkoutExercise.target_rpe`,
constant for the exercise across the mesocycle), which the plan lists as a separate
consumed input, and which the caller already has in hand while iterating slots in
`derive_week` - so it's passed in explicitly rather than re-derived here.
"""

from datetime import date, datetime

from app.models import WorkoutSetLog

EWMA_SPAN = 3
_ALPHA = 2.0 / (EWMA_SPAN + 1)  # pandas-style span->alpha conversion
ADJUSTMENT_K = 0.075
MIN_FACTOR = 0.925
MAX_FACTOR = 1.05
MIN_SESSIONS = 2

INSUFFICIENT_HISTORY_REASON = "insufficient history"


def _to_rpe_scale(value: float, effort_method: str) -> float:
    """Inverse of `preview._effort_target`: maps a logged actual-effort value back to
    the canonical 0-10 RPE scale that `WorkoutExercise.target_rpe` is stored in, so
    signals are comparable regardless of which scale the user logged in."""
    if effort_method == "rir":
        return 10.0 - value
    if effort_method == "borg":
        return (value - 2.0) / 2.0
    return value


def _session_key(log: WorkoutSetLog) -> date:
    created = log.created_at
    return created.date() if isinstance(created, datetime) else created


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def compute_adjustment(
    session_logs: list[WorkoutSetLog],
    exercise_id: int,
    model_key: str,
    target_rpe: float,
) -> tuple[float, str]:
    """Compute a deterministic load-adjustment factor for one exercise slot from its
    logged history.

    Returns `(factor, reason)`. `factor` is in `[MIN_FACTOR, MAX_FACTOR]`
    (0.925-1.05); `factor == 1.0` with `reason == "insufficient history"` when fewer
    than `MIN_SESSIONS` distinct sessions of logged RPE are available for this
    exercise. `model_key` does not affect the computation - it is threaded through for
    traceability (surfaced in `reason`) since callers operate per progression model.
    """
    sessions: dict[date, list[float]] = {}
    for log in session_logs:
        if log.workout_exercise_id != exercise_id or log.actual_rpe is None:
            continue
        key = _session_key(log)
        rpe_equivalent = _to_rpe_scale(log.actual_rpe, log.effort_method)
        sessions.setdefault(key, []).append(rpe_equivalent)

    if len(sessions) < MIN_SESSIONS:
        return 1.0, INSUFFICIENT_HISTORY_REASON

    ordered_keys = sorted(sessions.keys())
    signals = [sum(sessions[key]) / len(sessions[key]) - target_rpe for key in ordered_keys]

    smoothed = signals[0]
    for signal in signals[1:]:
        smoothed = _ALPHA * signal + (1 - _ALPHA) * smoothed

    raw_factor = 1.0 - ADJUSTMENT_K * smoothed
    factor = round(_clamp(raw_factor, MIN_FACTOR, MAX_FACTOR), 6)
    smoothed_rounded = round(smoothed, 6)
    clamped_suffix = " (clamped)" if round(raw_factor, 6) != factor else ""

    reason = (
        f"ewma_rpe_signal={smoothed_rounded:+.6f} over {len(sessions)} sessions " f"(model={model_key}){clamped_suffix}"
    )
    return factor, reason
