from pydantic import BaseModel, ConfigDict, field_validator

from app.schemas.program import EffortMethod, ProgressionStyle, VarietyPreference


class MatchRequest(BaseModel):
    environment_id: int
    days_per_week: int
    session_duration_min: int
    fitness_focus: str
    weight_unit: str = "kg"
    duration_weeks: int = 8
    progression_style: ProgressionStyle = ProgressionStyle.CONSISTENT
    movement_preferences: dict[str, float] = {}
    complementary_focus: bool = True
    variety_preference: VarietyPreference = VarietyPreference.LOW

    @field_validator("movement_preferences")
    @classmethod
    def _validate_weight_range(cls, v: dict[str, float]) -> dict[str, float]:
        for family, weight in v.items():
            if not 0.0 <= weight <= 2.0:
                raise ValueError(f"movement_preferences weight for '{family}' must be in [0.0, 2.0], got {weight}")
        return v


class TemplateMatchOut(BaseModel):
    template_id: int
    slug: str
    name: str
    fit_pct: int
    factors: dict[str, float]
    required_inputs: list[dict[str, object]]
    # True only when returned via the all-infeasible best-effort fallback.
    # Phase 2 (plan §2.5) will fold this into the general Advisory list rather
    # than keep it as a standalone boolean.
    all_infeasible: bool = False


class DraftRequest(MatchRequest):
    template_id: int
    required_inputs: dict[str, float] = {}
    effort_method: EffortMethod | None = None


class FeedbackRequest(BaseModel):
    type: str
    workout_exercise_id: int | None = None
    exercise_id: int | None = None
    workout_key: str | None = None
    delta: int | None = None


class SlotPreviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    workout_exercise_id: int
    exercise_id: int
    exercise_name: str
    sets: int
    reps: int
    load: float | None
    rest_seconds: int
    note: str | None
    is_locked: bool
    is_user_swapped: bool
    effort_target: dict[str, object] | None = None
    rotation_pool: list[int] = []


class WorkoutPreviewOut(BaseModel):
    workout_id: int
    key: str
    name: str
    slots: list[SlotPreviewOut]


class ProgramPreviewOut(BaseModel):
    program_id: int
    name: str
    status: str
    duration_weeks: int
    weeks: dict[int, list[WorkoutPreviewOut]]


class AlternativeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    slug: str
