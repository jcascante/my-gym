from pydantic import BaseModel, ConfigDict


class MatchRequest(BaseModel):
    environment_id: int
    days_per_week: int
    session_duration_min: int
    fitness_focus: str
    weight_unit: str = "kg"
    duration_weeks: int = 8


class TemplateMatchOut(BaseModel):
    template_id: int
    slug: str
    name: str
    fit_pct: int
    factors: dict[str, float]
    required_inputs: list[dict[str, object]]


class DraftRequest(MatchRequest):
    template_id: int
    required_inputs: dict[str, float] = {}


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
