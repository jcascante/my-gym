"""Muscle group taxonomy for volume tracking and program analysis.

This module defines the coarser groupings (15 groups) used by the volume ledger
to aggregate across individual muscle focus areas. It is distinct from
core.constants.ALLOWED_MUSCLE_GROUPS, which is a flat validation allow-list
for the Muscle enum.
"""

from app.models.exercise import Muscle

# 15-group taxonomy covering 21 of 22 Muscle values.
# CARDIO is deliberately excluded because it is not a resistance-trained
# muscle group with MEV/MRV volume landmarks; cardio work is tracked separately.
MUSCLE_GROUPS: dict[str, list[Muscle]] = {
    "chest": [Muscle.CHEST],
    "back": [Muscle.LATS, Muscle.UPPER_BACK],
    "traps": [Muscle.TRAPS],
    "shoulders": [Muscle.SHOULDERS_ANTERIOR, Muscle.SHOULDERS_LATERAL, Muscle.SHOULDERS_POSTERIOR],
    "biceps": [Muscle.BICEPS],
    "triceps": [Muscle.TRICEPS],
    "forearms": [Muscle.FOREARMS],
    "quads": [Muscle.QUADS],
    "hamstrings": [Muscle.HAMSTRINGS],
    "glutes": [Muscle.GLUTES],
    "calves": [Muscle.CALVES],
    "abs": [Muscle.ABS, Muscle.DEEP_CORE],
    "obliques": [Muscle.OBLIQUES],
    "lower_back": [Muscle.LOWER_BACK],
    "hips": [Muscle.HIP_FLEXORS, Muscle.HIP_ABDUCTORS, Muscle.HIP_ADDUCTORS],
}

# Muscles not tracked in the volume ledger (no MEV/MRV landmarks).
UNTRACKED_MUSCLES: frozenset[Muscle] = frozenset({Muscle.CARDIO})

# Role-based volume multipliers: primary muscles get 1.0x volume credit,
# secondary 0.5x. Stabilizer (0.25x) is deferred until the exercise library
# tags stabilizer muscles as a distinct data field.
ROLE_FACTOR: dict[str, float] = {"primary": 1.0, "secondary": 0.5}

# Build reverse mapping at module load time to avoid scanning on every lookup.
_MUSCLE_TO_GROUP: dict[Muscle, str] = {}
for group_name, muscles in MUSCLE_GROUPS.items():
    for muscle in muscles:
        _MUSCLE_TO_GROUP[muscle] = group_name


def muscle_group_for(muscle: Muscle) -> str | None:
    """Returns the taxonomy group for a Muscle, or None if untracked (e.g. CARDIO)."""
    return _MUSCLE_TO_GROUP.get(muscle)
