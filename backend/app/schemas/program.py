import enum
from datetime import date

from pydantic import BaseModel, ConfigDict


class FocusArea(str, enum.Enum):
    PUSH = "push"
    PULL = "pull"
    LEGS = "legs"
    CORE = "core"
    CARDIO = "cardio"
    FLEXIBILITY = "flexibility"
    FULL_BODY = "full_body"


class WeightUnit(str, enum.Enum):
    KG = "kg"
    LBS = "lbs"


class ProgressionStyle(str, enum.Enum):
    CONSISTENT = "consistent"
    VARIABLE = "variable"


class EffortMethod(str, enum.Enum):
    RPE = "rpe"
    RIR = "rir"
    BORG = "borg"
    PERCENT_1RM = "percent_1rm"


class VarietyPreference(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class DayOfWeek(str, enum.Enum):
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"


class ProgramCreationRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    environment_id: int
    days_per_week: int
    preferred_days: list[DayOfWeek]
    session_duration_min: int
    start_date: date
    focus_areas: list[FocusArea] = []
    weight_unit: WeightUnit
    available_weight_increments: list[float] = []
    progression_style: ProgressionStyle
    movement_preferences: dict[str, float] = {}
    complementary_focus: bool = True
    variety_preference: VarietyPreference = VarietyPreference.LOW
