import pytest

from app.core.constants import ALLOWED_PROVOCATION_TAGS
from app.db.seed.exercise_classification import classify_exercise, derive_provocation_tags, validate_tags
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


def test_derives_deep_knee_and_hip_flexion_for_squat():
    data = {"name": "Barbell Back Squat", "movement_pattern": "SQUAT", "equipment_tags": ["barbell", "squat_rack"]}
    tags = derive_provocation_tags(data)
    assert "deep_knee_flexion" in tags
    assert "deep_hip_flexion" in tags
    assert "axial_loading" in tags


def test_squat_without_axial_equipment_has_no_axial_loading():
    data = {"name": "Bodyweight Squat", "movement_pattern": "SQUAT", "equipment_tags": ["none"]}
    assert "axial_loading" not in derive_provocation_tags(data)


def test_derives_spinal_flexion_and_grip_for_barbell_hinge():
    data = {"name": "Barbell Deadlift", "movement_pattern": "HINGE", "equipment_tags": ["barbell"]}
    tags = derive_provocation_tags(data)
    assert "loaded_spinal_flexion" in tags
    assert "axial_loading" in tags
    assert "heavy_grip" in tags


def test_derives_unilateral_loading_from_name_keyword():
    data = {
        "name": "Single-Leg Dumbbell Romanian Deadlift",
        "movement_pattern": "HINGE",
        "equipment_tags": ["dumbbells"],
    }
    assert "unilateral_loading" in derive_provocation_tags(data)


def test_derives_overhead_for_vertical_push():
    data = {"name": "Barbell Overhead Press", "movement_pattern": "VERTICAL_PUSH", "equipment_tags": ["barbell"]}
    assert "overhead" in derive_provocation_tags(data)


def test_derives_ballistic_loading_from_name_keyword():
    data = {"name": "Kettlebell Swing", "movement_pattern": "HINGE", "equipment_tags": ["kettlebell"]}
    assert "ballistic_loading" in derive_provocation_tags(data)


def test_derives_high_impact_from_equipment():
    data = {"name": "Box Jump", "movement_pattern": "LOCOMOTION", "equipment_tags": ["plyo_box"]}
    assert "high_impact" in derive_provocation_tags(data)


def test_derives_no_tags_for_neutral_isolation_movement():
    data = {"name": "Dumbbell Bicep Curl", "movement_pattern": "ISOLATION", "equipment_tags": ["dumbbells"]}
    assert derive_provocation_tags(data) == []


def test_derive_provocation_tags_output_is_always_in_allowed_vocabulary():
    allowed = set(ALLOWED_PROVOCATION_TAGS)
    for data in EXERCISE_SEED_DATA:
        assert set(derive_provocation_tags(data)) <= allowed
