from datetime import date

import pytest
from pydantic import ValidationError

from app.schemas.session import ScheduleEntryOut, SessionSetLogCreate


def test_schedule_entry_round_trips() -> None:
    entry = ScheduleEntryOut(
        session_id=1,
        scheduled_date=date(2026, 7, 27),
        week=1,
        status="scheduled",
        workout_id=4,
        workout_name="Upper Body A",
        exercise_count=5,
        duration_min=45,
    )

    assert entry.model_dump()["scheduled_date"] == date(2026, 7, 27)


def test_session_set_log_does_not_take_a_workout_id() -> None:
    log = SessionSetLogCreate(workout_exercise_id=3, set_number=1, actual_reps=8, actual_rpe=8.0)

    assert "workout_id" not in log.model_dump()


def test_session_set_log_rejects_a_bad_rpe() -> None:
    with pytest.raises(ValidationError):
        SessionSetLogCreate(workout_exercise_id=3, set_number=1, actual_rpe=99.0)


def test_session_set_log_rejects_rpe_below_range() -> None:
    with pytest.raises(ValidationError):
        SessionSetLogCreate(workout_exercise_id=3, set_number=1, actual_rpe=0.0)


def test_session_set_log_rejects_rpe_above_range() -> None:
    with pytest.raises(ValidationError):
        SessionSetLogCreate(workout_exercise_id=3, set_number=1, actual_rpe=11.0)


def test_session_set_log_accepts_rpe_range() -> None:
    for rpe in [1.0, 5.0, 10.0]:
        log = SessionSetLogCreate(workout_exercise_id=3, set_number=1, actual_rpe=rpe)
        assert log.actual_rpe == rpe
