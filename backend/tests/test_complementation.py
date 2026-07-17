from collections import Counter

from app.services.program.complementation import antagonist_pattern, coverage_deficit, is_core


class _Ex:
    def __init__(self, region):
        self.body_region = type("R", (), {"value": region})


def test_coverage_deficit_uniform_when_session_empty():
    coverage = Counter()
    assert coverage_deficit(["chest"], coverage) == 1.0
    assert coverage_deficit(["lats"], coverage) == 1.0


def test_coverage_deficit_favors_undercovered_muscles():
    coverage = Counter({"chest": 3, "shoulders_anterior": 2})
    undercovered = coverage_deficit(["lats"], coverage)
    overcovered = coverage_deficit(["chest"], coverage)
    assert undercovered > overcovered


def test_coverage_deficit_neutral_when_muscles_empty():
    assert coverage_deficit([], Counter()) == 0.5


def test_is_core_true_for_core_region():
    assert is_core(_Ex("core")) is True
    assert is_core(_Ex("upper_body")) is False


def test_antagonist_pattern_pairs():
    assert antagonist_pattern("horizontal_push") == "horizontal_pull"
    assert antagonist_pattern("horizontal_pull") == "horizontal_push"
    assert antagonist_pattern("squat") == "hinge"
    assert antagonist_pattern("hinge") == "squat"
    assert antagonist_pattern("isolation") is None
