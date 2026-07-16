from dataclasses import dataclass

from app.schemas.template import SlotRule

EXPERIENCE_ORDER = {"beginner": 0, "intermediate": 1, "advanced": 2}


@dataclass
class SelectionContext:
    equipment: list[str]
    experience: str
    injuries: list[str]
    used_movement_slugs: set[str]


def _matches_rule(ex: object, rule: SlotRule) -> bool:
    if rule.pattern and getattr(ex, "movement_pattern").value != rule.pattern:
        return False
    if rule.region and getattr(ex, "body_region").value != rule.region:
        return False
    if rule.muscles and not (set(rule.muscles) & set(getattr(ex, "primary_muscles"))):
        return False
    return True


def _passes_filters(ex: object, ctx: SelectionContext, tolerance: int = 1) -> bool:
    if not set(getattr(ex, "equipment_tags")) <= set(ctx.equipment):
        return False
    if EXPERIENCE_ORDER[getattr(ex, "difficulty_level").value] > EXPERIENCE_ORDER[ctx.experience] + tolerance:
        return False
    if set(getattr(ex, "contraindications")) & set(ctx.injuries):
        return False
    return True


def _score(ex: object, rule: SlotRule, ctx: SelectionContext) -> tuple[int, int, int, int]:
    muscle_fit = len(set(rule.muscles) & set(getattr(ex, "primary_muscles")))
    variety = 0 if getattr(ex, "movement_slug") in ctx.used_movement_slugs else 1
    diff_gap = -abs(EXPERIENCE_ORDER[getattr(ex, "difficulty_level").value] - EXPERIENCE_ORDER[ctx.experience])
    return (variety, muscle_fit, diff_gap, -getattr(ex, "id"))


def select_for_slot(
    candidates: list[object],
    rule: SlotRule,
    ctx: SelectionContext,
    locked_exercise_id: int | None,
    excluded_ids: set[int],
) -> object | None:
    if locked_exercise_id is not None:
        for ex in candidates:
            if getattr(ex, "id") == locked_exercise_id:
                return ex
    pool = [
        ex
        for ex in candidates
        if getattr(ex, "id") not in excluded_ids and _matches_rule(ex, rule) and _passes_filters(ex, ctx)
    ]
    if not pool:  # fallback: relax difficulty tolerance
        pool = [
            ex
            for ex in candidates
            if getattr(ex, "id") not in excluded_ids
            and _matches_rule(ex, rule)
            and _passes_filters(ex, ctx, tolerance=99)
        ]
    if not pool:
        return None
    return max(pool, key=lambda ex: _score(ex, rule, ctx))


def template_is_feasible(sessions: list[object], all_exercises: list[object], equipment: list[str]) -> bool:
    ctx = SelectionContext(list(equipment), "advanced", [], set())
    for session in sessions:
        for slot in getattr(session, "slots"):
            if select_for_slot(all_exercises, slot, ctx, None, set()) is None:
                return False
    return True
