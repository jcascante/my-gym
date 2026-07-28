"""Synthetic-user profile generator for the A/B harness (plan Section 1.8).

`generate_profiles()` is a true grid generator over goals x experience x days x
duration x equipment presets x injury sets, matching the plan's "grid over
goals x experience x days x duration x equipment presets x injury strings"
requirement literally -- it can be widened later without changing its shape.

The full Cartesian product is a few thousand combinations; running match->draft
twice (old + new formula) per profile would make the harness slow and a bad CI
citizen. `bounded_profiles()` deterministically samples a fixed-size subset
(fixed seed, never varies per run -- determinism matters for the harness's own
determinism property test) for the harness/property tests to actually run
against.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from app.db.seed.program_templates import PROGRAM_TEMPLATE_SEED

GOALS: list[str] = ["strength", "endurance", "weight_loss", "muscle_gain", "flexibility", "general"]
EXPERIENCE_LEVELS: list[str] = ["beginner", "intermediate", "advanced"]

# The 6 non-degenerate presets (excludes "other", whose empty equipment list makes
# every equipment-gated exercise infeasible -- ground truth from the task brief).
EQUIPMENT_PRESETS: list[str] = [
    "commercial_gym",
    "home",
    "bodyweight",
    "crossfit_box",
    "powerlifting_gym",
    "strength_gym",
]

INJURY_SETS: list[tuple[str, ...]] = [(), ("shoulder",), ("knee",)]

# Fixed seed + sample size for `bounded_profiles()`. Do not vary either per run: the
# determinism property test depends on the harness itself behaving deterministically.
_SAMPLE_SEED = 20260719
_SAMPLE_SIZE = 250


def _days_grid() -> list[int]:
    """Distinct days-per-week bounds across the seeded templates, read from the actual
    seed data (not hand-transcribed) so this stays correct if the seed data changes."""
    values = {int(entry["days_per_week_min"]) for entry in PROGRAM_TEMPLATE_SEED}  # type: ignore[arg-type]
    values |= {int(entry["days_per_week_max"]) for entry in PROGRAM_TEMPLATE_SEED}  # type: ignore[arg-type]
    return sorted(values)


def _duration_grid() -> list[int]:
    """Distinct session-duration bounds across the seeded templates, read from the
    actual seed data (not hand-transcribed)."""
    values = {int(entry["session_duration_min"]) for entry in PROGRAM_TEMPLATE_SEED}  # type: ignore[arg-type]
    values |= {int(entry["session_duration_max"]) for entry in PROGRAM_TEMPLATE_SEED}  # type: ignore[arg-type]
    return sorted(values)


@dataclass(frozen=True)
class SyntheticProfile:
    fitness_focus: str
    experience_level: str
    days_per_week: int
    session_duration_min: int
    environment_type: str
    injuries: tuple[str, ...]


def generate_profiles() -> list[SyntheticProfile]:
    """The full Cartesian grid: goals x experience x days x duration x equipment x injuries.

    Days/duration values are derived from the seeded templates' actual ranges (see
    `_days_grid`/`_duration_grid`), not hardcoded, so a fine-grained sweep over every
    plausible days/duration value isn't attempted here -- this is deliberately the
    boundary values that matter for range-fit scoring, per design decision #1(a).
    """
    days_values = _days_grid()
    duration_values = _duration_grid()
    return [
        SyntheticProfile(goal, experience, days, duration, equipment, injuries)
        for goal in GOALS
        for experience in EXPERIENCE_LEVELS
        for days in days_values
        for duration in duration_values
        for equipment in EQUIPMENT_PRESETS
        for injuries in INJURY_SETS
    ]


def bounded_profiles() -> list[SyntheticProfile]:
    """A fixed-size, fixed-seed sample of `generate_profiles()` sized for a fast harness
    run (target: ~150-300 profiles, well under 60s total suite runtime)."""
    full = generate_profiles()
    if len(full) <= _SAMPLE_SIZE:
        return full
    rng = random.Random(_SAMPLE_SEED)
    return rng.sample(full, _SAMPLE_SIZE)
