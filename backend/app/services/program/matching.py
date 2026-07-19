import logging
import math
from dataclasses import dataclass, field, replace
from typing import Any, Callable, Protocol

from app.schemas.template import SlotRule, TemplateDefinition
from app.services.program.preferences import movement_preference_weight
from app.services.program.selection import _matches_rule

logger = logging.getLogger(__name__)

_PATTERN_REGION: dict[str, str] = {
    "squat": "lower_body",
    "hinge": "lower_body",
    "lunge": "lower_body",
    "horizontal_push": "upper_body",
    "vertical_push": "upper_body",
    "horizontal_pull": "upper_body",
    "vertical_pull": "upper_body",
    "rotation": "core",
    "anti_rotation": "core",
    "carry": "full_body",
    "isolation": "upper_body",
    "locomotion": "full_body",
    "mobility": "full_body",
}

_PERIODIZATION_CONSISTENT_MODELS = {"linear_load", "double_progression"}
_PERIODIZATION_VARIABLE_MODELS = {"weekly_undulating"}


@dataclass(frozen=True)
class MatchWeights:
    goal: float = 0.25
    experience: float = 0.20
    days: float = 0.12
    duration: float = 0.08
    movement_preference: float = 0.15
    focus_complement: float = 0.12
    periodization: float = 0.08


class TemplateScorer(Protocol):
    def score(self, features: dict[str, float]) -> float: ...


@dataclass(frozen=True)
class HeuristicTemplateScorer:
    weights: MatchWeights = field(default_factory=MatchWeights)

    def score(self, features: dict[str, float]) -> float:
        w = self.weights
        return (
            w.goal * features["goal"]
            + w.experience * features["experience"]
            + w.days * features["days"]
            + w.duration * features["duration"]
            + w.movement_preference * features["movement_preference"]
            + w.focus_complement * features["focus_complement"]
            + w.periodization * features["periodization"]
        )


@dataclass(frozen=True)
class MatchInput:
    fitness_focus: str
    experience_level: str
    days_per_week: int
    session_duration_min: int
    environment_equipment: list[str]
    movement_preferences: dict[str, float] = field(default_factory=dict)
    complementary_focus: bool = True
    progression_style: str = "consistent"


@dataclass(frozen=True)
class TemplateMatch:
    template_id: int
    slug: str
    name: str
    fit_pct: int
    factors: dict[str, float]
    # True only when returned via the all-infeasible best-effort fallback.
    # Phase 2 (plan §2.5) will fold this into the general Advisory list.
    all_infeasible: bool = False


def _range_fit(value: int, low: int, high: int) -> float:
    if low <= value <= high:
        return 1.0
    distance = low - value if value < low else value - high
    return max(0.0, 1.0 - distance / max(low, 1))


def _gaussian_range_fit(value: int, low: int, high: int, sigma: float) -> float:
    """Gaussian kernel for range fitting.

    Returns exp(-(d/sigma)^2) where d = max(0, low - value, value - high).
    When d == 0 (value in range), returns 1.0.
    Handles sigma <= 0: returns 1.0 if d == 0, else 0.0.
    """
    if low <= value <= high:
        distance = 0
    elif value < low:
        distance = low - value
    else:
        distance = value - high

    if sigma <= 0:
        return 1.0 if distance == 0 else 0.0
    return math.exp(-((distance / sigma) ** 2))


def _slot_region(slot: SlotRule) -> str:
    if slot.region:
        return slot.region
    return _PATTERN_REGION.get(slot.pattern or "", "full_body")


def _region_diversity(sessions: list[Any]) -> float:
    regions = {_slot_region(slot) for session in sessions for slot in session.slots}
    return min(1.0, len(regions) / 3)


def _movement_preference_feature(
    sessions: list[Any], all_exercises: list[Any], equipment: list[str], prefs: dict[str, float]
) -> float:
    candidates = [
        ex
        for session in sessions
        for slot in session.slots
        if slot.priority == "primary"
        for ex in all_exercises
        if _matches_rule(ex, slot) and set(ex.equipment_tags) <= set(equipment)
    ]
    if not candidates:
        return 0.5
    return (sum(movement_preference_weight(ex, prefs) for ex in candidates) / len(candidates)) / 2


def _focus_complement_feature(sessions: list[Any], complementary_focus: bool) -> float:
    diversity = _region_diversity(sessions)
    return diversity if complementary_focus else 1.0 - diversity


def _periodization_feature(model_key: str, progression_style: str) -> float:
    if progression_style == "consistent" and model_key in _PERIODIZATION_CONSISTENT_MODELS:
        return 1.0
    if progression_style == "variable" and model_key in _PERIODIZATION_VARIABLE_MODELS:
        return 1.0
    return 0.3


def rank_templates(
    templates: list[Any],
    inp: MatchInput,
    feasibility: dict[int, bool],
    definitions: dict[int, TemplateDefinition] | None = None,
    all_exercises: list[Any] | None = None,
    scorer: TemplateScorer | None = None,
    safety_feasible: Callable[[Any], bool] | None = None,
) -> list[TemplateMatch]:
    """Score and rank templates, excluding infeasible ones.

    `safety_feasible` is a hook point for Phase 3 (plan §3.3) to layer
    safety-driven infeasibility on top of equipment/pool-based feasibility.
    It is a no-op until then: when omitted, no template is excluded on its
    account.
    """
    scorer = scorer or HeuristicTemplateScorer()
    definitions = definitions or {}
    exercises = all_exercises or []
    logger.info(
        f"Matching templates for: fitness_focus={inp.fitness_focus}, experience={inp.experience_level}, "
        f"days_per_week={inp.days_per_week}, session_duration_min={inp.session_duration_min}, "
        f"equipment={inp.environment_equipment}"
    )
    matches: list[TemplateMatch] = []
    feasible_matches: list[TemplateMatch] = []
    for t in templates:
        is_feasible = feasibility.get(t.id, False) and (safety_feasible is None or safety_feasible(t))
        definition = definitions.get(t.id)
        if definition is not None:
            sessions = definition.split.sessions
            movement_preference = _movement_preference_feature(
                sessions, exercises, inp.environment_equipment, inp.movement_preferences
            )
            focus_complement = _focus_complement_feature(sessions, inp.complementary_focus)
            periodization = _periodization_feature(definition.progression.model_key, inp.progression_style)
        else:
            movement_preference = 0.5
            focus_complement = 0.5
            periodization = 0.3
        factors = {
            "goal": 1.0 if inp.fitness_focus in t.goals else 0.0,
            "experience": 1.0 if inp.experience_level in t.experience_levels else 0.3,
            "days": _range_fit(inp.days_per_week, t.days_per_week_min, t.days_per_week_max),
            "duration": _range_fit(inp.session_duration_min, t.session_duration_min, t.session_duration_max),
            "movement_preference": movement_preference,
            "focus_complement": focus_complement,
            "periodization": periodization,
        }
        score = scorer.score(factors)
        match = TemplateMatch(t.id, t.slug, t.name, round(score * 100), factors)
        matches.append(match)
        if is_feasible:
            feasible_matches.append(match)
        logger.debug(f"Template {t.slug}: score={round(score * 100)}, feasible={is_feasible}, factors={factors}")

    all_infeasible = bool(matches) and not feasible_matches
    candidates = matches if all_infeasible else feasible_matches
    candidates = sorted(candidates, key=lambda m: m.fit_pct, reverse=True)
    top_3 = candidates[:3]
    if all_infeasible:
        top_3 = [replace(m, all_infeasible=True) for m in top_3]
        logger.warning(f"All templates infeasible; returning best-effort matches: {[m.slug for m in top_3]}")
    logger.info(f"Top 3 matches: {[(m.slug, m.fit_pct) for m in top_3]}")
    return top_3
