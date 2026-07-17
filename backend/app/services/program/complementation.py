from collections import Counter

from app.models.exercise import Exercise


def coverage_deficit(muscles: list[str], coverage: "Counter[str]") -> float:
    if not muscles:
        return 0.5
    mean_cov = sum(coverage[m] for m in muscles) / len(muscles)
    max_cov = max(coverage.values(), default=0)
    return 1 - mean_cov / (1 + max_cov)


def is_core(ex: Exercise) -> bool:
    return ex.body_region.value == "core"


ANTAGONIST_PATTERNS: dict[str, str] = {
    "horizontal_push": "horizontal_pull",
    "horizontal_pull": "horizontal_push",
    "vertical_push": "vertical_pull",
    "vertical_pull": "vertical_push",
    "squat": "hinge",
    "hinge": "squat",
}


def antagonist_pattern(pattern: str) -> str | None:
    return ANTAGONIST_PATTERNS.get(pattern)
