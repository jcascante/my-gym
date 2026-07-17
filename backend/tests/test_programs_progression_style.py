import pytest

from app.schemas.template import TemplateDefinition
from app.services.program.drafting import build_draft
from app.services.program.preview import derive_week
from app.services.program.selection import SelectionContext
from app.services.program.style_override import apply_progression_style


@pytest.mark.asyncio
async def test_variable_style_makes_week_to_week_reps_undulate(sample_template_orm, sample_exercises):
    definition = TemplateDefinition.from_orm_template(sample_template_orm)
    ctx = SelectionContext(["barbell", "bench", "squat_rack"], "intermediate", [], set())
    program = build_draft(
        sample_template_orm,
        definition,
        ctx,
        sample_exercises,
        user_id=1,
        environment_id=1,
        days_per_week=3,
        duration_weeks=8,
        weight_unit="kg",
        required_inputs={"squat_start": 80},
        progression_style="variable",
    )
    for w in program.workouts:
        w.id = w.order
        for j, ex in enumerate(w.exercises, 1):
            ex.id = j
    exercise_map = {e.id: e for e in sample_exercises}
    styled_definition = apply_progression_style(definition, program.constraints["progression_style"])
    assert styled_definition.progression.model_key == "weekly_undulating"

    w1 = derive_week(program, styled_definition, 1, exercise_map)
    w2 = derive_week(program, styled_definition, 2, exercise_map)
    load1 = next((s["load"] for d in w1 for s in d["slots"] if s["load"] is not None), None)
    load2 = next((s["load"] for d in w2 for s in d["slots"] if s["load"] is not None), None)
    assert load1 != load2  # intensity wave changes the load, unlike flat linear progression
