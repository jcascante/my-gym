from app.services.program.variety import pool_size_for, rotation_pool_ids


class _Ex:
    def __init__(self, id):
        self.id = id


def test_pool_size_for_each_variety_level():
    assert pool_size_for("low") == 1
    assert pool_size_for("medium") == 2
    assert pool_size_for("high") == 3


def test_pool_size_defaults_to_one_for_unknown_level():
    assert pool_size_for("bogus") == 1


def test_rotation_pool_ids_takes_top_n():
    ranked = [_Ex(1), _Ex(2), _Ex(3), _Ex(4)]
    assert rotation_pool_ids(ranked, 2) == [1, 2]


def test_rotation_pool_ids_handles_pool_smaller_than_n():
    ranked = [_Ex(1)]
    assert rotation_pool_ids(ranked, 3) == [1]
