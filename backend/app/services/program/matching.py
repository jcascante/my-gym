import logging
from dataclasses import dataclass
from typing import Any

WEIGHTS = {"goal": 0.35, "experience": 0.3, "days": 0.2, "duration": 0.15}

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MatchInput:
    fitness_focus: str
    experience_level: str
    days_per_week: int
    session_duration_min: int
    environment_equipment: list[str]


@dataclass(frozen=True)
class TemplateMatch:
    template_id: int
    slug: str
    name: str
    fit_pct: int
    factors: dict[str, float]


def _range_fit(value: int, low: int, high: int) -> float:
    if low <= value <= high:
        return 1.0
    distance = low - value if value < low else value - high
    return max(0.0, 1.0 - distance / max(low, 1))


def rank_templates(templates: list[Any], inp: MatchInput, feasibility: dict[int, bool]) -> list[TemplateMatch]:
    logger.info(
        f"Matching templates for: fitness_focus={inp.fitness_focus}, experience={inp.experience_level}, "
        f"days_per_week={inp.days_per_week}, session_duration_min={inp.session_duration_min}, "
        f"equipment={inp.environment_equipment}"
    )
    matches: list[TemplateMatch] = []
    for t in templates:
        is_feasible = feasibility.get(t.id, False)
        factors = {
            "goal": 1.0 if inp.fitness_focus in t.goals else 0.0,
            "experience": 1.0 if inp.experience_level in t.experience_levels else 0.3,
            "days": _range_fit(inp.days_per_week, t.days_per_week_min, t.days_per_week_max),
            "duration": _range_fit(inp.session_duration_min, t.session_duration_min, t.session_duration_max),
        }
        score = sum(WEIGHTS[k] * v for k, v in factors.items())
        matches.append(TemplateMatch(t.id, t.slug, t.name, round(score * 100), factors))
        logger.debug(f"Template {t.slug}: score={round(score * 100)}, feasible={is_feasible}, factors={factors}")
    matches.sort(key=lambda m: m.fit_pct, reverse=True)
    top_3 = matches[:3]
    logger.info(f"Top 3 matches: {[(m.slug, m.fit_pct) for m in top_3]}")
    return top_3
