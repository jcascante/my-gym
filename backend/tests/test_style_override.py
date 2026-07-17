from app.schemas.template import ProgressionRef, SchemeDef, SessionDef, SlotRule, SplitDef, TemplateDefinition
from app.services.program.style_override import apply_progression_style


def _definition(model_key: str, params: dict[str, object]) -> TemplateDefinition:
    return TemplateDefinition(
        split=SplitDef(
            sessions=[SessionDef(key="a", name="A", order=1, slots=[SlotRule(pattern="squat", scheme="main")])]
        ),
        progression=ProgressionRef(model_key=model_key, params=params, deload_every=4),
        schemes={"main": SchemeDef(sets=3, reps_min=5, reps_max=5, rest_seconds=120)},
    )


def test_consistent_leaves_template_model_unchanged():
    original = _definition("linear_load", {"increment": 2.5})
    result = apply_progression_style(original, "consistent")
    assert result.progression.model_key == "linear_load"
    assert result.progression.params == {"increment": 2.5}


def test_consistent_preserves_double_progression_model():
    original = _definition("double_progression", {"increment": 0})
    result = apply_progression_style(original, "consistent")
    assert result.progression.model_key == "double_progression"


def test_variable_forces_weekly_undulating_with_default_waves():
    original = _definition("linear_load", {"increment": 2.5})
    result = apply_progression_style(original, "variable")
    assert result.progression.model_key == "weekly_undulating"
    assert result.progression.params["waves"] == [
        {"intensity": 1.0},
        {"intensity": 0.85},
        {"intensity": 1.05},
    ]
    assert result.progression.deload_every == 4  # untouched


def test_variable_keeps_templates_own_waves_if_defined():
    original = _definition("weekly_undulating", {"waves": [{"reps": 5, "intensity": 1.0}]})
    result = apply_progression_style(original, "variable")
    assert result.progression.params["waves"] == [{"reps": 5, "intensity": 1.0}]


def test_original_definition_is_not_mutated():
    original = _definition("linear_load", {"increment": 2.5})
    apply_progression_style(original, "variable")
    assert original.progression.model_key == "linear_load"
