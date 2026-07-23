from datetime import date, datetime, timedelta

from app.models import UserWorkoutLog
from app.services.progression.deload import (
    INSUFFICIENT_SIGNAL_REASON,
    compute_deload_trigger,
)

REFERENCE_DATE = date(2026, 7, 23)


def _log(days_before_reference: int, readiness: int | None, workout_id: int = 1) -> UserWorkoutLog:
    session_date = datetime.combine(REFERENCE_DATE - timedelta(days=days_before_reference), datetime.min.time())
    return UserWorkoutLog(
        user_id=1,
        workout_id=workout_id,
        session_date=session_date,
        readiness=readiness,
    )


def test_empty_history_does_not_trigger():
    triggered, reason = compute_deload_trigger([], REFERENCE_DATE)
    assert triggered is False
    assert reason == INSUFFICIENT_SIGNAL_REASON


def test_single_low_readiness_session_is_insufficient():
    logs = [_log(1, 2)]
    triggered, reason = compute_deload_trigger(logs, REFERENCE_DATE)
    assert triggered is False
    assert reason == INSUFFICIENT_SIGNAL_REASON


def test_two_low_readiness_sessions_within_window_trigger():
    logs = [_log(1, 2), _log(3, 1)]
    triggered, reason = compute_deload_trigger(logs, REFERENCE_DATE)
    assert triggered is True
    assert "low_readiness_sessions=2" in reason
    assert "threshold<=2" in reason


def test_readiness_above_threshold_does_not_count_as_low():
    logs = [_log(1, 3), _log(2, 3), _log(3, 3)]
    triggered, reason = compute_deload_trigger(logs, REFERENCE_DATE)
    assert triggered is False
    assert reason == INSUFFICIENT_SIGNAL_REASON


def test_readiness_exactly_at_threshold_counts_as_low():
    # threshold is 2 (<=), so readiness == 2 must count
    logs = [_log(1, 2), _log(2, 2)]
    triggered, _reason = compute_deload_trigger(logs, REFERENCE_DATE)
    assert triggered is True


def test_sessions_outside_lookback_window_are_ignored():
    logs = [_log(1, 2), _log(20, 1)]  # second is 20 days ago, outside 14-day window
    triggered, reason = compute_deload_trigger(logs, REFERENCE_DATE)
    assert triggered is False
    assert reason == INSUFFICIENT_SIGNAL_REASON


def test_session_exactly_at_lookback_boundary_is_included():
    logs = [_log(1, 2), _log(14, 1)]  # 14 days ago is the inclusive edge of the window
    triggered, _reason = compute_deload_trigger(logs, REFERENCE_DATE)
    assert triggered is True


def test_session_after_reference_date_is_ignored():
    future_log = UserWorkoutLog(
        user_id=1,
        workout_id=1,
        session_date=datetime.combine(REFERENCE_DATE + timedelta(days=1), datetime.min.time()),
        readiness=1,
    )
    logs = [_log(1, 2), future_log]
    triggered, reason = compute_deload_trigger(logs, REFERENCE_DATE)
    assert triggered is False
    assert reason == INSUFFICIENT_SIGNAL_REASON


def test_none_readiness_entries_are_ignored():
    logs = [_log(1, 2), _log(2, None), _log(3, 2)]
    triggered, _reason = compute_deload_trigger(logs, REFERENCE_DATE)
    assert triggered is True  # two valid low-readiness sessions, the None is skipped


def test_mixed_high_and_low_readiness_still_triggers_on_low_count():
    logs = [_log(1, 5), _log(2, 4), _log(3, 2), _log(4, 1), _log(5, 3)]
    triggered, reason = compute_deload_trigger(logs, REFERENCE_DATE)
    assert triggered is True
    assert "low_readiness_sessions=2" in reason


def test_more_than_minimum_low_readiness_sessions_still_triggers():
    logs = [_log(1, 2), _log(3, 1), _log(5, 2)]
    triggered, reason = compute_deload_trigger(logs, REFERENCE_DATE)
    assert triggered is True
    assert "low_readiness_sessions=3" in reason


def test_reason_includes_sorted_dates():
    logs = [_log(5, 2), _log(1, 1)]  # deliberately out of order
    _triggered, reason = compute_deload_trigger(logs, REFERENCE_DATE)
    older = (REFERENCE_DATE - timedelta(days=5)).isoformat()
    newer = (REFERENCE_DATE - timedelta(days=1)).isoformat()
    assert reason.index(older) < reason.index(newer)


def test_determinism_same_inputs_produce_byte_identical_output():
    logs = [_log(1, 2), _log(3, 1), _log(10, 5)]
    result_a = compute_deload_trigger(logs, REFERENCE_DATE)
    result_b = compute_deload_trigger(logs, REFERENCE_DATE)
    assert result_a == result_b


def test_determinism_is_independent_of_input_order():
    logs_forward = [_log(1, 2), _log(3, 1)]
    logs_reversed = list(reversed(logs_forward))
    assert compute_deload_trigger(logs_forward, REFERENCE_DATE) == compute_deload_trigger(logs_reversed, REFERENCE_DATE)
