from app.schemas.template import TemplateDefinition
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


def test_infeasible_template_still_ranked():
    templates = [_T(1, "ul", ["strength"], ["intermediate"], 4, 4, 45, 75)]
    inp = MatchInput("strength", "intermediate", 4, 60, [])
    ranked = rank_templates(templates, inp, feasibility={1: False})
    assert len(ranked) == 1
    assert ranked[0].template_id == 1


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
