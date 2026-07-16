from app.models.exercise import Contraindication, Equipment, Exercise, Muscle


def test_equipment_enum_covers_all_seeded_values():
    seeded = {
        "ab_wheel",
        "assault_bike",
        "assisted_dip_machine",
        "assisted_pullup_machine",
        "barbell",
        "battle_ropes",
        "bench",
        "cable_machine",
        "calf_raise_machine",
        "chest_press_machine",
        "dumbbells",
        "ez_bar",
        "gymnastic_rings",
        "hack_squat_machine",
        "hip_abduction_machine",
        "hip_adduction_machine",
        "jump_rope",
        "kettlebell",
        "lat_pulldown_machine",
        "leg_curl_machine",
        "leg_extension_machine",
        "leg_press_machine",
        "medicine_ball",
        "none",
        "pec_deck_machine",
        "plyo_box",
        "pull_up_bar",
        "resistance_bands",
        "rowing_machine",
        "sandbag",
        "seated_row_machine",
        "shoulder_press_machine",
        "sled",
        "smith_machine",
        "squat_rack",
        "stair_climber",
        "stationary_bike",
        "treadmill",
    }
    assert seeded <= {e.value for e in Equipment}


def test_muscle_enum_covers_all_seeded_values():
    seeded = {
        "abs",
        "biceps",
        "calves",
        "cardio",
        "chest",
        "deep_core",
        "forearms",
        "glutes",
        "hamstrings",
        "hip_abductors",
        "hip_adductors",
        "hip_flexors",
        "lats",
        "lower_back",
        "obliques",
        "quads",
        "shoulders_anterior",
        "shoulders_lateral",
        "shoulders_posterior",
        "traps",
        "triceps",
        "upper_back",
    }
    assert seeded <= {m.value for m in Muscle}


def test_contraindication_enum_covers_all_seeded_values():
    seeded = {"ankle", "elbow", "hip", "knee", "lower_back", "neck", "shoulder", "wrist"}
    assert seeded <= {c.value for c in Contraindication}


def test_exercise_has_unilateral_and_compound_flags():
    columns = Exercise.__table__.columns
    assert "is_unilateral" in columns
    assert "is_compound" in columns
    assert columns["is_unilateral"].nullable is False
    assert columns["is_compound"].nullable is False
