"""Property test: goal-mismatch never outranks goal-match within soft-score 0.3
(plan Section 1.8, design decision #4).

This is specifically a property of `ConstraintTemplateScorer`'s multiplicative
`fit = max(goal, eps)^alpha * max(experience, eps)^beta * soft` formula (Task 4): a
mismatched goal (goal factor floored to `epsilon`) should never let a template
outrank one with a matched goal (goal factor 1.0) when their `soft` scores are close
(within 0.3).

Verified with synthetic templates (the `_T`-style test-double pattern from
`test_matching.py`) rather than the real 4-template catalog, so the soft-score gap
between the two templates is deliberately constructed and controlled, not hoped for.
"""

from __future__ import annotations

from app.services.program.engine_config import EngineConfig, EngineFlags, MatchConfig
from app.services.program.matching import MatchInput, rank_templates


class _T:
    """Same minimal ORM-shaped test double `test_matching.py` uses: only the
    attributes `rank_templates`/`ConstraintTemplateScorer` actually read."""

    def __init__(
        self,
        id: int,
        slug: str,
        goals: list[str],
        exps: list[str],
        dmin: int,
        dmax: int,
        smin: int,
        smax: int,
    ) -> None:
        self.id, self.slug, self.name = id, slug, slug
        self.goals, self.experience_levels = goals, exps
        self.days_per_week_min, self.days_per_week_max = dmin, dmax
        self.session_duration_min, self.session_duration_max = smin, smax


def _soft_score(factors: dict[str, float], cfg: MatchConfig) -> float:
    """Recomputes `ConstraintTemplateScorer`'s `soft` term independently of the scorer,
    from the `factors` dict `rank_templates` returns on each `TemplateMatch` -- used
    here only to assert the near-tie precondition, not as part of the scorer itself."""
    weight_sum = cfg.days + cfg.duration + cfg.movement_preference + cfg.focus_complement + cfg.periodization
    return (
        cfg.days * factors["days"]
        + cfg.duration * factors["duration"]
        + cfg.movement_preference * factors["movement_preference"]
        + cfg.focus_complement * factors["focus_complement"]
        + cfg.periodization * factors["periodization"]
    ) / weight_sum


def test_goal_mismatch_never_outranks_goal_match_within_soft_tolerance() -> None:
    # Both templates match the input's experience level and duration range, isolating
    # the goal factor. `matched`'s days range (20-20) is far outside the input's 4
    # days/week, driving its Gaussian days factor near 0 and its soft score DOWN.
    # `mismatched`'s days range (4-4) is exact, driving its soft score UP -- a
    # deliberately constructed near-tie in soft score that favors the mismatched
    # template, so the goal factor is the only thing that can save the ordering.
    matched = _T(1, "matched", ["strength"], ["intermediate"], 20, 20, 45, 75)
    mismatched = _T(2, "mismatched", ["endurance"], ["intermediate"], 4, 4, 45, 75)

    inp = MatchInput(
        fitness_focus="strength",
        experience_level="intermediate",
        days_per_week=4,
        session_duration_min=60,
        environment_equipment=["barbell"],
    )
    cfg = EngineConfig(
        config_version="harness-goal-mismatch",
        flags=EngineFlags(use_constraint_scorer=True),
    )

    ranked = rank_templates([matched, mismatched], inp, feasibility={1: True, 2: True}, config=cfg)
    by_id = {m.template_id: m for m in ranked}

    soft_matched = _soft_score(by_id[1].factors, cfg.match)
    soft_mismatched = _soft_score(by_id[2].factors, cfg.match)
    soft_gap = abs(soft_matched - soft_mismatched)
    assert soft_gap <= 0.3, f"test precondition failed: soft scores are not a near-tie (gap={soft_gap})"
    # Sanity: the near-tie deliberately favors the mismatched template on soft score,
    # so a passing goal-mismatch property below isn't just "both templates tied".
    assert soft_mismatched > soft_matched

    assert by_id[1].factors["goal"] == 1.0
    assert by_id[2].factors["goal"] == 0.0

    assert by_id[1].fit_pct >= by_id[2].fit_pct
