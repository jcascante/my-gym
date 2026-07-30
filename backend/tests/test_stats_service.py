from datetime import date

from app.models import SessionStatus, WorkoutSession, WorkoutSetLog
from app.services.stats import current_streak_days, personal_records, total_volume, workouts_this_month


def _session(scheduled_date: date, program_id: int = 1) -> WorkoutSession:
    return WorkoutSession(
        program_id=program_id,
        workout_id=1,
        week=1,
        scheduled_date=scheduled_date,
        status=SessionStatus.COMPLETED,
    )


def _set_log(session_id: int, workout_exercise_id: int, weight: float, reps: int) -> WorkoutSetLog:
    return WorkoutSetLog(
        user_id=1,
        workout_id=1,
        workout_exercise_id=workout_exercise_id,
        session_id=session_id,
        set_number=1,
        actual_weight=weight,
        actual_reps=reps,
    )


def test_workouts_this_month_counts_only_the_current_calendar_month() -> None:
    today = date(2026, 7, 29)
    sessions = [_session(date(2026, 7, 1)), _session(date(2026, 7, 29)), _session(date(2026, 6, 30))]

    assert workouts_this_month(sessions, today) == 2


def test_streak_counts_consecutive_days_ending_today() -> None:
    today = date(2026, 7, 29)
    sessions = [_session(date(2026, 7, 29)), _session(date(2026, 7, 28)), _session(date(2026, 7, 27))]

    assert current_streak_days(sessions, today) == 3


def test_streak_allows_a_one_day_grace_before_todays_workout() -> None:
    today = date(2026, 7, 29)
    sessions = [_session(date(2026, 7, 28)), _session(date(2026, 7, 27))]

    assert current_streak_days(sessions, today) == 2


def test_streak_breaks_on_a_gap() -> None:
    today = date(2026, 7, 29)
    sessions = [_session(date(2026, 7, 29)), _session(date(2026, 7, 26))]

    assert current_streak_days(sessions, today) == 1


def test_streak_is_zero_with_no_completed_sessions() -> None:
    assert current_streak_days([], date(2026, 7, 29)) == 0


def test_streak_resets_after_more_than_a_day_gap_from_today() -> None:
    today = date(2026, 7, 29)
    sessions = [_session(date(2026, 7, 26))]

    assert current_streak_days(sessions, today) == 0


def test_personal_records_counts_exercises_at_their_current_best() -> None:
    # exercise 1: latest (session 3) is heavier than session 1 -> current PR
    # exercise 2: latest (session 3) is lighter than session 1 -> not a current PR
    set_logs = [
        _set_log(session_id=1, workout_exercise_id=1, weight=80, reps=5),
        _set_log(session_id=3, workout_exercise_id=1, weight=100, reps=5),
        _set_log(session_id=1, workout_exercise_id=2, weight=90, reps=5),
        _set_log(session_id=3, workout_exercise_id=2, weight=70, reps=5),
    ]

    assert personal_records(set_logs) == 1


def test_personal_records_ignores_sets_with_no_weight() -> None:
    set_logs = [_set_log(session_id=1, workout_exercise_id=1, weight=None, reps=12)]  # type: ignore[arg-type]

    assert personal_records(set_logs) == 0


def test_total_volume_sums_weight_times_reps() -> None:
    set_logs = [
        _set_log(session_id=1, workout_exercise_id=1, weight=100, reps=5),
        _set_log(session_id=1, workout_exercise_id=1, weight=50, reps=10),
    ]

    assert total_volume(set_logs) == 1000.0


def test_total_volume_treats_missing_weight_or_reps_as_zero() -> None:
    set_logs = [_set_log(session_id=1, workout_exercise_id=1, weight=None, reps=10)]  # type: ignore[arg-type]

    assert total_volume(set_logs) == 0.0
