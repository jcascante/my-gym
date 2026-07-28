from typing import cast

from app.models.exercise import Contraindication, Equipment, MovementPattern, Muscle, Provocation

_UNILATERAL_KEYWORDS = (
    "single-leg",
    "single leg",
    "single-arm",
    "single arm",
    "one-arm",
    "one arm",
    "one-leg",
    "one leg",
    "alternating",
    "split squat",
    "step-up",
    "step up",
    "pistol",
    "unilateral",
    "lunge",
)

_NON_COMPOUND_PATTERNS = {
    MovementPattern.ISOLATION,
    MovementPattern.ROTATION,
    MovementPattern.ANTI_ROTATION,
    MovementPattern.MOBILITY,
}

_VALID_EQUIPMENT = {e.value for e in Equipment}
_VALID_MUSCLES = {m.value for m in Muscle}
_VALID_CONTRAINDICATIONS = {c.value for c in Contraindication}

_HEAVY_GRIP_EQUIPMENT = {"barbell", "dumbbells", "kettlebell", "ez_bar", "pull_up_bar", "sandbag"}
_AXIAL_SQUAT_EQUIPMENT = {"barbell", "squat_rack", "smith_machine"}
_HIGH_IMPACT_EQUIPMENT = {"plyo_box", "jump_rope"}
_BALLISTIC_KEYWORDS = ("clean", "snatch", "swing", "push press")
_HIGH_IMPACT_KEYWORDS = ("jump", "sprint", "double-under")
_SPINAL_EXTENSION_KEYWORDS = ("good morning", "hyperextension", "back extension", "superman")
_END_RANGE_SHOULDER_KEYWORDS = ("behind the neck", "behind-the-neck", "upright row")

# Movement-pattern -> provocation tags every exercise of that pattern carries.
# Heuristic first pass (proposal §5.1) - LLM-derived from movement biomechanics,
# not yet human-verified per-exercise; refine as real injury-matching data comes in.
_PATTERN_PROVOCATIONS: dict[MovementPattern, tuple[Provocation, ...]] = {
    MovementPattern.SQUAT: (Provocation.DEEP_KNEE_FLEXION, Provocation.DEEP_HIP_FLEXION),
    MovementPattern.LUNGE: (Provocation.DEEP_KNEE_FLEXION, Provocation.UNILATERAL_LOADING),
    MovementPattern.HINGE: (Provocation.LOADED_SPINAL_FLEXION, Provocation.AXIAL_LOADING),
    MovementPattern.VERTICAL_PUSH: (Provocation.OVERHEAD,),
    MovementPattern.HORIZONTAL_PUSH: (Provocation.WRIST_EXTENSION_LOAD,),
    MovementPattern.CARRY: (Provocation.AXIAL_LOADING,),
}


def classify_exercise(data: dict[str, object]) -> tuple[bool, bool]:
    """Derive (is_unilateral, is_compound) from an exercise's name and movement pattern."""
    name = str(data["name"]).lower()
    is_unilateral = any(keyword in name for keyword in _UNILATERAL_KEYWORDS)
    pattern = MovementPattern[str(data["movement_pattern"])]
    is_compound = pattern not in _NON_COMPOUND_PATTERNS
    return is_unilateral, is_compound


def derive_provocation_tags(data: dict[str, object]) -> list[str]:
    """Heuristic first-pass provocation tags from movement pattern/equipment/name.

    See `_PATTERN_PROVOCATIONS` docstring: this is the "LLM-assisted first pass"
    from the plan, not a per-exercise human-verified annotation.
    """
    name = str(data["name"]).lower()
    pattern = MovementPattern[str(data["movement_pattern"])]
    equipment = set(cast(list[str], data.get("equipment_tags", [])))
    tags = {p.value for p in _PATTERN_PROVOCATIONS.get(pattern, ())}

    if pattern is MovementPattern.SQUAT and equipment & _AXIAL_SQUAT_EQUIPMENT:
        tags.add(Provocation.AXIAL_LOADING.value)
    if pattern in (
        MovementPattern.HINGE,
        MovementPattern.CARRY,
        MovementPattern.HORIZONTAL_PULL,
        MovementPattern.VERTICAL_PULL,
    ):
        if equipment & _HEAVY_GRIP_EQUIPMENT:
            tags.add(Provocation.HEAVY_GRIP.value)

    if any(keyword in name for keyword in _UNILATERAL_KEYWORDS):
        tags.add(Provocation.UNILATERAL_LOADING.value)
    if "overhead" in name:
        tags.add(Provocation.OVERHEAD.value)
    if any(keyword in name for keyword in _BALLISTIC_KEYWORDS):
        tags.add(Provocation.BALLISTIC_LOADING.value)
    if any(keyword in name for keyword in _HIGH_IMPACT_KEYWORDS) or equipment & _HIGH_IMPACT_EQUIPMENT:
        tags.add(Provocation.HIGH_IMPACT.value)
    if any(keyword in name for keyword in _SPINAL_EXTENSION_KEYWORDS):
        tags.add(Provocation.LOADED_SPINAL_EXTENSION.value)
    if any(keyword in name for keyword in _END_RANGE_SHOULDER_KEYWORDS):
        tags.add(Provocation.END_RANGE_SHOULDER_ROTATION.value)

    return sorted(tags)


def validate_tags(data: dict[str, object]) -> None:
    """Raise ValueError if any equipment/muscle/contraindication tag isn't in the canonical vocabulary."""
    invalid_equipment = set(cast(list[str], data.get("equipment_tags", []))) - _VALID_EQUIPMENT
    invalid_primary = set(cast(list[str], data.get("primary_muscles", []))) - _VALID_MUSCLES
    invalid_secondary = set(cast(list[str], data.get("secondary_muscles", []))) - _VALID_MUSCLES
    invalid_contra = set(cast(list[str], data.get("contraindications", []))) - _VALID_CONTRAINDICATIONS
    if invalid_equipment or invalid_primary or invalid_secondary or invalid_contra:
        raise ValueError(
            f"{data.get('slug')}: unrecognized tags - "
            f"equipment_tags={invalid_equipment}, primary_muscles={invalid_primary}, "
            f"secondary_muscles={invalid_secondary}, contraindications={invalid_contra}"
        )
