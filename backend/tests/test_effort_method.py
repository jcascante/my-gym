import pytest

from app.db.seed.program_templates import PROGRAM_TEMPLATE_SEED
from app.schemas.program import EffortMethod
from app.schemas.template import SchemeDef


def test_effort_method_values():
    assert {m.value for m in EffortMethod} == {"rpe", "rir", "borg", "percent_1rm"}


def test_scheme_def_effort_fields_default_to_none():
    scheme = SchemeDef(sets=3, reps_min=8, reps_max=12, rest_seconds=60)
    assert scheme.target_rpe is None
    assert scheme.intensity_pct is None


def test_scheme_def_accepts_effort_fields():
    scheme = SchemeDef(sets=4, reps_min=6, reps_max=8, rest_seconds=120, target_rpe=8.0, intensity_pct=0.8)
    assert scheme.target_rpe == 8.0
    assert scheme.intensity_pct == 0.8


@pytest.mark.parametrize("template", PROGRAM_TEMPLATE_SEED, ids=lambda t: t["slug"])
def test_seed_template_schemes_define_effort_anchors(template):
    schemes = template["split"]["schemes"]
    for key, raw in schemes.items():
        scheme = SchemeDef(**raw)
        assert scheme.target_rpe is not None, f"{template['slug']}.{key} missing target_rpe"
        assert scheme.intensity_pct is not None, f"{template['slug']}.{key} missing intensity_pct"
