from app.models.exercise import Muscle
from app.services.program.taxonomy import (
    MUSCLE_GROUPS,
    ROLE_FACTOR,
    UNTRACKED_MUSCLES,
    muscle_group_for,
)


class TestMuscleGroupsCompleteness:
    """Every Muscle enum value must be either in MUSCLE_GROUPS or UNTRACKED_MUSCLES."""

    def test_all_muscles_accounted_for(self):
        """All 22 Muscle enum values must be placed exactly once."""
        all_muscles = set(Muscle)
        grouped_muscles = set()
        for muscles in MUSCLE_GROUPS.values():
            grouped_muscles.update(muscles)

        untracked = UNTRACKED_MUSCLES

        # All grouped + untracked must equal all muscles
        accounted = grouped_muscles | untracked
        assert accounted == all_muscles, f"Missing: {all_muscles - accounted}"

    def test_exactly_21_grouped_and_1_untracked(self):
        """21 muscles grouped, 1 untracked (CARDIO)."""
        grouped_count = sum(len(m) for m in MUSCLE_GROUPS.values())
        assert grouped_count == 21
        assert len(UNTRACKED_MUSCLES) == 1
        assert Muscle.CARDIO in UNTRACKED_MUSCLES


class TestMuscleGroupsDisjointness:
    """No Muscle should appear in more than one group."""

    def test_no_muscle_appears_twice(self):
        """Each muscle can only be in one group."""
        all_muscles = []
        for muscles in MUSCLE_GROUPS.values():
            all_muscles.extend(muscles)

        seen = set()
        duplicates = set()
        for muscle in all_muscles:
            if muscle in seen:
                duplicates.add(muscle)
            seen.add(muscle)

        assert not duplicates, f"Muscles in multiple groups: {duplicates}"


class TestMuscleGroupStructure:
    """Verify MUSCLE_GROUPS has the correct structure."""

    def test_exactly_15_groups(self):
        """Must have exactly 15 muscle groups."""
        assert len(MUSCLE_GROUPS) == 15

    def test_expected_group_names(self):
        """All expected group names should be present."""
        expected = {
            "chest",
            "back",
            "traps",
            "shoulders",
            "biceps",
            "triceps",
            "forearms",
            "quads",
            "hamstrings",
            "glutes",
            "calves",
            "abs",
            "obliques",
            "lower_back",
            "hips",
        }
        assert set(MUSCLE_GROUPS.keys()) == expected


class TestMuscleGroupLookup:
    """Test muscle_group_for() lookup function."""

    def test_chest_maps_to_chest_group(self):
        assert muscle_group_for(Muscle.CHEST) == "chest"

    def test_lats_maps_to_back_group(self):
        assert muscle_group_for(Muscle.LATS) == "back"

    def test_upper_back_maps_to_back_group(self):
        assert muscle_group_for(Muscle.UPPER_BACK) == "back"

    def test_shoulders_anterior_maps_to_shoulders(self):
        assert muscle_group_for(Muscle.SHOULDERS_ANTERIOR) == "shoulders"

    def test_shoulders_lateral_maps_to_shoulders(self):
        assert muscle_group_for(Muscle.SHOULDERS_LATERAL) == "shoulders"

    def test_shoulders_posterior_maps_to_shoulders(self):
        assert muscle_group_for(Muscle.SHOULDERS_POSTERIOR) == "shoulders"

    def test_biceps_maps_to_biceps_group(self):
        assert muscle_group_for(Muscle.BICEPS) == "biceps"

    def test_triceps_maps_to_triceps_group(self):
        assert muscle_group_for(Muscle.TRICEPS) == "triceps"

    def test_forearms_maps_to_forearms_group(self):
        assert muscle_group_for(Muscle.FOREARMS) == "forearms"

    def test_quads_maps_to_quads_group(self):
        assert muscle_group_for(Muscle.QUADS) == "quads"

    def test_hamstrings_maps_to_hamstrings_group(self):
        assert muscle_group_for(Muscle.HAMSTRINGS) == "hamstrings"

    def test_glutes_maps_to_glutes_group(self):
        assert muscle_group_for(Muscle.GLUTES) == "glutes"

    def test_calves_maps_to_calves_group(self):
        assert muscle_group_for(Muscle.CALVES) == "calves"

    def test_abs_maps_to_abs_group(self):
        assert muscle_group_for(Muscle.ABS) == "abs"

    def test_deep_core_maps_to_abs_group(self):
        assert muscle_group_for(Muscle.DEEP_CORE) == "abs"

    def test_obliques_maps_to_obliques_group(self):
        assert muscle_group_for(Muscle.OBLIQUES) == "obliques"

    def test_lower_back_maps_to_lower_back_group(self):
        assert muscle_group_for(Muscle.LOWER_BACK) == "lower_back"

    def test_hip_flexors_maps_to_hips_group(self):
        assert muscle_group_for(Muscle.HIP_FLEXORS) == "hips"

    def test_hip_abductors_maps_to_hips_group(self):
        assert muscle_group_for(Muscle.HIP_ABDUCTORS) == "hips"

    def test_hip_adductors_maps_to_hips_group(self):
        assert muscle_group_for(Muscle.HIP_ADDUCTORS) == "hips"

    def test_cardio_returns_none(self):
        """CARDIO is untracked and should return None."""
        assert muscle_group_for(Muscle.CARDIO) is None

    def test_all_grouped_muscles_have_lookup(self):
        """Every muscle in MUSCLE_GROUPS should have a lookup result."""
        for group_name, muscles in MUSCLE_GROUPS.items():
            for muscle in muscles:
                result = muscle_group_for(muscle)
                assert result == group_name, f"{muscle} should map to {group_name}, got {result}"


class TestRoleFactor:
    """Test ROLE_FACTOR dictionary."""

    def test_role_factor_has_correct_keys(self):
        """ROLE_FACTOR must have exactly 'primary' and 'secondary' keys."""
        assert set(ROLE_FACTOR.keys()) == {"primary", "secondary"}

    def test_role_factor_primary_value(self):
        """Primary muscle role factor should be 1.0."""
        assert ROLE_FACTOR["primary"] == 1.0

    def test_role_factor_secondary_value(self):
        """Secondary muscle role factor should be 0.5."""
        assert ROLE_FACTOR["secondary"] == 0.5

    def test_no_stabilizer_key_yet(self):
        """Stabilizer (0.25) should NOT be in ROLE_FACTOR yet (deferred)."""
        assert "stabilizer" not in ROLE_FACTOR
