from datetime import datetime

import pytest
from pydantic import ValidationError

from app.schemas.exercise import ExerciseResponse


def _base_kwargs(**overrides: object) -> dict[str, object]:
    kwargs: dict[str, object] = {
        "id": 1,
        "name": "Barbell Back Squat",
        "slug": "barbell-back-squat",
        "movement_slug": "back_squat",
        "body_region": "lower_body",
        "movement_pattern": "squat",
        "primary_muscles": ["quads", "glutes"],
        "secondary_muscles": ["hamstrings"],
        "equipment_tags": ["barbell", "squat_rack"],
        "difficulty_level": "intermediate",
        "instructions": "Squat down.",
        "form_cues": [],
        "safety_notes": None,
        "contraindications": ["knee"],
        "provocation_tags": ["axial_loading"],
        "is_unilateral": False,
        "is_compound": True,
        "created_at": datetime(2026, 1, 1),
        "updated_at": datetime(2026, 1, 1),
    }
    kwargs.update(overrides)
    return kwargs


def test_exercise_response_accepts_valid_tags():
    resp = ExerciseResponse(**_base_kwargs())
    assert resp.is_compound is True
    assert resp.is_unilateral is False


def test_exercise_response_rejects_unknown_equipment_tag():
    with pytest.raises(ValidationError):
        ExerciseResponse(**_base_kwargs(equipment_tags=["not-a-real-tag"]))


def test_exercise_response_rejects_unknown_provocation_tag():
    with pytest.raises(ValidationError):
        ExerciseResponse(**_base_kwargs(provocation_tags=["not-a-real-provocation"]))
