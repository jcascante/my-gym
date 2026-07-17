# backend/tests/test_preferences.py
from app.services.program.preferences import EQUIPMENT_FAMILY, movement_preference_weight


class _Ex:
    def __init__(self, equipment_tags):
        self.equipment_tags = equipment_tags


def test_all_seeded_equipment_tags_have_a_family():
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
    assert seeded <= set(EQUIPMENT_FAMILY.keys())


def test_neutral_weight_when_prefs_empty():
    ex = _Ex(["barbell"])
    assert movement_preference_weight(ex, {}) == 1.0


def test_takes_max_family_weight_among_tags_not_mean():
    ex = _Ex(["barbell", "bench"])  # bench -> bodyweight, left unset -> neutral 1.0
    prefs = {"barbell": 1.8, "bodyweight": 0.2}
    assert movement_preference_weight(ex, prefs) == 1.8


def test_missing_family_in_prefs_is_neutral():
    ex = _Ex(["kettlebell"])
    prefs = {"barbell": 2.0}  # kettlebell family unset
    assert movement_preference_weight(ex, prefs) == 1.0


def test_bodyweight_none_tag_reads_neutral_family_by_default():
    ex = _Ex(["none"])
    assert movement_preference_weight(ex, {"bodyweight": 1.7}) == 1.7
