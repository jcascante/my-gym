import pytest
from pydantic import ValidationError

from app.schemas.template import SlotRule, SplitDef, TemplateDefinition


def test_slot_rule_requires_pattern_or_region():
    with pytest.raises(ValidationError):
        SlotRule(priority="primary", scheme="main")  # neither pattern nor region


def test_valid_template_definition_parses():
    td = TemplateDefinition(
        split=SplitDef(
            sessions=[
                {
                    "key": "upper_a",
                    "name": "Upper A",
                    "order": 1,
                    "slots": [{"pattern": "horizontal_push", "priority": "primary", "scheme": "main"}],
                }
            ]
        ),
        progression={"model_key": "linear_load", "params": {}},
        schemes={"main": {"sets": 3, "reps_min": 5, "reps_max": 5, "rest_seconds": 120}},
        required_inputs=[],
    )
    assert td.split.sessions[0].slots[0].pattern == "horizontal_push"
