from app.services.program.progression.base import SlotBase
from app.services.program.progression.linear_load import LinearLoad


def test_linear_adds_increment_per_week():
    m = LinearLoad()
    base = SlotBase(sets=3, reps_min=5, reps_max=5, rest_seconds=120, base_load=60.0)
    assert m.resolve(base, week=1, params={"increment": 2.5}).load == 60.0
    assert m.resolve(base, week=3, params={"increment": 2.5}).load == 65.0
    assert m.resolve(base, week=1, params={}).reps == 5


def test_linear_handles_no_load():
    m = LinearLoad()
    base = SlotBase(sets=3, reps_min=8, reps_max=8, rest_seconds=90, base_load=None)
    assert m.resolve(base, week=2, params={"increment": 2.5}).load is None
