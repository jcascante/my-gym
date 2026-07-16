from app.services.program.progression.base import SlotBase
from app.services.program.progression.weekly_undulating import WeeklyUndulating


def test_undulating_rotates_waves():
    m = WeeklyUndulating()
    base = SlotBase(sets=4, reps_min=5, reps_max=12, rest_seconds=120, base_load=100.0)
    p = {"waves": [{"reps": 5, "intensity": 1.0}, {"reps": 12, "intensity": 0.7}], "increment": 5.0}
    assert (m.resolve(base, 1, p).reps, m.resolve(base, 1, p).load) == (5, 100.0)
    assert (m.resolve(base, 2, p).reps, m.resolve(base, 2, p).load) == (12, 70.0)
    assert m.resolve(base, 3, p).reps == 5  # new cycle
    assert m.resolve(base, 3, p).load == 105.0  # +increment after one full wave
