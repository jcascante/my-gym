"""Static linter for the exercise/template seed catalog.

Checks schema validity, reachability, muscle-group coverage, and
duplicate/orphan exercises against the closed vocabularies and taxonomy
defined elsewhere in the codebase. Pure functions operating on
already-loaded ORM rows -- callers own DB I/O, matching the convention
used by services/program/*.py.

Run directly (loads the real seeded DB and exits non-zero on violations):

    uv run python -m scripts.lint_library
"""

import asyncio
import sys

from sqlalchemy import select

from app.core.constants import (
    ALLOWED_CONTRAINDICATION_TAGS,
    ALLOWED_EQUIPMENT_TAGS,
    ALLOWED_MUSCLE_GROUPS,
    ALLOWED_PROVOCATION_TAGS,
    ENVIRONMENT_TYPE_EQUIPMENT_PRESETS,
)
from app.core.database import async_session
from app.models.exercise import Equipment, Exercise, Muscle, Provocation
from app.models.program import ProgramTemplate
from app.models.user import ExperienceLevel
from app.services.program.regression_graphs import RegressionGraphsConfig, get_regression_graphs
from app.services.program.taxonomy import MUSCLE_GROUPS, muscle_group_for

# The "other" environment preset is deliberately empty (core/constants.py) --
# it signals "show everything" in the UI rather than a real equipment set. An
# empty equipment list makes every equipment-gated exercise infeasible there
# by construction, not a genuine library gap, so it is excluded from both
# reachability and coverage checks.
_NON_OTHER_PRESETS: dict[str, set[str]] = {
    name: set(equipment) for name, equipment in ENVIRONMENT_TYPE_EQUIPMENT_PRESETS.items() if name != "other"
}


def check_schema_validity(exercises: list[Exercise]) -> list[str]:
    """Validate exercise fields against the closed vocabularies in core.constants.

    Covers all rows passed in (not just active ones) -- schema validity is a
    data-integrity property independent of whether an exercise is currently
    selectable.
    """
    violations: list[str] = []

    allowed_equipment = set(ALLOWED_EQUIPMENT_TAGS)
    allowed_muscles = set(ALLOWED_MUSCLE_GROUPS)
    allowed_contraindications = set(ALLOWED_CONTRAINDICATION_TAGS)
    allowed_provocations = set(ALLOWED_PROVOCATION_TAGS)

    # Drift check: ALLOWED_EQUIPMENT_TAGS is meant to mirror the Equipment
    # enum exactly, but nothing enforces that at import time.
    equipment_enum_values = {e.value for e in Equipment}
    if allowed_equipment != equipment_enum_values:
        violations.append(
            "ALLOWED_EQUIPMENT_TAGS has drifted from the Equipment enum: "
            f"missing_from_allowed_list={sorted(equipment_enum_values - allowed_equipment)}, "
            f"extra_in_allowed_list={sorted(allowed_equipment - equipment_enum_values)}"
        )

    provocation_enum_values = {p.value for p in Provocation}
    if allowed_provocations != provocation_enum_values:
        violations.append(
            "ALLOWED_PROVOCATION_TAGS has drifted from the Provocation enum: "
            f"missing_from_allowed_list={sorted(provocation_enum_values - allowed_provocations)}, "
            f"extra_in_allowed_list={sorted(allowed_provocations - provocation_enum_values)}"
        )

    for exercise in exercises:
        invalid_equipment = set(exercise.equipment_tags) - allowed_equipment
        if invalid_equipment:
            violations.append(f"{exercise.slug}: invalid equipment_tags {sorted(invalid_equipment)}")

        invalid_primary = set(exercise.primary_muscles) - allowed_muscles
        if invalid_primary:
            violations.append(f"{exercise.slug}: invalid primary_muscles {sorted(invalid_primary)}")

        invalid_secondary = set(exercise.secondary_muscles) - allowed_muscles
        if invalid_secondary:
            violations.append(f"{exercise.slug}: invalid secondary_muscles {sorted(invalid_secondary)}")

        invalid_contraindications = set(exercise.contraindications) - allowed_contraindications
        if invalid_contraindications:
            violations.append(f"{exercise.slug}: invalid contraindications {sorted(invalid_contraindications)}")

        invalid_provocations = set(exercise.provocation_tags) - allowed_provocations
        if invalid_provocations:
            violations.append(f"{exercise.slug}: invalid provocation_tags {sorted(invalid_provocations)}")

    return violations


def _active_template_patterns(templates: list[ProgramTemplate]) -> set[str]:
    """Every slot["pattern"] value (where present) across active templates' sessions/slots."""
    patterns: set[str] = set()
    for template in templates:
        if not template.is_active:
            continue
        for session in template.split.get("sessions", []):
            for slot in session.get("slots", []):
                pattern = slot.get("pattern")
                if pattern is not None:
                    patterns.add(pattern)
    return patterns


def check_reachability(exercises: list[Exercise], templates: list[ProgramTemplate]) -> list[str]:
    """Every (non-'other' preset, pattern-used-by-an-active-template) pair must have
    >=1 beginner-permissible active exercise satisfiable in that preset.
    """
    violations: list[str] = []
    patterns = _active_template_patterns(templates)
    active_exercises = [ex for ex in exercises if ex.is_active]

    for preset_name, preset_equipment in _NON_OTHER_PRESETS.items():
        for pattern in patterns:
            reachable = any(
                exercise.movement_pattern.value == pattern
                and set(exercise.equipment_tags) <= preset_equipment
                and exercise.difficulty_level == ExperienceLevel.BEGINNER
                for exercise in active_exercises
            )
            if not reachable:
                violations.append(
                    f"No beginner-permissible active exercise reaches pattern={pattern!r} " f"in preset={preset_name!r}"
                )

    return violations


def _exercise_muscle_groups(exercise: Exercise) -> set[str]:
    groups = {muscle_group_for(Muscle(m)) for m in exercise.primary_muscles}
    return {g for g in groups if g is not None}


def check_coverage(exercises: list[Exercise]) -> list[str]:
    """Every taxonomy group must be primary for >=3 active exercises across
    >=2 distinct non-'other' presets (collectively, not per-exercise).
    """
    violations: list[str] = []
    active_exercises = [ex for ex in exercises if ex.is_active]

    for group in MUSCLE_GROUPS:
        qualifying = [ex for ex in active_exercises if group in _exercise_muscle_groups(ex)]

        if len(qualifying) < 3:
            violations.append(
                f"Muscle group {group!r} is primary for only {len(qualifying)} active exercise(s) (need >= 3)"
            )

        reachable_presets = {
            preset_name
            for preset_name, preset_equipment in _NON_OTHER_PRESETS.items()
            if any(set(ex.equipment_tags) <= preset_equipment for ex in qualifying)
        }
        if len(reachable_presets) < 2:
            violations.append(
                f"Muscle group {group!r} qualifying exercises collectively reach only "
                f"{len(reachable_presets)} preset(s) (need >= 2): {sorted(reachable_presets)}"
            )

    return violations


def check_duplicates_and_orphans(exercises: list[Exercise]) -> list[str]:
    """Duplicates: any slug appearing more than once across all rows.
    Orphans: any active exercise whose equipment_tags can't fit into any
    single non-'other' preset (dead content -- never selectable anywhere).
    """
    violations: list[str] = []

    slug_counts: dict[str, int] = {}
    for exercise in exercises:
        slug_counts[exercise.slug] = slug_counts.get(exercise.slug, 0) + 1
    for slug, count in sorted(slug_counts.items()):
        if count > 1:
            violations.append(f"Duplicate slug {slug!r} appears {count} times")

    for exercise in exercises:
        if not exercise.is_active:
            continue
        required = set(exercise.equipment_tags)
        if not any(required <= preset_equipment for preset_equipment in _NON_OTHER_PRESETS.values()):
            violations.append(
                f"{exercise.slug}: equipment_tags {sorted(required)} not satisfiable by any "
                "non-'other' environment preset (orphaned)"
            )

    return violations


def check_regression_graphs(
    exercises: list[Exercise], templates: list[ProgramTemplate], graphs: RegressionGraphsConfig
) -> list[str]:
    """Every regression-graph node slug must exist in the library (all rows, not just
    active -- same rationale as `check_schema_validity`), and every movement pattern
    used by an active template must have >=2 `regression` edges + >=1 `cross_pattern`
    edge (plan §3.3 exit criteria). Edge `relieves` values are already validated as real
    `Provocation` members at config-load time (`RegressionEdge`'s Pydantic typing), so
    that half of "edge axes" doesn't need a separate check here.
    """
    violations: list[str] = []
    slugs = {exercise.slug for exercise in exercises}

    for pattern, edges in graphs.patterns.items():
        for edge in edges:
            if edge.from_slug not in slugs:
                violations.append(f"regression_graphs.{pattern}: unknown 'from' slug {edge.from_slug!r}")
            if edge.to not in slugs:
                violations.append(f"regression_graphs.{pattern}: unknown 'to' slug {edge.to!r}")

    for pattern in sorted(_active_template_patterns(templates)):
        edges = graphs.patterns.get(pattern, [])
        regressions = sum(1 for e in edges if e.kind == "regression")
        cross_pattern = sum(1 for e in edges if e.kind == "cross_pattern")
        if regressions < 2:
            violations.append(f"regression_graphs.{pattern}: only {regressions} regression edge(s), need >= 2")
        if cross_pattern < 1:
            violations.append(f"regression_graphs.{pattern}: only {cross_pattern} cross_pattern edge(s), need >= 1")

    return violations


def lint_library(
    exercises: list[Exercise], templates: list[ProgramTemplate], graphs: RegressionGraphsConfig
) -> list[str]:
    """Run all five checks and concatenate violation messages. Empty result = library passes."""
    violations: list[str] = []
    violations.extend(check_schema_validity(exercises))
    violations.extend(check_reachability(exercises, templates))
    violations.extend(check_coverage(exercises))
    violations.extend(check_duplicates_and_orphans(exercises))
    violations.extend(check_regression_graphs(exercises, templates, graphs))
    return violations


async def _load_and_lint() -> list[str]:
    async with async_session() as db:
        exercises = list((await db.execute(select(Exercise))).scalars().all())
        templates = list((await db.execute(select(ProgramTemplate))).scalars().all())
    return lint_library(exercises, templates, get_regression_graphs())


def main() -> int:
    violations = asyncio.run(_load_and_lint())
    if violations:
        print(f"Library lint found {len(violations)} violation(s):")
        for violation in violations:
            print(f"  - {violation}")
        return 1
    print("Library lint passed: no violations found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
