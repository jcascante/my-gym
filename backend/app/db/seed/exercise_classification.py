from typing import cast

from app.models.exercise import Contraindication, Equipment, MovementPattern, Muscle

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


def classify_exercise(data: dict[str, object]) -> tuple[bool, bool]:
    """Derive (is_unilateral, is_compound) from an exercise's name and movement pattern."""
    name = str(data["name"]).lower()
    is_unilateral = any(keyword in name for keyword in _UNILATERAL_KEYWORDS)
    pattern = MovementPattern[str(data["movement_pattern"])]
    is_compound = pattern not in _NON_COMPOUND_PATTERNS
    return is_unilateral, is_compound


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
