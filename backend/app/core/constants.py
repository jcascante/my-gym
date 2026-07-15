ALLOWED_EQUIPMENT_TAGS: list[str] = [
    "barbell",
    "squat_rack",
    "dumbbells",
    "kettlebell",
    "resistance_bands",
    "pull_up_bar",
    "bench",
    "cardio_machine",
    "cable_machine",
    "ez_bar",
    "machine",
    "medicine_ball",
    "ab_wheel",
    "sled",
    "none",
]

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
