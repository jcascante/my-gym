import pytest

from app.services.program.progression.base import SetScheme, SlotBase, get_model, register


def test_register_and_get():
    class Dummy:
        key = "dummy"

        def resolve(self, base, week, params):
            return SetScheme(
                sets=base.sets, reps=base.reps_min, load=base.base_load, rest_seconds=base.rest_seconds, note=None
            )

    register(Dummy())
    model = get_model("dummy")
    out = model.resolve(SlotBase(sets=3, reps_min=5, reps_max=5, rest_seconds=120, base_load=60.0), week=1, params={})
    assert out.sets == 3 and out.load == 60.0


def test_get_unknown_raises():
    with pytest.raises(KeyError):
        get_model("nope")
