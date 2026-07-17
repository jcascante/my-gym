from app.schemas.template import TemplateDefinition

DEFAULT_UNDULATING_WAVES: list[dict[str, float]] = [
    {"intensity": 1.0},
    {"intensity": 0.85},
    {"intensity": 1.05},
]


def apply_progression_style(definition: TemplateDefinition, progression_style: str) -> TemplateDefinition:
    """Override a template's progression model based on the user's chosen per-program style.

    "consistent" is a no-op: the template keeps its own declared model (linear_load or
    double_progression, whichever it defines). "variable" forces weekly_undulating,
    injecting a default 3-week load wave when the template's own params don't already
    define one (a template that already picks weekly_undulating keeps its own waves).
    """
    if progression_style != "variable":
        return definition
    params = dict(definition.progression.params)
    params.setdefault("waves", DEFAULT_UNDULATING_WAVES)
    new_progression = definition.progression.model_copy(update={"model_key": "weekly_undulating", "params": params})
    return definition.model_copy(update={"progression": new_progression})
