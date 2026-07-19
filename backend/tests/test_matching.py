import math

from app.schemas.template import TemplateDefinition
from app.services.program.engine_config import EngineConfig, EngineFlags, MatchConfig
from app.services.program.matching import (
    ConstraintTemplateScorer,
    MatchInput,
    _gaussian_range_fit,
    _goal_factor,
    rank_templates,
)


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


# _goal_factor tests
def test_goal_factor_single_matching_goal_default_vector():
    """A template whose goal is in the vector sums that goal's weight."""
    assert _goal_factor(["strength"], {"strength": 1.0}) == 1.0


def test_goal_factor_unmatched_goal_is_zero():
    assert _goal_factor(["endurance"], {"strength": 1.0}) == 0.0


def test_goal_factor_multi_goal_vector_sums_matches():
    """Template with two goals sums the vector weights of both."""
    assert abs(_goal_factor(["strength", "hypertrophy"], {"strength": 0.6, "hypertrophy": 0.3}) - 0.9) < 1e-12


def test_goal_factor_ignores_goals_absent_from_vector():
    assert _goal_factor(["strength", "mobility"], {"strength": 0.7}) == 0.7


# ConstraintTemplateScorer tests
def _all_ones_factors() -> dict[str, float]:
    return {
        "goal": 1.0,
        "experience": 1.0,
        "days": 1.0,
        "duration": 1.0,
        "movement_preference": 1.0,
        "focus_complement": 1.0,
        "periodization": 1.0,
    }


def test_constraint_scorer_all_ones_returns_one():
    """soft is a weighted average of factors all equal to 1.0, so soft=1.0;
    fit = 1^1 * 1^1 * 1.0 = 1.0."""
    scorer = ConstraintTemplateScorer(MatchConfig())
    assert abs(scorer.score(_all_ones_factors()) - 1.0) < 1e-12


def test_constraint_scorer_soft_renormalization_math():
    """soft = Σ wᵢ·fᵢ / Σw over the 5 soft keys only."""
    c = MatchConfig()
    factors = _all_ones_factors()
    factors["duration"] = 0.0
    factors["movement_preference"] = 0.0
    factors["focus_complement"] = 0.0
    factors["periodization"] = 0.0
    # only days contributes: soft = (days*1.0)/(days+duration+mp+fc+per)
    weight_sum = c.days + c.duration + c.movement_preference + c.focus_complement + c.periodization
    expected_soft = (c.days * 1.0) / weight_sum
    # goal=experience=1.0 -> fit = soft
    assert abs(ConstraintTemplateScorer(c).score(factors) - expected_soft) < 1e-12


def test_constraint_scorer_fit_formula_with_partial_goal_experience():
    c = MatchConfig()
    factors = _all_ones_factors()
    factors["goal"] = 0.5
    factors["experience"] = 0.3
    # soft = 1.0 (all soft factors 1.0)
    expected = (max(0.5, c.epsilon) ** c.alpha) * (max(0.3, c.epsilon) ** c.beta) * 1.0
    assert abs(ConstraintTemplateScorer(c).score(factors) - expected) < 1e-12


def test_constraint_scorer_epsilon_floor_when_goal_and_experience_zero():
    """When goal and experience are 0, epsilon floor keeps fit positive."""
    c = MatchConfig()
    factors = _all_ones_factors()
    factors["goal"] = 0.0
    factors["experience"] = 0.0
    # soft = 1.0; fit = eps^alpha * eps^beta * 1.0
    expected = (c.epsilon**c.alpha) * (c.epsilon**c.beta)
    assert abs(ConstraintTemplateScorer(c).score(factors) - expected) < 1e-12
    assert ConstraintTemplateScorer(c).score(factors) > 0.0


def test_constraint_scorer_alpha_beta_exponents_applied():
    c = MatchConfig(alpha=2.0, beta=3.0)
    factors = _all_ones_factors()
    factors["goal"] = 0.5
    factors["experience"] = 0.4
    expected = (max(0.5, c.epsilon) ** 2.0) * (max(0.4, c.epsilon) ** 3.0) * 1.0
    assert abs(ConstraintTemplateScorer(c).score(factors) - expected) < 1e-12


# rank_templates config/flag combinations
def _match_input() -> MatchInput:
    return MatchInput("strength", "intermediate", 4, 60, ["barbell"])


def test_config_none_is_legacy_default_path():
    """config=None reproduces the legacy HeuristicTemplateScorer result exactly."""
    templates = [_T(1, "ul", ["strength"], ["intermediate"], 4, 4, 45, 75)]
    inp = _match_input()
    legacy = rank_templates(templates, inp, feasibility={1: True})
    with_none = rank_templates(templates, inp, feasibility={1: True}, config=None)
    assert legacy[0].fit_pct == with_none[0].fit_pct


def test_config_flag_off_matches_legacy_path():
    """A config with use_constraint_scorer=False behaves like config=None."""
    templates = [_T(1, "ul", ["strength"], ["intermediate"], 4, 4, 45, 75)]
    inp = _match_input()
    legacy = rank_templates(templates, inp, feasibility={1: True})
    cfg = EngineConfig(config_version="t", flags=EngineFlags(use_constraint_scorer=False))
    flag_off = rank_templates(templates, inp, feasibility={1: True}, config=cfg)
    assert legacy[0].fit_pct == flag_off[0].fit_pct


def test_config_flag_on_produces_different_fit_pct():
    """Flag on selects the constraint scorer AND the Gaussian kernel, producing a
    genuinely different fit_pct than the legacy path for an out-of-range case."""
    # days out of range (2 vs min 4) so _range_fit and _gaussian_range_fit diverge.
    templates = [_T(1, "ul", ["strength"], ["intermediate"], 4, 4, 45, 75)]
    inp = MatchInput("strength", "intermediate", 2, 60, ["barbell"])
    legacy = rank_templates(templates, inp, feasibility={1: True})
    cfg = EngineConfig(config_version="t", flags=EngineFlags(use_constraint_scorer=True))
    new = rank_templates(templates, inp, feasibility={1: True}, config=cfg)
    assert new[0].fit_pct != legacy[0].fit_pct


def test_config_flag_on_uses_gaussian_kernel_for_days():
    """With the flag on, the days factor is computed by the Gaussian kernel."""
    templates = [_T(1, "ul", ["strength"], ["intermediate"], 2, 2, 45, 75)]
    inp = MatchInput("strength", "intermediate", 4, 60, ["barbell"])
    cfg = EngineConfig(config_version="t", flags=EngineFlags(use_constraint_scorer=True))
    new = rank_templates(templates, inp, feasibility={1: True}, config=cfg)
    expected_days = _gaussian_range_fit(4, 2, 2, sigma=cfg.match.sigma_days)
    assert abs(new[0].factors["days"] - expected_days) < 1e-12


def test_explicit_scorer_wins_over_config_default():
    """An explicitly-passed scorer overrides the config-driven default scorer."""
    templates = [_T(1, "ul", ["strength"], ["intermediate"], 4, 4, 45, 75)]
    inp = _match_input()
    cfg = EngineConfig(config_version="t", flags=EngineFlags(use_constraint_scorer=True))
    # Force the legacy scorer even with the flag on.
    from app.services.program.matching import HeuristicTemplateScorer

    forced = rank_templates(templates, inp, feasibility={1: True}, scorer=HeuristicTemplateScorer(), config=cfg)
    legacy = rank_templates(templates, inp, feasibility={1: True})
    # Same scorer, but note the kernel still switches under flag-on; use in-range days
    # so _range_fit and _gaussian_range_fit both yield 1.0, isolating the scorer choice.
    assert forced[0].fit_pct == legacy[0].fit_pct


def test_goal_vector_generalizes_goal_factor_in_rank():
    """A multi-goal vector feeds through to the goal factor."""
    templates = [_T(1, "ul", ["strength", "hypertrophy"], ["intermediate"], 4, 4, 45, 75)]
    inp = MatchInput("strength", "intermediate", 4, 60, ["barbell"], goal_vector={"strength": 0.5, "hypertrophy": 0.5})
    ranked = rank_templates(templates, inp, feasibility={1: True})
    assert ranked[0].factors["goal"] == 1.0


# Tier derivation tests
def test_tier_for_gap_zero_is_best():
    """Top match has gap=0 -> 'best'."""
    from app.services.program.matching import _tier_for

    assert _tier_for(100, 100) == "best"


def test_tier_for_gap_at_best_boundary_inclusive():
    """Gap exactly 5 is at the boundary, should be 'best' (<=)."""
    from app.services.program.matching import _tier_for

    assert _tier_for(95, 100) == "best"


def test_tier_for_gap_just_beyond_best_is_strong():
    """Gap 6 exceeds best boundary, should be 'strong'."""
    from app.services.program.matching import _tier_for

    assert _tier_for(94, 100) == "strong"


def test_tier_for_gap_at_strong_boundary_inclusive():
    """Gap exactly 15 is at the boundary, should be 'strong' (<=)."""
    from app.services.program.matching import _tier_for

    assert _tier_for(85, 100) == "strong"


def test_tier_for_gap_just_beyond_strong_is_possible():
    """Gap 16 exceeds strong boundary, should be 'possible'."""
    from app.services.program.matching import _tier_for

    assert _tier_for(84, 100) == "possible"


def test_tier_for_large_gap_is_possible():
    """Large gap far beyond strong boundary should be 'possible'."""
    from app.services.program.matching import _tier_for

    assert _tier_for(50, 100) == "possible"


def test_rank_templates_assigns_tiers_relative_to_top():
    """Integration: rank_templates returns matches with tier field,
    computed relative to the list's max fit_pct."""
    templates = [
        _T(1, "best", ["strength"], ["intermediate"], 4, 4, 45, 75),
        _T(2, "strong", ["strength"], ["intermediate"], 4, 4, 45, 75),
        _T(3, "possible", ["strength"], ["intermediate"], 4, 4, 45, 75),
    ]
    inp = MatchInput("strength", "intermediate", 4, 60, ["barbell"])
    ranked = rank_templates(templates, inp, feasibility={1: True, 2: True, 3: True})
    assert len(ranked) == 3
    # The top match is always "best"
    assert ranked[0].tier == "best"
    # Verify all have tiers assigned
    assert all(hasattr(m, "tier") and m.tier in ["best", "strong", "possible"] for m in ranked)


def test_rank_templates_tier_spans_all_tiers():
    """Construct input that produces fit_pct differences spanning all three tiers.

    Under the default HeuristicTemplateScorer (weights: goal=0.25, experience=0.20,
    days=0.12, duration=0.08, movement_preference=0.15, focus_complement=0.12,
    periodization=0.08), templates without a `TemplateDefinition` get fixed neutral
    values for movement_preference/focus_complement/periodization (0.5/0.5/0.3),
    contributing a constant 0.15*0.5 + 0.12*0.5 + 0.08*0.3 = 0.159 to every score.

    days_per_week_min == days_per_week_max == 1 with an input of 4 days drives
    `_range_fit` to exactly 0 (distance=3 > max(low, 1)=1 -> fit is clamped to 0),
    which is used below to knock out the days factor entirely.

    - top: goal=1.0, experience=1.0, days=1.0 (4 in [4,4]), duration=1.0 (60 in [45,75])
      -> score = 0.25 + 0.20 + 0.12 + 0.08 + 0.159 = 0.809 -> fit_pct = 81
    - mid: goal=1.0, experience=1.0, days=0.0 (range [1,1]), duration=1.0
      -> score = 0.25 + 0.20 + 0 + 0.08 + 0.159 = 0.689 -> fit_pct = 69
      -> gap from top = 81 - 69 = 12 -> "strong" (6 < gap <= 15)
    - low: goal=0.0 (endurance goal, strength vector), experience=0.3 (beginner-only,
      input is intermediate), days=0.0 (range [1,1]), duration=1.0
      -> score = 0 + 0.06 + 0 + 0.08 + 0.159 = 0.299 -> fit_pct = 30
      -> gap from top = 81 - 30 = 51 -> "possible" (gap > 15)
    """
    t1 = _T(1, "top", ["strength"], ["intermediate"], 4, 4, 45, 75)
    t2 = _T(2, "mid", ["strength"], ["intermediate"], 1, 1, 45, 75)
    t3 = _T(3, "low", ["endurance"], ["beginner"], 1, 1, 45, 75)

    templates = [t1, t2, t3]
    inp = MatchInput("strength", "intermediate", 4, 60, ["barbell"])
    ranked = rank_templates(templates, inp, feasibility={1: True, 2: True, 3: True})

    by_id = {m.template_id: m for m in ranked}
    assert by_id[1].fit_pct == 81
    assert by_id[2].fit_pct == 69
    assert by_id[3].fit_pct == 30

    assert ranked[0].template_id == 1
    assert ranked[0].tier == "best"

    tiers = [m.tier for m in ranked]
    assert set(tiers) == {"best", "strong", "possible"}
    assert by_id[2].tier == "strong"
    assert by_id[3].tier == "possible"


def test_rank_templates_all_infeasible_path_also_gets_tiers():
    """When all templates are infeasible, the fallback path should also assign tiers."""
    templates = [
        _T(1, "t1", ["strength"], ["intermediate"], 4, 4, 45, 75),
        _T(2, "t2", ["strength"], ["intermediate"], 4, 4, 45, 75),
    ]
    inp = MatchInput("strength", "intermediate", 4, 60, [])  # No equipment: all infeasible
    ranked = rank_templates(templates, inp, feasibility={1: False, 2: False})

    # Even with all_infeasible=True, all should have tier
    assert len(ranked) == 2
    assert all(hasattr(m, "tier") and m.tier in ["best", "strong", "possible"] for m in ranked)
    assert all(m.all_infeasible is True for m in ranked)
