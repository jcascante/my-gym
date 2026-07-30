"""Pure aggregation logic for the dashboard "Your Stats" cards.

Scoped to a single program (the user's active one) - callers fetch that
program's completed sessions and set logs and pass them in here.
"""

from datetime import date

from app.models.logging import WorkoutSetLog
from app.models.session import WorkoutSession


def workouts_this_month(completed_sessions: list[WorkoutSession], today: date) -> int:
    return sum(
        1
        for session in completed_sessions
        if session.scheduled_date.year == today.year and session.scheduled_date.month == today.month
    )


def current_streak_days(completed_sessions: list[WorkoutSession], today: date) -> int:
    """Consecutive calendar days with a completed session, ending today or yesterday.

    A gap of more than one day between "today" and the most recent completed
    date breaks the streak entirely (yesterday is allowed as a grace day so the
    streak doesn't reset the instant midnight passes, before the user's next
    workout).
    """
    dates = sorted({session.scheduled_date for session in completed_sessions}, reverse=True)
    if not dates or (today - dates[0]).days > 1:
        return 0

    streak = 1
    for later, earlier in zip(dates, dates[1:]):
        if (later - earlier).days == 1:
            streak += 1
        else:
            break
    return streak


def personal_records(set_logs: list[WorkoutSetLog]) -> int:
    """Count of exercises currently at their all-time-best weight.

    An exercise counts if its heaviest ever logged set was logged in the most
    recent session that touched it (session_id increases with scheduled_date
    within a program, same ordering assumption _dedupe_latest_per_set relies on).
    """
    by_exercise: dict[int, list[WorkoutSetLog]] = {}
    for log in set_logs:
        if log.actual_weight is None:
            continue
        by_exercise.setdefault(log.workout_exercise_id, []).append(log)

    count = 0
    for logs in by_exercise.values():
        best_weight = max(log.actual_weight or 0.0 for log in logs)
        latest_session_id = max(log.session_id for log in logs)
        if any(log.session_id == latest_session_id and log.actual_weight == best_weight for log in logs):
            count += 1
    return count


def total_volume(set_logs: list[WorkoutSetLog]) -> float:
    return sum((log.actual_weight or 0) * (log.actual_reps or 0) for log in set_logs)
