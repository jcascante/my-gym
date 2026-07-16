from app.services.program.progression.base import SlotBase
from app.services.program.progression.double_progression import DoubleProgression


def test_double_progression_cycle():
    m = DoubleProgression()
    base = SlotBase(sets=3, reps_min=8, reps_max=10, rest_seconds=90, base_load=20.0)
    p = {"increment": 2.5}
    assert (m.resolve(base, 1, p).reps, m.resolve(base, 1, p).load) == (8, 20.0)
    assert (m.resolve(base, 2, p).reps, m.resolve(base, 2, p).load) == (9, 20.0)
    assert (m.resolve(base, 3, p).reps, m.resolve(base, 3, p).load) == (10, 20.0)
    assert (m.resolve(base, 4, p).reps, m.resolve(base, 4, p).load) == (8, 22.5)  # reset + load up
    assert (m.resolve(base, 7, p).reps, m.resolve(base, 7, p).load) == (8, 25.0)
