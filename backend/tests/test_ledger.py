"""Tests for the workout ledger (volume tracking) module.

Tests cover: compute_ledger on draft programs, LedgerAccumulator round-trips,
same-group dedup, hard set share, frequency days calculation, and round-trip
equivalence (apply/remove produces identical snapshots to bulk compute_ledger).
"""

import pytest

from app.models.exercise import BodyRegion, Exercise, ExperienceLevel, MovementPattern
from app.models.program import Workout, WorkoutExercise, WorkoutProgram
from app.services.program.ledger import (
    GroupLedger,
    LedgerAccumulator,
    LedgerPick,
    compute_ledger,
)
from app.services.program.taxonomy import MUSCLE_GROUPS


def _exercise(
    id_: int,
    slug: str,
    *,
    primary_muscles: list[str] | None = None,
    secondary_muscles: list[str] | None = None,
    movement_pattern: MovementPattern = MovementPattern.ISOLATION,
    body_region: BodyRegion = BodyRegion.FULL_BODY,
    equipment_tags: list[str] | None = None,
    difficulty_level: ExperienceLevel = ExperienceLevel.BEGINNER,
) -> Exercise:
    """Construct an Exercise for testing (no DB session needed)."""
    return Exercise(
        id=id_,
        name=slug,
        slug=slug,
        movement_slug=slug,
        body_region=body_region,
        movement_pattern=movement_pattern,
        primary_muscles=primary_muscles if primary_muscles is not None else ["chest"],
        secondary_muscles=secondary_muscles if secondary_muscles is not None else [],
        equipment_tags=equipment_tags if equipment_tags is not None else [],
        difficulty_level=difficulty_level,
        instructions="Do the thing.",
        form_cues=[],
        contraindications=[],
        is_active=True,
    )


def _workout_exercise(
    id_: int,
    exercise_id: int,
    sets: int = 3,
    scheme_key: str = "main",
    reps_min: int = 6,
    reps_max: int = 10,
) -> WorkoutExercise:
    """Construct a WorkoutExercise for testing."""
    return WorkoutExercise(
        id=id_,
        workout_id=0,  # Will be set by caller
        order=0,  # Will be set by caller
        exercise_id=exercise_id,
        fills_rule={},
        sets=sets,
        reps_min=reps_min,
        reps_max=reps_max,
        base_load=None,
        rest_seconds=90,
        scheme_key=scheme_key,
        target_rpe=None,
        intensity_pct=None,
        is_locked=False,
        is_user_swapped=False,
        rotation_pool=[],
    )


def _workout(
    id_: int,
    program_id: int,
    key: str = "day_1",
    exercises: list[WorkoutExercise] | None = None,
) -> Workout:
    """Construct a Workout with exercises."""
    workout = Workout(
        id=id_,
        program_id=program_id,
        key=key,
        name=f"Workout {key}",
        focus=None,
        order=0,
    )
    if exercises is None:
        exercises = []
    # Set workout_id and order on each exercise
    for order, ex in enumerate(exercises):
        ex.workout_id = workout.id
        ex.order = order
    workout.exercises = exercises
    return workout


def _program(
    id_: int,
    user_id: int,
    workouts: list[Workout] | None = None,
) -> WorkoutProgram:
    """Construct a WorkoutProgram with workouts."""
    program = WorkoutProgram(
        id=id_,
        user_id=user_id,
        template_id=1,
        environment_id=1,
        name="Test Program",
        focus=None,
        status="draft",
        duration_weeks=4,
        days_per_week=4,
        weight_unit="kg",
        constraints={},
    )
    if workouts is None:
        workouts = []
    # Set program_id and order on each workout
    for order, w in enumerate(workouts):
        w.program_id = program.id
        w.order = order
    program.workouts = workouts
    return program


class TestGroupLedger:
    """Test the GroupLedger dataclass."""

    def test_group_ledger_is_frozen(self):
        """GroupLedger is immutable."""
        gl = GroupLedger(effective_sets_week=10.0, frequency_days=3, hard_set_share=0.8)
        with pytest.raises(AttributeError):
            gl.effective_sets_week = 20.0  # type: ignore

    def test_group_ledger_creation(self):
        """GroupLedger can be created with valid values."""
        gl = GroupLedger(effective_sets_week=12.5, frequency_days=4, hard_set_share=0.75)
        assert gl.effective_sets_week == 12.5
        assert gl.frequency_days == 4
        assert gl.hard_set_share == 0.75


class TestLedgerPick:
    """Test the LedgerPick dataclass."""

    def test_ledger_pick_is_frozen(self):
        """LedgerPick is immutable."""
        pick = LedgerPick(exercise_id=1, workout_key="day_1", sets=3, is_hard=True)
        with pytest.raises(AttributeError):
            pick.sets = 4  # type: ignore

    def test_ledger_pick_creation(self):
        """LedgerPick can be created."""
        pick = LedgerPick(exercise_id=5, workout_key="day_2", sets=4, is_hard=False)
        assert pick.exercise_id == 5
        assert pick.workout_key == "day_2"
        assert pick.sets == 4
        assert pick.is_hard is False


class TestLedgerAccumulator:
    """Test the LedgerAccumulator incremental API."""

    def test_accumulator_snapshot_all_groups_present(self):
        """Snapshot includes all 15 groups, even with no data."""
        acc = LedgerAccumulator()
        snapshot = acc.snapshot()
        assert len(snapshot) == 15
        assert all(name in snapshot for name in MUSCLE_GROUPS.keys())

    def test_accumulator_snapshot_empty_groups_have_zero_values(self):
        """Untouched groups have 0.0 sets, 0 days, 0.0 hard_share."""
        acc = LedgerAccumulator()
        snapshot = acc.snapshot()
        chest_ledger = snapshot["chest"]
        assert chest_ledger.effective_sets_week == 0.0
        assert chest_ledger.frequency_days == 0
        assert chest_ledger.hard_set_share == 0.0

    def test_accumulator_apply_single_exercise_primary_muscle(self):
        """Applying an exercise credits its primary muscle group."""
        acc = LedgerAccumulator()
        chest_ex = _exercise(1, "bench-press", primary_muscles=["chest"])
        pick = LedgerPick(exercise_id=1, workout_key="day_1", sets=4, is_hard=True)

        acc.apply(pick, chest_ex)
        snapshot = acc.snapshot()

        # chest group gets 4 sets (primary role factor = 1.0)
        assert snapshot["chest"].effective_sets_week == 4.0
        assert snapshot["chest"].frequency_days == 1
        assert snapshot["chest"].hard_set_share == 1.0

    def test_accumulator_apply_secondary_muscle_weighting(self):
        """Applying an exercise credits secondary muscles at 0.5x."""
        acc = LedgerAccumulator()
        # Barbell row: primary back, secondary biceps
        ex = _exercise(
            1,
            "barbell-row",
            primary_muscles=["lats"],
            secondary_muscles=["biceps"],
        )
        pick = LedgerPick(exercise_id=1, workout_key="day_1", sets=4, is_hard=True)

        acc.apply(pick, ex)
        snapshot = acc.snapshot()

        # back (lats primary): 4 sets * 1.0 = 4.0
        # biceps (secondary): 4 sets * 0.5 = 2.0
        assert snapshot["back"].effective_sets_week == 4.0
        assert snapshot["biceps"].effective_sets_week == 2.0

    def test_accumulator_apply_multiple_picks_same_group_same_day(self):
        """Multiple exercises on same day hitting same group sum, but count as 1 frequency day."""
        acc = LedgerAccumulator()
        ex1 = _exercise(1, "bench-press", primary_muscles=["chest"])
        ex2 = _exercise(2, "incline-press", primary_muscles=["chest"])

        pick1 = LedgerPick(exercise_id=1, workout_key="day_1", sets=3, is_hard=True)
        pick2 = LedgerPick(exercise_id=2, workout_key="day_1", sets=3, is_hard=True)

        acc.apply(pick1, ex1)
        acc.apply(pick2, ex2)

        snapshot = acc.snapshot()

        # chest: 3 + 3 = 6 sets, but only 1 frequency day
        assert snapshot["chest"].effective_sets_week == 6.0
        assert snapshot["chest"].frequency_days == 1
        assert snapshot["chest"].hard_set_share == 1.0

    def test_accumulator_apply_multiple_days_increases_frequency(self):
        """Same group on different days increases frequency."""
        acc = LedgerAccumulator()
        ex = _exercise(1, "bench-press", primary_muscles=["chest"])

        pick1 = LedgerPick(exercise_id=1, workout_key="day_1", sets=3, is_hard=True)
        pick2 = LedgerPick(exercise_id=1, workout_key="day_2", sets=3, is_hard=True)

        acc.apply(pick1, ex)
        acc.apply(pick2, ex)

        snapshot = acc.snapshot()

        # chest: 3 + 3 = 6 sets, 2 frequency days
        assert snapshot["chest"].effective_sets_week == 6.0
        assert snapshot["chest"].frequency_days == 2

    def test_accumulator_hard_set_share_main_only(self):
        """hard_set_share = 1.0 when all sets are is_hard=True."""
        acc = LedgerAccumulator()
        ex = _exercise(1, "bench-press", primary_muscles=["chest"])

        pick = LedgerPick(exercise_id=1, workout_key="day_1", sets=4, is_hard=True)
        acc.apply(pick, ex)

        snapshot = acc.snapshot()
        assert snapshot["chest"].hard_set_share == 1.0

    def test_accumulator_hard_set_share_mixed(self):
        """hard_set_share reflects ratio of hard to total sets."""
        acc = LedgerAccumulator()
        ex = _exercise(1, "bench-press", primary_muscles=["chest"])

        # 3 hard sets main, 2 accessory
        pick_hard = LedgerPick(exercise_id=1, workout_key="day_1", sets=3, is_hard=True)
        pick_accessory = LedgerPick(exercise_id=1, workout_key="day_1", sets=2, is_hard=False)

        acc.apply(pick_hard, ex)
        acc.apply(pick_accessory, ex)

        snapshot = acc.snapshot()
        # 3 hard, 5 total => 3/5 = 0.6
        assert snapshot["chest"].hard_set_share == pytest.approx(0.6)

    def test_accumulator_hard_set_share_zero_when_no_volume(self):
        """hard_set_share = 0.0 for groups with zero volume (no division by zero)."""
        acc = LedgerAccumulator()
        snapshot = acc.snapshot()
        assert snapshot["chest"].hard_set_share == 0.0

    def test_accumulator_remove_reverses_apply(self):
        """Removing a pick exactly reverses applying it."""
        acc = LedgerAccumulator()
        ex = _exercise(1, "bench-press", primary_muscles=["chest"])
        pick = LedgerPick(exercise_id=1, workout_key="day_1", sets=4, is_hard=True)

        # Apply, then remove
        acc.apply(pick, ex)
        acc.remove(pick, ex)

        snapshot = acc.snapshot()

        # Should be back to all zeros
        assert snapshot["chest"].effective_sets_week == pytest.approx(0.0)
        assert snapshot["chest"].frequency_days == 0
        assert snapshot["chest"].hard_set_share == 0.0

    def test_accumulator_remove_keeps_other_groups_unchanged(self):
        """Removing a pick doesn't affect other muscle groups."""
        acc = LedgerAccumulator()
        bench_ex = _exercise(1, "bench-press", primary_muscles=["chest"])
        row_ex = _exercise(2, "row", primary_muscles=["lats"])

        pick_bench = LedgerPick(exercise_id=1, workout_key="day_1", sets=3, is_hard=True)
        pick_row = LedgerPick(exercise_id=2, workout_key="day_1", sets=3, is_hard=True)

        acc.apply(pick_bench, bench_ex)
        acc.apply(pick_row, row_ex)
        acc.remove(pick_bench, bench_ex)

        snapshot = acc.snapshot()

        assert snapshot["chest"].effective_sets_week == 0.0
        assert snapshot["back"].effective_sets_week == 3.0

    def test_accumulator_round_trip_multiple_days_and_exercises(self):
        """Round-trip with mixed main/accessory across multiple days."""
        acc = LedgerAccumulator()
        ex1 = _exercise(1, "bench", primary_muscles=["chest"])
        ex2 = _exercise(2, "row", primary_muscles=["lats"])

        picks = [
            LedgerPick(exercise_id=1, workout_key="day_1", sets=4, is_hard=True),
            LedgerPick(exercise_id=2, workout_key="day_1", sets=3, is_hard=True),
            LedgerPick(exercise_id=1, workout_key="day_2", sets=3, is_hard=False),
        ]

        # Apply all
        acc.apply(picks[0], ex1)
        acc.apply(picks[1], ex2)
        acc.apply(picks[2], ex1)

        # Remove all
        acc.remove(picks[0], ex1)
        acc.remove(picks[1], ex2)
        acc.remove(picks[2], ex1)

        snapshot_after = acc.snapshot()

        # Should be back to empty state
        for group_name in MUSCLE_GROUPS.keys():
            assert snapshot_after[group_name].effective_sets_week == pytest.approx(0.0)
            assert snapshot_after[group_name].frequency_days == 0
            assert snapshot_after[group_name].hard_set_share == 0.0


class TestSameGroupDedup:
    """Test same-group dedup: an exercise doesn't double-credit a group."""

    def test_dedup_primary_same_group(self):
        """Exercise with multiple primary muscles in same group credits once."""
        acc = LedgerAccumulator()
        # shoulders_anterior and shoulders_lateral both map to "shoulders"
        ex = _exercise(
            1,
            "shoulder-press",
            primary_muscles=["shoulders_anterior", "shoulders_lateral"],
        )

        pick = LedgerPick(exercise_id=1, workout_key="day_1", sets=3, is_hard=True)
        acc.apply(pick, ex)

        snapshot = acc.snapshot()

        # shoulders group gets 3 sets (not 6, even though we have 2 muscles)
        assert snapshot["shoulders"].effective_sets_week == 3.0

    def test_dedup_secondary_same_group(self):
        """Multiple secondary muscles in same group credit once at 0.5x."""
        acc = LedgerAccumulator()
        # Hypothetical exercise with hip_flexors and hip_abductors as secondary
        ex = _exercise(
            1,
            "hip-exercise",
            primary_muscles=["quads"],
            secondary_muscles=["hip_flexors", "hip_abductors"],
        )

        pick = LedgerPick(exercise_id=1, workout_key="day_1", sets=4, is_hard=True)
        acc.apply(pick, ex)

        snapshot = acc.snapshot()

        # quads (primary): 4 sets
        # hips (secondary, deduped): 4 * 0.5 = 2.0 sets (not 4.0)
        assert snapshot["quads"].effective_sets_week == 4.0
        assert snapshot["hips"].effective_sets_week == pytest.approx(2.0)

    def test_dedup_primary_override_secondary_same_group(self):
        """If a group appears in both primary and secondary, use primary factor."""
        acc = LedgerAccumulator()
        # chest as primary, abs and deep_core in secondary, but "abs" group also in primary
        ex = _exercise(
            1,
            "compound",
            primary_muscles=["chest", "abs"],
            secondary_muscles=["obliques", "abs"],  # abs appears in both
        )

        pick = LedgerPick(exercise_id=1, workout_key="day_1", sets=4, is_hard=True)
        acc.apply(pick, ex)

        snapshot = acc.snapshot()

        # chest (primary): 4.0
        # abs (primary, not secondary): 4.0 (not 2.0)
        # obliques (secondary): 2.0
        assert snapshot["chest"].effective_sets_week == 4.0
        assert snapshot["abs"].effective_sets_week == 4.0
        assert snapshot["obliques"].effective_sets_week == pytest.approx(2.0)


class TestComputeLedger:
    """Test the bulk compute_ledger function."""

    def test_compute_ledger_all_15_groups_present(self):
        """compute_ledger returns all 15 groups, even with only one touched."""
        program = _program(
            1,
            1,
            workouts=[
                _workout(
                    1,
                    1,
                    key="day_1",
                    exercises=[_workout_exercise(1, 1, sets=3)],
                ),
            ],
        )
        exercises = [_exercise(1, "bench", primary_muscles=["chest"])]

        ledger = compute_ledger(program, exercises)

        assert len(ledger) == 15
        assert all(name in ledger for name in MUSCLE_GROUPS.keys())
        assert ledger["chest"].effective_sets_week == 3.0
        assert ledger["back"].effective_sets_week == 0.0

    def test_compute_ledger_primary_secondary_weighting(self):
        """compute_ledger applies role-factor weighting correctly."""
        program = _program(
            1,
            1,
            workouts=[
                _workout(
                    1,
                    1,
                    key="day_1",
                    exercises=[
                        _workout_exercise(1, 1, sets=4, scheme_key="main"),
                        _workout_exercise(2, 2, sets=4, scheme_key="main"),
                    ],
                ),
            ],
        )
        exercises = [
            _exercise(1, "bench", primary_muscles=["chest"]),
            _exercise(
                2,
                "barbell-row",
                primary_muscles=["lats"],
                secondary_muscles=["biceps"],
            ),
        ]

        ledger = compute_ledger(program, exercises)

        assert ledger["chest"].effective_sets_week == 4.0
        assert ledger["back"].effective_sets_week == 4.0
        assert ledger["biceps"].effective_sets_week == pytest.approx(2.0)

    def test_compute_ledger_frequency_days_multi_workout(self):
        """compute_ledger counts distinct workout days correctly."""
        program = _program(
            1,
            1,
            workouts=[
                _workout(1, 1, key="day_1", exercises=[_workout_exercise(1, 1, sets=3)]),
                _workout(2, 1, key="day_2", exercises=[_workout_exercise(2, 1, sets=3)]),
                _workout(3, 1, key="day_3", exercises=[_workout_exercise(3, 1, sets=3)]),
            ],
        )
        exercises = [_exercise(1, "chest-ex", primary_muscles=["chest"])]

        ledger = compute_ledger(program, exercises)

        assert ledger["chest"].frequency_days == 3
        assert ledger["chest"].effective_sets_week == 9.0

    def test_compute_ledger_hard_set_share_all_main(self):
        """hard_set_share = 1.0 when all picks are scheme_key='main'."""
        program = _program(
            1,
            1,
            workouts=[
                _workout(
                    1,
                    1,
                    key="day_1",
                    exercises=[
                        _workout_exercise(1, 1, sets=3, scheme_key="main"),
                        _workout_exercise(2, 1, sets=2, scheme_key="main"),
                    ],
                ),
            ],
        )
        exercises = [_exercise(1, "bench", primary_muscles=["chest"])]

        ledger = compute_ledger(program, exercises)

        assert ledger["chest"].hard_set_share == 1.0

    def test_compute_ledger_hard_set_share_mixed(self):
        """hard_set_share reflects main/(main+accessory) correctly."""
        program = _program(
            1,
            1,
            workouts=[
                _workout(
                    1,
                    1,
                    key="day_1",
                    exercises=[
                        _workout_exercise(1, 1, sets=4, scheme_key="main"),
                        _workout_exercise(2, 1, sets=1, scheme_key="accessory"),
                    ],
                ),
            ],
        )
        exercises = [_exercise(1, "bench", primary_muscles=["chest"])]

        ledger = compute_ledger(program, exercises)

        # 4 hard, 1 accessory (2 secondary weighting = 0.5 effective)
        # hard / (hard + accessory * 0.5) would be wrong
        # Actually: scheme_key="main" is_hard, else is_hard=False
        # So 4 hard, 1 not-hard = 4/5 = 0.8
        assert ledger["chest"].hard_set_share == pytest.approx(0.8)

    def test_compute_ledger_with_accessory_scheme(self):
        """Picks with scheme_key != 'main' are not hard."""
        program = _program(
            1,
            1,
            workouts=[
                _workout(
                    1,
                    1,
                    key="day_1",
                    exercises=[
                        _workout_exercise(1, 1, sets=3, scheme_key="main"),
                        _workout_exercise(2, 1, sets=2, scheme_key="accessory"),
                    ],
                ),
            ],
        )
        exercises = [_exercise(1, "bench", primary_muscles=["chest"])]

        ledger = compute_ledger(program, exercises)

        # 3 hard + 2 non-hard = 5 total, hard_share = 3/5 = 0.6
        assert ledger["chest"].effective_sets_week == 5.0
        assert ledger["chest"].hard_set_share == pytest.approx(0.6)


class TestAccumulatorVsComputeLedger:
    """Test that accumulator and compute_ledger produce identical results."""

    def test_accumulator_and_compute_produce_same_snapshot(self):
        """Manual accumulator calls match compute_ledger results."""
        program = _program(
            1,
            1,
            workouts=[
                _workout(
                    1,
                    1,
                    key="day_1",
                    exercises=[
                        _workout_exercise(1, 1, sets=3, scheme_key="main"),
                        _workout_exercise(2, 2, sets=2, scheme_key="accessory"),
                    ],
                ),
                _workout(
                    2,
                    1,
                    key="day_2",
                    exercises=[
                        _workout_exercise(3, 1, sets=2, scheme_key="main"),
                    ],
                ),
            ],
        )
        exercises = [
            _exercise(1, "bench", primary_muscles=["chest"]),
            _exercise(2, "flye", primary_muscles=["chest"]),
        ]

        # Compute via compute_ledger
        ledger_via_compute = compute_ledger(program, exercises)

        # Compute via manual accumulator
        acc = LedgerAccumulator()
        for workout in program.workouts:
            for we in workout.exercises:
                ex = next(e for e in exercises if e.id == we.exercise_id)
                pick = LedgerPick(
                    exercise_id=we.exercise_id,
                    workout_key=workout.key,
                    sets=we.sets,
                    is_hard=(we.scheme_key == "main"),
                )
                acc.apply(pick, ex)

        ledger_via_manual = acc.snapshot()

        # Both should be identical
        for group_name in MUSCLE_GROUPS.keys():
            assert ledger_via_compute[group_name].effective_sets_week == pytest.approx(
                ledger_via_manual[group_name].effective_sets_week
            )
            assert ledger_via_compute[group_name].frequency_days == ledger_via_manual[group_name].frequency_days
            assert ledger_via_compute[group_name].hard_set_share == pytest.approx(
                ledger_via_manual[group_name].hard_set_share
            )

    def test_accumulator_and_compute_complex_program(self):
        """Complex program with multiple exercises and days."""
        program = _program(
            1,
            1,
            workouts=[
                _workout(
                    1,
                    1,
                    key="upper_a",
                    exercises=[
                        _workout_exercise(1, 1, sets=4, scheme_key="main"),
                        _workout_exercise(2, 2, sets=4, scheme_key="main"),
                        _workout_exercise(3, 3, sets=3, scheme_key="accessory"),
                    ],
                ),
                _workout(
                    2,
                    1,
                    key="lower_a",
                    exercises=[
                        _workout_exercise(4, 4, sets=4, scheme_key="main"),
                        _workout_exercise(5, 5, sets=3, scheme_key="main"),
                        _workout_exercise(6, 6, sets=3, scheme_key="accessory"),
                    ],
                ),
                _workout(
                    3,
                    1,
                    key="upper_b",
                    exercises=[
                        _workout_exercise(7, 2, sets=4, scheme_key="main"),
                        _workout_exercise(8, 3, sets=2, scheme_key="accessory"),
                    ],
                ),
            ],
        )
        exercises = [
            _exercise(1, "bench", primary_muscles=["chest"]),
            _exercise(2, "rows", primary_muscles=["lats"]),
            _exercise(3, "flyes", primary_muscles=["chest"]),
            _exercise(4, "squats", primary_muscles=["quads"]),
            _exercise(5, "rdl", primary_muscles=["hamstrings"]),
            _exercise(6, "leg-curl", primary_muscles=["hamstrings"]),
        ]

        ledger_via_compute = compute_ledger(program, exercises)

        acc = LedgerAccumulator()
        for workout in program.workouts:
            for we in workout.exercises:
                ex = next(e for e in exercises if e.id == we.exercise_id)
                pick = LedgerPick(
                    exercise_id=we.exercise_id,
                    workout_key=workout.key,
                    sets=we.sets,
                    is_hard=(we.scheme_key == "main"),
                )
                acc.apply(pick, ex)

        ledger_via_manual = acc.snapshot()

        for group_name in MUSCLE_GROUPS.keys():
            assert ledger_via_compute[group_name].effective_sets_week == pytest.approx(
                ledger_via_manual[group_name].effective_sets_week
            )
            assert ledger_via_compute[group_name].frequency_days == ledger_via_manual[group_name].frequency_days
            assert ledger_via_compute[group_name].hard_set_share == pytest.approx(
                ledger_via_manual[group_name].hard_set_share
            )
