# backend/app/services/program/preferences.py
import enum

from app.models.exercise import Exercise


class EquipmentFamily(str, enum.Enum):
    BARBELL = "barbell"
    DUMBBELL = "dumbbell"
    KETTLEBELL = "kettlebell"
    MACHINE = "machine"
    CABLE = "cable"
    BODYWEIGHT = "bodyweight"
    BANDS = "bands"


EQUIPMENT_FAMILY: dict[str, EquipmentFamily] = {
    "barbell": EquipmentFamily.BARBELL,
    "ez_bar": EquipmentFamily.BARBELL,
    "dumbbells": EquipmentFamily.DUMBBELL,
    "kettlebell": EquipmentFamily.KETTLEBELL,
    "cable_machine": EquipmentFamily.CABLE,
    "resistance_bands": EquipmentFamily.BANDS,
    "none": EquipmentFamily.BODYWEIGHT,
    "bench": EquipmentFamily.BODYWEIGHT,
    "squat_rack": EquipmentFamily.BODYWEIGHT,
    "pull_up_bar": EquipmentFamily.BODYWEIGHT,
    "gymnastic_rings": EquipmentFamily.BODYWEIGHT,
    "ab_wheel": EquipmentFamily.BODYWEIGHT,
    "plyo_box": EquipmentFamily.BODYWEIGHT,
    "jump_rope": EquipmentFamily.BODYWEIGHT,
    "battle_ropes": EquipmentFamily.BODYWEIGHT,
    "medicine_ball": EquipmentFamily.BODYWEIGHT,
    "sandbag": EquipmentFamily.BODYWEIGHT,
    "assisted_dip_machine": EquipmentFamily.MACHINE,
    "assisted_pullup_machine": EquipmentFamily.MACHINE,
    "calf_raise_machine": EquipmentFamily.MACHINE,
    "chest_press_machine": EquipmentFamily.MACHINE,
    "hack_squat_machine": EquipmentFamily.MACHINE,
    "hip_abduction_machine": EquipmentFamily.MACHINE,
    "hip_adduction_machine": EquipmentFamily.MACHINE,
    "lat_pulldown_machine": EquipmentFamily.MACHINE,
    "leg_curl_machine": EquipmentFamily.MACHINE,
    "leg_extension_machine": EquipmentFamily.MACHINE,
    "leg_press_machine": EquipmentFamily.MACHINE,
    "pec_deck_machine": EquipmentFamily.MACHINE,
    "seated_row_machine": EquipmentFamily.MACHINE,
    "shoulder_press_machine": EquipmentFamily.MACHINE,
    "rowing_machine": EquipmentFamily.MACHINE,
    "stair_climber": EquipmentFamily.MACHINE,
    "stationary_bike": EquipmentFamily.MACHINE,
    "treadmill": EquipmentFamily.MACHINE,
    "assault_bike": EquipmentFamily.MACHINE,
    "sled": EquipmentFamily.MACHINE,
    "smith_machine": EquipmentFamily.MACHINE,
}


def movement_preference_weight(ex: Exercise, prefs: dict[str, float]) -> float:
    if not prefs:
        return 1.0
    weights = []
    for tag in ex.equipment_tags:
        family = EQUIPMENT_FAMILY.get(tag)
        if family is not None:
            weights.append(prefs.get(family.value, 1.0))
    return max(weights) if weights else 1.0
