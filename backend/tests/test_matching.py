import math

from app.schemas.template import TemplateDefinition
from app.services.program.matching import MatchInput, _gaussian_range_fit, rank_templates


class _T:
    def __init__(self, id, slug, goals, exps, dmin, dmax, smin, smax):
        self.id, self.slug, self.name = id, slug, slug
        self.goals, self.experience_levels = goals, exps
        self.days_per_week_min, self.days_per_week_max = dmin, dmax
        self.session_duration_min, self.session_duration_max = smin, smax


def test_goal_and_experience_rank_highest():
    templates = [
        _T(1, "ul", ["strength"], ["intermediate"], 4, 4, 45, 75),
        _T(2, "fb", ["endurance"], ["beginner"], 3, 3, 30, 45),
    ]
    inp = MatchInput("strength", "intermediate", 4, 60, ["barbell"])
    ranked = rank_templates(templates, inp, feasibility={1: True, 2: True})
    assert ranked[0].template_id == 1
    assert ranked[0].fit_pct > ranked[1].fit_pct


def test_infeasible_template_excluded():
    templates = [
        _T(1, "ul", ["strength"], ["intermediate"], 4, 4, 45, 75),
        _T(2, "fb", ["strength"], ["intermediate"], 4, 4, 45, 75),
    ]
    inp = MatchInput("strength", "intermediate", 4, 60, [])
    ranked = rank_templates(templates, inp, feasibility={1: True, 2: False})
    template_ids = [m.template_id for m in ranked]
    assert 1 in template_ids
    assert 2 not in template_ids
    assert all(m.all_infeasible is False for m in ranked)


def test_all_infeasible_returns_best_effort_with_advisory():
    templates = [_T(1, "ul", ["strength"], ["intermediate"], 4, 4, 45, 75)]
    inp = MatchInput("strength", "intermediate", 4, 60, [])
    ranked = rank_templates(templates, inp, feasibility={1: False})
    assert len(ranked) == 1
    assert ranked[0].template_id == 1
    assert ranked[0].all_infeasible is True


def test_multiple_all_infeasible_returns_best_effort_with_advisory():
    templates = [
        _T(1, "ul", ["strength"], ["intermediate"], 4, 4, 45, 75),
        _T(2, "fb", ["endurance"], ["beginner"], 3, 3, 30, 45),
    ]
    inp = MatchInput("strength", "intermediate", 4, 60, [])
    ranked = rank_templates(templates, inp, feasibility={1: False, 2: False})
    assert len(ranked) == 2
    assert all(m.all_infeasible is True for m in ranked)


class _TWithSplit(_T):
    def __init__(self, id, slug, goals, exps, dmin, dmax, smin, smax, split, progression_ref):
        super().__init__(id, slug, goals, exps, dmin, dmax, smin, smax)
        self.split = split
        self.progression_ref = progression_ref
        self.required_inputs = []


def _definition_for(t) -> TemplateDefinition:
    return TemplateDefinition.from_orm_template(t)


def test_missing_definitions_produce_neutral_new_factors_for_every_template():
    templates = [
        _T(1, "ul", ["strength"], ["intermediate"], 4, 4, 45, 75),
        _T(2, "fb", ["endurance"], ["beginner"], 3, 3, 30, 45),
    ]
    inp = MatchInput("strength", "intermediate", 4, 60, ["barbell"])
    ranked = rank_templates(templates, inp, feasibility={1: True, 2: True})
    assert ranked[0].factors["movement_preference"] == 0.5
    assert ranked[0].factors["focus_complement"] == 0.5
    assert ranked[0].factors["periodization"] == 0.3


def test_periodization_rewards_matching_progression_style():
    split = {
        "sessions": [
            {
                "key": "a",
                "name": "A",
                "order": 1,
                "slots": [
                    {"pattern": "squat", "priority": "primary", "scheme": "main"},
                ],
            }
        ],
        "schemes": {"main": {"sets": 3, "reps_min": 5, "reps_max": 5, "rest_seconds": 120}},
    }
    consistent_t = _TWithSplit(
        1,
        "linear",
        ["strength"],
        ["intermediate"],
        4,
        4,
        45,
        75,
        split,
        {"model_key": "linear_load", "params": {}},
    )
    variable_t = _TWithSplit(
        2,
        "undulating",
        ["strength"],
        ["intermediate"],
        4,
        4,
        45,
        75,
        split,
        {"model_key": "weekly_undulating", "params": {}},
    )
    definitions = {1: _definition_for(consistent_t), 2: _definition_for(variable_t)}
    inp = MatchInput("strength", "intermediate", 4, 60, ["barbell"], progression_style="consistent")
    ranked = rank_templates([consistent_t, variable_t], inp, feasibility={1: True, 2: True}, definitions=definitions)
    by_id = {m.template_id: m for m in ranked}
    assert by_id[1].factors["periodization"] == 1.0
    assert by_id[2].factors["periodization"] == 0.3


# Gaussian range kernel tests
def test_gaussian_range_fit_value_inside_range_returns_one():
    """When value is inside [low, high], distance is 0, so exp(0) = 1.0."""
    result = _gaussian_range_fit(50, 40, 60, sigma=1.0)
    assert result == 1.0


def test_gaussian_range_fit_value_below_range():
    """When value is below low, distance = low - value."""
    # value=30, low=40, high=60: d = 40-30 = 10
    # exp(-(10/1.0)^2) = exp(-100) ≈ 0
    result = _gaussian_range_fit(30, 40, 60, sigma=1.0)
    assert result > 0  # Should be very small but positive
    assert result < 0.001  # exp(-100) is tiny


def test_gaussian_range_fit_value_above_range():
    """When value is above high, distance = value - high."""
    # value=70, low=40, high=60: d = 70-60 = 10
    # exp(-(10/1.0)^2) = exp(-100) ≈ 0
    result = _gaussian_range_fit(70, 40, 60, sigma=1.0)
    assert result > 0  # Should be very small but positive
    assert result < 0.001  # exp(-100) is tiny


def test_gaussian_range_fit_never_negative():
    """Result should never be negative; exp is always positive."""
    result = _gaussian_range_fit(0, 40, 60, sigma=1.0)
    assert result >= 0


def test_gaussian_range_fit_larger_sigma_more_tolerant():
    """Larger sigma means the score falls off more slowly."""
    # With sigma=1.0, distance of 5 gives exp(-(5/1)^2) = exp(-25) ≈ 0
    # With sigma=10.0, distance of 5 gives exp(-(5/10)^2) = exp(-0.25) ≈ 0.778
    result_small_sigma = _gaussian_range_fit(35, 40, 60, sigma=1.0)  # d=5
    result_large_sigma = _gaussian_range_fit(35, 40, 60, sigma=10.0)  # d=5
    assert result_large_sigma > result_small_sigma


def test_gaussian_range_fit_smaller_sigma_stricter():
    """Smaller sigma means the score falls off more quickly."""
    # With sigma=5.0, distance of 10 gives exp(-(10/5)^2) = exp(-4) ≈ 0.0183
    # With sigma=10.0, distance of 10 gives exp(-(10/10)^2) = exp(-1) ≈ 0.368
    result_small_sigma = _gaussian_range_fit(30, 40, 60, sigma=5.0)  # d=10
    result_large_sigma = _gaussian_range_fit(30, 40, 60, sigma=10.0)  # d=10
    assert result_small_sigma < result_large_sigma


def test_gaussian_range_fit_concrete_numeric_example():
    """Verify specific numeric behavior."""
    # value=35, low=40, high=60, sigma=2.0: d = 5
    # exp(-(5/2.0)^2) = exp(-6.25) ≈ 0.00193
    result = _gaussian_range_fit(35, 40, 60, sigma=2.0)
    expected = math.exp(-((5 / 2.0) ** 2))
    assert abs(result - expected) < 1e-10


def test_gaussian_range_fit_handles_zero_sigma():
    """When sigma is 0 or negative and d > 0, return 0; when d == 0, return 1.0."""
    # Inside range: d=0, should return 1.0
    result_inside = _gaussian_range_fit(50, 40, 60, sigma=0.0)
    assert result_inside == 1.0
    # Outside range: d>0 with sigma=0, should return 0.0
    result_outside = _gaussian_range_fit(30, 40, 60, sigma=0.0)
    assert result_outside == 0.0
    # Same for negative sigma
    result_outside_neg = _gaussian_range_fit(30, 40, 60, sigma=-1.0)
    assert result_outside_neg == 0.0
