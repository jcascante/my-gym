from app.services.program.progression.base import SetScheme
from app.services.program.progression.deload import apply_deload


def test_deload_every_fourth_week():
    s = SetScheme(sets=3, reps=5, load=100.0, rest_seconds=120)
    assert apply_deload(s, week=3, every=4).load == 100.0
    out = apply_deload(s, week=4, every=4)
    assert out.load == 60.0 and out.note == "deload"
    assert apply_deload(s, week=4, every=None).load == 100.0
