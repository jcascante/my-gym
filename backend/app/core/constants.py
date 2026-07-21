EQUIPMENT_CATEGORIES: dict[str, list[str]] = {
    "free_weights": ["barbell", "ez_bar", "dumbbells", "kettlebell", "medicine_ball"],
    "machines": [
        "cable_machine",
        "smith_machine",
        "leg_press_machine",
        "hack_squat_machine",
        "chest_press_machine",
        "shoulder_press_machine",
        "seated_row_machine",
        "assisted_dip_machine",
        "assisted_pullup_machine",
        "calf_raise_machine",
        "leg_extension_machine",
        "leg_curl_machine",
        "hip_abduction_machine",
        "hip_adduction_machine",
        "lat_pulldown_machine",
        "pec_deck_machine",
    ],
    "racks_and_benches": ["squat_rack", "bench"],
    "cardio": ["treadmill", "stationary_bike", "rowing_machine", "stair_climber", "assault_bike"],
    "bodyweight_and_accessories": [
        "pull_up_bar",
        "resistance_bands",
        "ab_wheel",
        "gymnastic_rings",
        "plyo_box",
        "jump_rope",
        "battle_ropes",
        "sandbag",
        "sled",
        "none",
    ],
}

# Flattened for validation (schemas/training_environment.py) - derived so the
# categorized dict above stays the single source of truth.
ALLOWED_EQUIPMENT_TAGS: list[str] = [tag for tags in EQUIPMENT_CATEGORIES.values() for tag in tags]

# Typical equipment per training environment archetype. Used to prefill and
# narrow the equipment picker so users aren't shown the full catalog by
# default. "other" is intentionally empty - it signals "show everything."
ENVIRONMENT_TYPE_EQUIPMENT_PRESETS: dict[str, list[str]] = {
    "commercial_gym": [
        "barbell",
        "ez_bar",
        "dumbbells",
        "kettlebell",
        "medicine_ball",
        "cable_machine",
        "smith_machine",
        "leg_press_machine",
        "hack_squat_machine",
        "chest_press_machine",
        "shoulder_press_machine",
        "seated_row_machine",
        "assisted_dip_machine",
        "assisted_pullup_machine",
        "calf_raise_machine",
        "leg_extension_machine",
        "leg_curl_machine",
        "hip_abduction_machine",
        "hip_adduction_machine",
        "lat_pulldown_machine",
        "pec_deck_machine",
        "squat_rack",
        "bench",
        "treadmill",
        "stationary_bike",
        "rowing_machine",
        "stair_climber",
        "assault_bike",
        "pull_up_bar",
        "resistance_bands",
        "none",
        "ab_wheel",
    ],
    "home": ["dumbbells", "kettlebell", "resistance_bands", "bench", "pull_up_bar", "none", "ab_wheel"],
    "bodyweight": ["none", "pull_up_bar", "resistance_bands"],
    "crossfit_box": [
        "barbell",
        "squat_rack",
        "kettlebell",
        "medicine_ball",
        "pull_up_bar",
        "gymnastic_rings",
        "plyo_box",
        "jump_rope",
        "battle_ropes",
        "sandbag",
        "sled",
        "rowing_machine",
        "assault_bike",
        "none",
    ],
    "powerlifting_gym": ["barbell", "squat_rack", "bench", "ez_bar", "sled", "none", "pull_up_bar"],
    "strength_gym": [
        "barbell",
        "squat_rack",
        "bench",
        "dumbbells",
        "kettlebell",
        "pull_up_bar",
        "resistance_bands",
        "none",
    ],
    "other": [],
}

# Muscle groups organized by body region for clarity
ALLOWED_MUSCLE_GROUPS: list[str] = [
    # Upper body
    "chest",
    "upper_back",
    "lats",
    "traps",
    "shoulders_anterior",
    "shoulders_lateral",
    "shoulders_posterior",
    "biceps",
    "triceps",
    "forearms",
    # Lower body
    "quads",
    "hamstrings",
    "glutes",
    "calves",
    "hip_flexors",
    "hip_abductors",
    "hip_adductors",
    # Core
    "abs",
    "obliques",
    "lower_back",
    "deep_core",
    # Full body / cardio
    "cardio",
]

ALLOWED_CONTRAINDICATION_TAGS: list[str] = [
    "knee",
    "shoulder",
    "lower_back",
    "wrist",
    "elbow",
    "hip",
    "neck",
    "ankle",
]

# Mirrors app.models.exercise.Provocation - shared vocabulary between
# Exercise.provocation_tags and InjuryRecord.provocations so the two can be
# matched against each other (Phase 3.2+).
ALLOWED_PROVOCATION_TAGS: list[str] = [
    "overhead",
    "loaded_spinal_flexion",
    "loaded_spinal_extension",
    "axial_loading",
    "deep_knee_flexion",
    "deep_hip_flexion",
    "heavy_grip",
    "high_impact",
    "ballistic_loading",
    "end_range_shoulder_rotation",
    "wrist_extension_load",
    "unilateral_loading",
]
