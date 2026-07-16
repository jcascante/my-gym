import pytest

from app.db.seed.exercise_classification import classify_exercise, validate_tags
from app.db.seed.exercises import EXERCISE_SEED_DATA


def test_classifies_bilateral_compound_squat():
    data = {"name": "Barbell Back Squat", "movement_pattern": "SQUAT"}
    assert classify_exercise(data) == (False, True)


def test_classifies_unilateral_compound_hinge():
    data = {"name": "Single-Leg Dumbbell Romanian Deadlift", "movement_pattern": "HINGE"}
    assert classify_exercise(data) == (True, True)


def test_classifies_unilateral_compound_row():
    data = {"name": "Single-Arm Dumbbell Row", "movement_pattern": "HORIZONTAL_PULL"}
    assert classify_exercise(data) == (True, True)


def test_classifies_bilateral_isolation_curl():
    data = {"name": "Dumbbell Bicep Curl", "movement_pattern": "ISOLATION"}
    assert classify_exercise(data) == (False, False)


def test_classifies_split_squat_as_unilateral():
    data = {"name": "Bulgarian Split Squat", "movement_pattern": "LUNGE"}
    assert classify_exercise(data) == (True, True)


def test_validate_tags_accepts_known_values():
    validate_tags(
        {
            "slug": "test-ex",
            "equipment_tags": ["barbell", "bench"],
            "primary_muscles": ["chest"],
            "secondary_muscles": ["triceps"],
            "contraindications": ["shoulder"],
        }
    )  # should not raise


def test_validate_tags_rejects_unknown_equipment():
    with pytest.raises(ValueError, match="unknown-equipment"):
        validate_tags(
            {
                "slug": "test-ex",
                "equipment_tags": ["unknown-equipment"],
                "primary_muscles": [],
                "secondary_muscles": [],
                "contraindications": [],
            }
        )


def test_all_seed_exercises_pass_tag_validation():
    for data in EXERCISE_SEED_DATA:
        validate_tags(data)  # should not raise for any of the 148 seeded exercises
