import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.user import ExperienceLevel, _utcnow

if TYPE_CHECKING:
    pass


class BodyRegion(str, enum.Enum):
    UPPER_BODY = "upper_body"
    LOWER_BODY = "lower_body"
    CORE = "core"
    FULL_BODY = "full_body"


class MovementPattern(str, enum.Enum):
    SQUAT = "squat"
    HINGE = "hinge"
    LUNGE = "lunge"
    HORIZONTAL_PUSH = "horizontal_push"
    VERTICAL_PUSH = "vertical_push"
    HORIZONTAL_PULL = "horizontal_pull"
    VERTICAL_PULL = "vertical_pull"
    ROTATION = "rotation"
    ANTI_ROTATION = "anti_rotation"
    CARRY = "carry"
    ISOLATION = "isolation"
    LOCOMOTION = "locomotion"
    MOBILITY = "mobility"


class Equipment(str, enum.Enum):
    AB_WHEEL = "ab_wheel"
    ASSAULT_BIKE = "assault_bike"
    ASSISTED_DIP_MACHINE = "assisted_dip_machine"
    ASSISTED_PULLUP_MACHINE = "assisted_pullup_machine"
    BARBELL = "barbell"
    BATTLE_ROPES = "battle_ropes"
    BENCH = "bench"
    CABLE_MACHINE = "cable_machine"
    CALF_RAISE_MACHINE = "calf_raise_machine"
    CHEST_PRESS_MACHINE = "chest_press_machine"
    DUMBBELLS = "dumbbells"
    EZ_BAR = "ez_bar"
    GYMNASTIC_RINGS = "gymnastic_rings"
    HACK_SQUAT_MACHINE = "hack_squat_machine"
    HIP_ABDUCTION_MACHINE = "hip_abduction_machine"
    HIP_ADDUCTION_MACHINE = "hip_adduction_machine"
    JUMP_ROPE = "jump_rope"
    KETTLEBELL = "kettlebell"
    LAT_PULLDOWN_MACHINE = "lat_pulldown_machine"
    LEG_CURL_MACHINE = "leg_curl_machine"
    LEG_EXTENSION_MACHINE = "leg_extension_machine"
    LEG_PRESS_MACHINE = "leg_press_machine"
    MEDICINE_BALL = "medicine_ball"
    NONE = "none"
    PEC_DECK_MACHINE = "pec_deck_machine"
    PLYO_BOX = "plyo_box"
    PULL_UP_BAR = "pull_up_bar"
    RESISTANCE_BANDS = "resistance_bands"
    ROWING_MACHINE = "rowing_machine"
    SANDBAG = "sandbag"
    SEATED_ROW_MACHINE = "seated_row_machine"
    SHOULDER_PRESS_MACHINE = "shoulder_press_machine"
    SLED = "sled"
    SMITH_MACHINE = "smith_machine"
    SQUAT_RACK = "squat_rack"
    STAIR_CLIMBER = "stair_climber"
    STATIONARY_BIKE = "stationary_bike"
    TREADMILL = "treadmill"


class Muscle(str, enum.Enum):
    ABS = "abs"
    BICEPS = "biceps"
    CALVES = "calves"
    CARDIO = "cardio"
    CHEST = "chest"
    DEEP_CORE = "deep_core"
    FOREARMS = "forearms"
    GLUTES = "glutes"
    HAMSTRINGS = "hamstrings"
    HIP_ABDUCTORS = "hip_abductors"
    HIP_ADDUCTORS = "hip_adductors"
    HIP_FLEXORS = "hip_flexors"
    LATS = "lats"
    LOWER_BACK = "lower_back"
    OBLIQUES = "obliques"
    QUADS = "quads"
    SHOULDERS_ANTERIOR = "shoulders_anterior"
    SHOULDERS_LATERAL = "shoulders_lateral"
    SHOULDERS_POSTERIOR = "shoulders_posterior"
    TRAPS = "traps"
    TRICEPS = "triceps"
    UPPER_BACK = "upper_back"


class Contraindication(str, enum.Enum):
    ANKLE = "ankle"
    ELBOW = "elbow"
    HIP = "hip"
    KNEE = "knee"
    LOWER_BACK = "lower_back"
    NECK = "neck"
    SHOULDER = "shoulder"
    WRIST = "wrist"


class Provocation(str, enum.Enum):
    """Movement/loading demands that can aggravate a matching InjuryRecord.provocations
    entry (proposal §5.1) - finer-grained than the region-level Contraindication tags."""

    OVERHEAD = "overhead"
    LOADED_SPINAL_FLEXION = "loaded_spinal_flexion"
    LOADED_SPINAL_EXTENSION = "loaded_spinal_extension"
    AXIAL_LOADING = "axial_loading"
    DEEP_KNEE_FLEXION = "deep_knee_flexion"
    DEEP_HIP_FLEXION = "deep_hip_flexion"
    HEAVY_GRIP = "heavy_grip"
    HIGH_IMPACT = "high_impact"
    BALLISTIC_LOADING = "ballistic_loading"
    END_RANGE_SHOULDER_ROTATION = "end_range_shoulder_rotation"
    WRIST_EXTENSION_LOAD = "wrist_extension_load"
    UNILATERAL_LOADING = "unilateral_loading"


class Exercise(Base):
    __tablename__ = "exercises"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    movement_slug: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    body_region: Mapped[BodyRegion] = mapped_column(Enum(BodyRegion), nullable=False)
    movement_pattern: Mapped[MovementPattern] = mapped_column(Enum(MovementPattern), nullable=False)
    primary_muscles: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    secondary_muscles: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    equipment_tags: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    difficulty_level: Mapped[ExperienceLevel] = mapped_column(Enum(ExperienceLevel), nullable=False)
    instructions: Mapped[str] = mapped_column(Text, nullable=False)
    form_cues: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    safety_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    contraindications: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    provocation_tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    is_unilateral: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_compound: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<Exercise(id={self.id}, name={self.name}, slug={self.slug})>"
