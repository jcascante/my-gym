"""Volume ledger for tracking effective sets, frequency, and hard set ratios by muscle group.

The ledger is the authoritative source for volume distribution across muscle groups
in a workout program. It supports both bulk computation (over a full program) and
incremental updates (for beam search and adaptation workflows).

Core types:
- GroupLedger: effective sets per week, frequency (days hit), and hard set share
- Ledger: dict of GroupLedger keyed by taxonomy group name (always has all 15 groups)
- LedgerPick: a single exercise in a workout, with sets and hard/accessory classification
- LedgerAccumulator: mutable working state that applies/removes picks incrementally

The actual group-crediting math (dedupe same-group muscles, apply role factors) is
in LedgerAccumulator; compute_ledger is a thin wrapper over it.
"""

from dataclasses import dataclass

from app.models.exercise import Exercise, Muscle
from app.models.program import WorkoutProgram
from app.services.program.engine_config import VolumeBandRow, VolumeBandsConfig
from app.services.program.taxonomy import MUSCLE_GROUPS, ROLE_FACTOR, muscle_group_for


@dataclass(frozen=True)
class GroupLedger:
    """Volume metrics for a single muscle group in a program."""

    effective_sets_week: float
    """Total effective sets per week for this group (after role-factor weighting)."""

    frequency_days: int
    """Number of distinct workout days this group is trained."""

    hard_set_share: float
    """Ratio of hard (working) effective sets to total effective sets.
    0.0 if effective_sets_week == 0.0 (no division by zero).
    """


Ledger = dict[str, GroupLedger]
"""Ledger is a dict from taxonomy group name to GroupLedger.
Always has exactly 15 keys (one per MUSCLE_GROUPS entry), even for zero-volume groups.
"""


@dataclass(frozen=True)
class LedgerPick:
    """A single exercise occurrence in a workout session."""

    exercise_id: int
    """The Exercise.id being performed."""

    workout_key: str
    """The Workout.key (e.g., 'upper_a', 'day_1') — used to count frequency_days."""

    sets: int
    """Number of sets performed."""

    is_hard: bool
    """True if this pick is a 'working set' (scheme_key='main'), else accessory/secondary."""


class LedgerAccumulator:
    """Mutable working state for ledger calculations.

    Tracks effective sets and hard sets per group, and a per-(group, workout_key)
    pick counter to determine frequency_days (number of distinct workout_keys with >0 picks).

    The group-crediting logic (same-group dedup, role factors) is here and is shared
    by both apply/remove (for incremental updates) and compute_ledger (bulk path).
    """

    def __init__(self) -> None:
        """Initialize empty accumulator."""
        # Per-group totals (after role-factor weighting)
        self._effective_sets: dict[str, float] = {g: 0.0 for g in MUSCLE_GROUPS}
        self._hard_sets: dict[str, float] = {g: 0.0 for g in MUSCLE_GROUPS}

        # Per-(group, workout_key) pick counter (integer, to avoid float epsilon issues).
        # Used to determine if a (group, workout_key) pair still "counts" after removes.
        self._pick_counts: dict[tuple[str, str], int] = {}

    def apply(self, pick: LedgerPick, exercise: Exercise) -> None:
        """Apply a pick (exercise in a workout), crediting its muscle groups.

        Args:
            pick: The pick to apply (exercise_id, workout_key, sets, is_hard).
            exercise: The Exercise object (for primary/secondary muscle lookup).

        Same-group dedup logic: if an exercise's primary_muscles contains multiple
        Muscle values that map to the same taxonomy group, that group is credited
        once (at the primary role factor). Secondary muscles are credited only if
        they don't overlap with primary groups (and at 0.5x role factor).
        """
        # Determine which groups this exercise credits
        primary_groups = {g for m in exercise.primary_muscles if (g := muscle_group_for(Muscle(m))) is not None}
        secondary_groups = {
            g for m in exercise.secondary_muscles if (g := muscle_group_for(Muscle(m))) is not None
        } - primary_groups

        # Apply sets and hard sets to each group
        for group in primary_groups:
            weighted_sets = pick.sets * ROLE_FACTOR["primary"]
            self._effective_sets[group] += weighted_sets
            if pick.is_hard:
                self._hard_sets[group] += weighted_sets
            # Increment pick counter for this (group, workout_key) pair
            key = (group, pick.workout_key)
            self._pick_counts[key] = self._pick_counts.get(key, 0) + 1

        for group in secondary_groups:
            weighted_sets = pick.sets * ROLE_FACTOR["secondary"]
            self._effective_sets[group] += weighted_sets
            if pick.is_hard:
                self._hard_sets[group] += weighted_sets
            # Increment pick counter for this (group, workout_key) pair
            key = (group, pick.workout_key)
            self._pick_counts[key] = self._pick_counts.get(key, 0) + 1

    def remove(self, pick: LedgerPick, exercise: Exercise) -> None:
        """Remove a pick (exactly reverses apply with same pick and exercise).

        Args:
            pick: The pick to remove.
            exercise: The Exercise object (for primary/secondary muscle lookup).

        Applies the same group-crediting logic as apply, but negated (subtracts sets).
        Assumes callers always pair apply/remove correctly; mismatched pairs have
        undefined behavior.
        """
        # Determine which groups this exercise credits (same logic as apply)
        primary_groups = {g for m in exercise.primary_muscles if (g := muscle_group_for(Muscle(m))) is not None}
        secondary_groups = {
            g for m in exercise.secondary_muscles if (g := muscle_group_for(Muscle(m))) is not None
        } - primary_groups

        # Remove sets and hard sets from each group (negate apply)
        for group in primary_groups:
            weighted_sets = pick.sets * ROLE_FACTOR["primary"]
            self._effective_sets[group] -= weighted_sets
            if pick.is_hard:
                self._hard_sets[group] -= weighted_sets
            # Decrement pick counter
            key = (group, pick.workout_key)
            self._pick_counts[key] -= 1

        for group in secondary_groups:
            weighted_sets = pick.sets * ROLE_FACTOR["secondary"]
            self._effective_sets[group] -= weighted_sets
            if pick.is_hard:
                self._hard_sets[group] -= weighted_sets
            # Decrement pick counter
            key = (group, pick.workout_key)
            self._pick_counts[key] -= 1

    def clone(self) -> "LedgerAccumulator":
        """Return an independent copy of this accumulator (deep-copies the three
        internal dicts, mirroring their construction in `__init__`).

        Used by beam search to branch speculative per-candidate volume state without
        mutating the parent beam's ledger (plan §2.5).
        """
        new = LedgerAccumulator()
        new._effective_sets = dict(self._effective_sets)
        new._hard_sets = dict(self._hard_sets)
        new._pick_counts = dict(self._pick_counts)
        return new

    def snapshot(self) -> Ledger:
        """Return the current ledger state as a frozen Ledger dict.

        Returns:
            A Ledger with all 15 MUSCLE_GROUPS keys, each with computed
            GroupLedger (effective_sets_week, frequency_days, hard_set_share).
        """
        result: Ledger = {}

        for group in MUSCLE_GROUPS:
            effective = self._effective_sets[group]
            hard = self._hard_sets[group]

            # frequency_days = number of distinct workout_keys with pick_count > 0
            frequency = sum(1 for (g, _), count in self._pick_counts.items() if g == group and count > 0)

            # hard_set_share: ratio of hard to total, or 0.0 if no volume
            if effective > 0.0:
                hard_share = hard / effective
            else:
                hard_share = 0.0

            result[group] = GroupLedger(
                effective_sets_week=effective,
                frequency_days=frequency,
                hard_set_share=hard_share,
            )

        return result


def band_for_experience(volume_bands: VolumeBandsConfig, experience: str) -> VolumeBandRow:
    """Look up the volume band row matching `experience` (plan §2.4/§2.5).

    A validated `engine.yaml` always has exactly one row per experience level (Task
    2.4's schema, not enforced by a validator but true of every config that will ever
    load), so a linear scan is fine; a missing row means a config-loading bug, not a
    runtime-recoverable case, so it's allowed to raise `StopIteration`.
    """
    return next(b for b in volume_bands.bands if b.experience == experience)


def compute_ledger(program: WorkoutProgram, exercises: list[Exercise]) -> Ledger:
    """Compute the ledger for a workout program.

    Args:
        program: A WorkoutProgram with populated workouts and exercises.
        exercises: A flat list of all Exercise objects (looked up by id).

    Returns:
        A Ledger with metrics for all 15 muscle groups.

    The function is a thin wrapper over LedgerAccumulator: it builds an accumulator,
    applies every WorkoutExercise in the program as a LedgerPick, then returns the
    snapshot. This ensures the bulk and incremental paths use the same math.

    Note: program.workouts represents one representative week (not duration_weeks
    repeated); effective_sets_week and frequency_days are computed directly over
    this single week.
    """
    acc = LedgerAccumulator()

    # Build a lookup dict for O(1) exercise access by id
    exercise_by_id = {ex.id: ex for ex in exercises}

    # Process every workout and exercise in the program
    for workout in program.workouts:
        for we in workout.exercises:
            # Look up the Exercise object for this WorkoutExercise
            exercise = exercise_by_id.get(we.exercise_id)
            if exercise is None:
                # If exercise not found, skip it (shouldn't happen in well-formed data)
                continue

            # Build a LedgerPick and apply it
            pick = LedgerPick(
                exercise_id=we.exercise_id,
                workout_key=workout.key,
                sets=we.sets,
                is_hard=(we.scheme_key == "main"),
            )
            acc.apply(pick, exercise)

    return acc.snapshot()
