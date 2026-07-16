from app.services.program.matching import MatchInput, rank_templates


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
    templates = [_T(1, "ul", ["strength"], ["intermediate"], 4, 4, 45, 75)]
    inp = MatchInput("strength", "intermediate", 4, 60, [])
    assert rank_templates(templates, inp, feasibility={1: False}) == []
