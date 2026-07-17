from dataclasses import dataclass, field

from app.models.exercise import Exercise
from app.schemas.template import SlotRule

EXPERIENCE_ORDER = {"beginner": 0, "intermediate": 1, "advanced": 2}


@dataclass
class SelectionContext:
    equipment: list[str]
    experience: str
    injuries: list[str]
    used_movement_slugs: set[str]
    used_unilateral_flags: list[bool] = field(default_factory=list)


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


def _score(ex: Exercise, rule: SlotRule, ctx: SelectionContext) -> tuple[int, int, int, int, int]:
    muscle_fit = len(set(rule.muscles) & set(ex.primary_muscles))
    variety = 0 if ex.movement_slug in ctx.used_movement_slugs else 1
    diff_gap = -abs(EXPERIENCE_ORDER[ex.difficulty_level.value] - EXPERIENCE_ORDER[ctx.experience])
    priority_fit = 1 if (rule.priority == "primary") == ex.is_compound else 0
    unilateral_balance = 0
    if ctx.used_unilateral_flags and ctx.used_unilateral_flags[-1] == ex.is_unilateral:
        unilateral_balance = -1
    return (variety, priority_fit, muscle_fit, diff_gap, unilateral_balance)


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
        return None
    return max(pool, key=lambda ex: _score(ex, rule, ctx))


def template_is_feasible(sessions: list[object], all_exercises: list[Exercise], equipment: list[str]) -> bool:
    ctx = SelectionContext(list(equipment), "advanced", [], set())
    for session in sessions:
        for slot in getattr(session, "slots"):
            if select_for_slot(all_exercises, slot, ctx, None, set()) is None:
                return False
    return True
