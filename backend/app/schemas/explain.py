from typing import Literal

from pydantic import BaseModel

from app.schemas.program_api import Advisory


class TemplateExplanationOut(BaseModel):
    template_id: int
    slug: str
    name: str
    fit_pct: int
    factors: dict[str, float]
    tier: Literal["best", "strong", "possible"]
    advisories: list[Advisory] = []


class LedgerContributionOut(BaseModel):
    group: str
    effective_sets: float


class SlotExplanationOut(BaseModel):
    workout_exercise_id: int
    exercise_id: int
    exercise_name: str
    factors: dict[str, float]
    score: float
    ledger_contributions: list[LedgerContributionOut]
    safety_note: str | None
