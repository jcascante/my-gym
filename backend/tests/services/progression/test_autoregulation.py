from datetime import datetime

from app.models import WorkoutSetLog
from app.services.progression.autoregulation import (
    ADJUSTMENT_K,
    INSUFFICIENT_HISTORY_REASON,
    MAX_FACTOR,
    MIN_FACTOR,
    compute_adjustment,
)

EXERCISE_ID = 42
MODEL_KEY = "linear_load"


def _log(
    day: int,
    actual_rpe: float | None,
    effort_method: str = "rpe",
    exercise_id: int = EXERCISE_ID,
    set_number: int = 1,
) -> WorkoutSetLog:
    return WorkoutSetLog(
        user_id=1,
        workout_id=1,
        workout_exercise_id=exercise_id,
        set_number=set_number,
        actual_weight=100.0,
        actual_reps=5,
        actual_rpe=actual_rpe,
        effort_method=effort_method,
        created_at=datetime(2026, 7, day),
    )


def test_empty_history_returns_neutral_factor_with_reason():
    factor, reason = compute_adjustment([], EXERCISE_ID, MODEL_KEY, target_rpe=7.0)
    assert factor == 1.0
    assert reason == INSUFFICIENT_HISTORY_REASON


def test_single_session_is_insufficient_history():
    logs = [_log(1, 8.0), _log(1, 8.5)]  # same calendar day = one session
    factor, reason = compute_adjustment(logs, EXERCISE_ID, MODEL_KEY, target_rpe=7.0)
    assert factor == 1.0
    assert reason == INSUFFICIENT_HISTORY_REASON


def test_two_sessions_constant_overshoot_reduces_load_to_the_boundary():
    # signal = 8.0 - 7.0 = 1.0 both sessions -> EWMA smoothed = 1.0
    # raw factor = 1.0 - 0.075*1.0 = 0.925 (exactly MIN_FACTOR, not clamped further)
    logs = [_log(1, 8.0), _log(2, 8.0)]
    factor, reason = compute_adjustment(logs, EXERCISE_ID, MODEL_KEY, target_rpe=7.0)
    assert factor == MIN_FACTOR
    assert "clamped" not in reason
    assert "2 sessions" in reason


def test_two_sessions_constant_undershoot_raises_load_to_the_boundary():
    # signal = 6.0 - 8.0 = -2.0 both sessions -> raw factor = 1.0 - 0.075*(-2.0) = 1.15
    # clamped down to MAX_FACTOR (1.05)
    logs = [_log(1, 6.0), _log(2, 6.0)]
    factor, reason = compute_adjustment(logs, EXERCISE_ID, MODEL_KEY, target_rpe=8.0)
    assert factor == MAX_FACTOR
    assert "clamped" in reason


def test_large_overshoot_clamps_at_minimum_factor():
    # signal = 9.0 - 6.0 = 3.0 both sessions -> raw factor = 1.0 - 0.225 = 0.775
    # clamped up to MIN_FACTOR (0.925)
    logs = [_log(1, 9.0), _log(2, 9.0)]
    factor, reason = compute_adjustment(logs, EXERCISE_ID, MODEL_KEY, target_rpe=6.0)
    assert factor == MIN_FACTOR
    assert "clamped" in reason


def test_three_sessions_ewma_weights_recent_signal_more_heavily():
    # signals (oldest -> newest): 2.0, 1.0, 0.0 (trending back to target)
    # y0=2.0; y1=0.5*1.0+0.5*2.0=1.5; y2=0.5*0.0+0.5*1.5=0.75
    # raw factor = 1.0 - 0.075*0.75 = 0.94375
    logs = [_log(1, 9.0), _log(2, 8.0), _log(3, 7.0)]
    factor, reason = compute_adjustment(logs, EXERCISE_ID, MODEL_KEY, target_rpe=7.0)
    assert factor == 0.94375
    assert "3 sessions" in reason


def test_multiple_sets_within_a_session_are_averaged_before_signal():
    # session 1: sets at 7.0 and 9.0 -> avg 8.0 -> signal 1.0 (vs target 7.0)
    # session 2: single set at 7.5 -> signal 0.5
    # y0=1.0; y1=0.5*0.5+0.5*1.0=0.75 -> raw factor=1.0-0.075*0.75=0.94375 (unclamped)
    # (if the two session-1 sets were wrongly treated as separate sessions instead of
    # averaged, the EWMA - and thus the factor - would come out differently)
    logs = [
        _log(1, 7.0, set_number=1),
        _log(1, 9.0, set_number=2),
        _log(2, 7.5, set_number=1),
    ]
    factor, _reason = compute_adjustment(logs, EXERCISE_ID, MODEL_KEY, target_rpe=7.0)
    assert factor == 0.94375


def test_ignores_logs_for_other_exercises():
    logs = [
        _log(1, 8.0, exercise_id=EXERCISE_ID),
        _log(2, 8.0, exercise_id=EXERCISE_ID),
        _log(1, 3.0, exercise_id=999),  # would badly skew the signal if not filtered out
        _log(2, 3.0, exercise_id=999),
    ]
    factor, _reason = compute_adjustment(logs, EXERCISE_ID, MODEL_KEY, target_rpe=7.0)
    assert factor == MIN_FACTOR  # same result as if the other exercise's logs were absent


def test_ignores_sets_with_no_logged_rpe():
    logs = [
        _log(1, 8.0),
        _log(1, None),  # user skipped RPE entry for this set
        _log(2, 8.0),
    ]
    factor, _reason = compute_adjustment(logs, EXERCISE_ID, MODEL_KEY, target_rpe=7.0)
    assert factor == MIN_FACTOR


def test_rir_scale_is_converted_to_rpe_before_computing_signal():
    # RIR 1 == RPE 9 (10 - RIR); target 8.0 -> signal +1.0 both sessions
    logs = [_log(1, 1.0, effort_method="rir"), _log(2, 1.0, effort_method="rir")]
    factor, _reason = compute_adjustment(logs, EXERCISE_ID, MODEL_KEY, target_rpe=8.0)
    assert factor == MIN_FACTOR


def test_borg_scale_is_converted_to_rpe_before_computing_signal():
    # Borg 16 == RPE 7.0 ((16-2)/2); target 8.0 -> signal -1.0 both sessions
    # raw factor = 1.0 - 0.075*(-1.0) = 1.075 -> clamped to MAX_FACTOR
    logs = [_log(1, 16.0, effort_method="borg"), _log(2, 16.0, effort_method="borg")]
    factor, _reason = compute_adjustment(logs, EXERCISE_ID, MODEL_KEY, target_rpe=8.0)
    assert factor == MAX_FACTOR


def test_reason_includes_model_key():
    logs = [_log(1, 8.0), _log(2, 8.0)]
    _factor, reason = compute_adjustment(logs, EXERCISE_ID, MODEL_KEY, target_rpe=7.0)
    assert MODEL_KEY in reason


def test_determinism_same_inputs_produce_byte_identical_output():
    logs = [_log(1, 9.0), _log(2, 8.0), _log(3, 7.0)]
    result_a = compute_adjustment(logs, EXERCISE_ID, MODEL_KEY, target_rpe=7.0)
    result_b = compute_adjustment(logs, EXERCISE_ID, MODEL_KEY, target_rpe=7.0)
    assert result_a == result_b
    factor, _reason = result_a
    assert round(factor, 6) == factor  # exact to 6 decimal places


def test_adjustment_factor_never_exceeds_configured_bounds():
    # Extreme overshoot: far beyond what k=0.075 could keep in-bounds unclamped
    logs = [_log(1, 10.0), _log(2, 10.0)]
    factor, _reason = compute_adjustment(logs, EXERCISE_ID, MODEL_KEY, target_rpe=1.0)
    assert MIN_FACTOR <= factor <= MAX_FACTOR


def test_k_constant_matches_spec():
    assert ADJUSTMENT_K == 0.075
