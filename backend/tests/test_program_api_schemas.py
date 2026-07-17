import pytest
from pydantic import ValidationError

from app.schemas.program_api import DraftRequest, MatchRequest


def _base_kwargs():
    return dict(environment_id=1, days_per_week=3, session_duration_min=60, fitness_focus="strength")


def test_match_request_defaults():
    r = MatchRequest(
        environment_id=1,
        days_per_week=4,
        session_duration_min=60,
        fitness_focus="strength",
        weight_unit="kg",
        duration_weeks=8,
    )
    assert r.duration_weeks == 8


def test_draft_request_carries_required_inputs():
    r = DraftRequest(
        template_id=2,
        environment_id=1,
        days_per_week=4,
        session_duration_min=60,
        fitness_focus="strength",
        weight_unit="kg",
        duration_weeks=8,
        required_inputs={"squat_start": 80},
    )
    assert r.required_inputs["squat_start"] == 80


def test_draft_request_defaults_to_consistent_progression():
    r = DraftRequest(
        template_id=2,
        environment_id=1,
        days_per_week=4,
        session_duration_min=60,
        fitness_focus="strength",
        weight_unit="kg",
        duration_weeks=8,
    )
    assert r.progression_style.value == "consistent"


def test_draft_request_accepts_variable_progression():
    r = DraftRequest(
        template_id=2,
        environment_id=1,
        days_per_week=4,
        session_duration_min=60,
        fitness_focus="strength",
        weight_unit="kg",
        duration_weeks=8,
        progression_style="variable",
    )
    assert r.progression_style.value == "variable"


def test_draft_request_defaults_effort_method_to_none():
    r = DraftRequest(
        template_id=2,
        environment_id=1,
        days_per_week=4,
        session_duration_min=60,
        fitness_focus="strength",
        weight_unit="kg",
        duration_weeks=8,
    )
    assert r.effort_method is None


def test_draft_request_accepts_percent_1rm_effort_method():
    r = DraftRequest(
        template_id=2,
        environment_id=1,
        days_per_week=4,
        session_duration_min=60,
        fitness_focus="strength",
        weight_unit="kg",
        duration_weeks=8,
        effort_method="percent_1rm",
    )
    assert r.effort_method.value == "percent_1rm"


def test_match_request_defaults_new_signals():
    req = MatchRequest(**_base_kwargs())
    assert req.movement_preferences == {}
    assert req.complementary_focus is True
    assert req.variety_preference.value == "low"
    assert req.progression_style.value == "consistent"


def test_match_request_rejects_out_of_range_movement_preference():
    with pytest.raises(ValidationError):
        MatchRequest(**_base_kwargs(), movement_preferences={"barbell": 2.5})


def test_match_request_accepts_movement_preferences_in_range():
    req = MatchRequest(**_base_kwargs(), movement_preferences={"kettlebell": 1.5, "machine": 0.0})
    assert req.movement_preferences == {"kettlebell": 1.5, "machine": 0.0}


def test_draft_request_inherits_new_signals():
    req = DraftRequest(
        template_id=2,
        environment_id=1,
        days_per_week=4,
        session_duration_min=60,
        fitness_focus="strength",
        weight_unit="kg",
        duration_weeks=8,
        variety_preference="high",
    )
    assert req.variety_preference.value == "high"


def test_match_request_accepts_movement_preferences_at_boundaries():
    req = MatchRequest(**_base_kwargs(), movement_preferences={"barbell": 0.0, "kettlebell": 2.0})
    assert req.movement_preferences == {"barbell": 0.0, "kettlebell": 2.0}


def test_match_request_rejects_negative_movement_preference():
    with pytest.raises(ValidationError):
        MatchRequest(**_base_kwargs(), movement_preferences={"barbell": -0.1})
