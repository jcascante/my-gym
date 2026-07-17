from app.schemas.program_api import DraftRequest, MatchRequest


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
