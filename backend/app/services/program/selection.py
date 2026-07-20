from collections import Counter
from dataclasses import dataclass, field
from typing import Protocol

from app.models.exercise import Exercise
from app.schemas.template import SlotRule
from app.services.program.complementation import coverage_deficit
from app.services.program.ledger import LedgerAccumulator
from app.services.program.preferences import movement_preference_weight

EXPERIENCE_ORDER = {"beginner": 0, "intermediate": 1, "advanced": 2}


@dataclass(frozen=True)
class SelectionWeights:
    variety: float = 1.0
    priority_fit: float = 1.5
    muscle_fit: float = 1.0
    difficulty: float = 0.75
    unilateral_balance: float = 0.5
    movement_preference: float = 1.25
    complementary_coverage: float = 1.25


class ExerciseScorer(Protocol):
    def score(self, features: dict[str, float]) -> float: ...


@dataclass(frozen=True)
class HeuristicExerciseScorer:
    weights: SelectionWeights = field(default_factory=SelectionWeights)

    def score(self, features: dict[str, float]) -> float:
        w = self.weights
        return (
            w.variety * features["variety"]
            + w.priority_fit * features["priority_fit"]
            + w.muscle_fit * features["muscle_fit"]
            + w.difficulty * features["difficulty"]
            + w.unilateral_balance * features["unilateral_balance"]
            + w.movement_preference * features["movement_preference"]
            + w.complementary_coverage * features["complementary_coverage"]
        )


@dataclass
class SelectionContext:
    equipment: list[str]
    experience: str
    injuries: list[str]
    used_movement_slugs: set[str]
    used_unilateral_flags: list[bool] = field(default_factory=list)
    movement_preferences: dict[str, float] = field(default_factory=dict)
    muscle_coverage: "Counter[str]" = field(default_factory=Counter)
    complementary_focus: bool = True
    weights: SelectionWeights = field(default_factory=SelectionWeights)
    ledger: LedgerAccumulator = field(default_factory=LedgerAccumulator)


def _matches_rule(ex: Exercise, rule: SlotRule) -> bool:
    if rule.pattern and ex.movement_pattern.value != rule.pattern:
        return False
    if rule.region and ex.body_region.value != rule.region:
        return False
    if rule.muscles and not (set(rule.muscles) & set(ex.primary_muscles)):
        return False
    return True


def _passes_filters(ex: Exercise, ctx: SelectionContext, tolerance: int = 1) -> bool:
    if not set(ex.equipment_tags) <= set(ctx.equipment):
        return False
    if EXPERIENCE_ORDER[ex.difficulty_level.value] > EXPERIENCE_ORDER[ctx.experience] + tolerance:
        return False
    if set(ex.contraindications) & set(ctx.injuries):
        return False
    return True


def _extract_features(ex: Exercise, rule: SlotRule, ctx: SelectionContext) -> dict[str, float]:
    muscle_fit = len(set(rule.muscles) & set(ex.primary_muscles)) / max(1, len(rule.muscles)) if rule.muscles else 0.0
    variety = 0.0 if ex.movement_slug in ctx.used_movement_slugs else 1.0
    difficulty = 1.0 - abs(EXPERIENCE_ORDER[ex.difficulty_level.value] - EXPERIENCE_ORDER[ctx.experience]) / 2
    priority_fit = 1.0 if (rule.priority == "primary") == ex.is_compound else 0.0
    unilateral_balance = 1.0
    if ctx.used_unilateral_flags and ctx.used_unilateral_flags[-1] == ex.is_unilateral:
        unilateral_balance = 0.0
    movement_preference = movement_preference_weight(ex, ctx.movement_preferences) / 2
    if rule.priority == "primary" or not ctx.complementary_focus:
        complementary_coverage = 0.5
    else:
        complementary_coverage = coverage_deficit(ex.primary_muscles, ctx.muscle_coverage)
    return {
        "variety": variety,
        "priority_fit": priority_fit,
        "muscle_fit": muscle_fit,
        "difficulty": difficulty,
        "unilateral_balance": unilateral_balance,
        "movement_preference": movement_preference,
        "complementary_coverage": complementary_coverage,
    }


def _ranked_pool(
    candidates: list[Exercise], rule: SlotRule, ctx: SelectionContext, excluded_ids: set[int]
) -> list[Exercise]:
    pool = [
        ex for ex in candidates if ex.id not in excluded_ids and _matches_rule(ex, rule) and _passes_filters(ex, ctx)
    ]
    if not pool:  # fallback: relax difficulty tolerance
        pool = [
            ex
            for ex in candidates
            if ex.id not in excluded_ids and _matches_rule(ex, rule) and _passes_filters(ex, ctx, tolerance=99)
        ]
    if not pool:
        return []
    scorer = HeuristicExerciseScorer(ctx.weights)
    # score descending, exercise id ascending on ties (deterministic, no reliance on input order).
    return sorted(pool, key=lambda ex: (-scorer.score(_extract_features(ex, rule, ctx)), ex.id))


def ranked_pool_for_slot(
    candidates: list[Exercise], rule: SlotRule, ctx: SelectionContext, excluded_ids: set[int]
) -> list[Exercise]:
    return _ranked_pool(candidates, rule, ctx, excluded_ids)


def select_for_slot(
    candidates: list[Exercise],
    rule: SlotRule,
    ctx: SelectionContext,
    locked_exercise_id: int | None,
    excluded_ids: set[int],
) -> Exercise | None:
    if locked_exercise_id is not None:
        for ex in candidates:
            if ex.id == locked_exercise_id:
                return ex
    ranked = _ranked_pool(candidates, rule, ctx, excluded_ids)
    return ranked[0] if ranked else None


def template_is_feasible(sessions: list[object], all_exercises: list[Exercise], equipment: list[str]) -> bool:
    ctx = SelectionContext(list(equipment), "advanced", [], set())
    for session in sessions:
        for slot in getattr(session, "slots"):
            if select_for_slot(all_exercises, slot, ctx, None, set()) is None:
                return False
    return True
