import pytest
from sqlalchemy import select

from app.models.exercise import BodyRegion, Exercise, ExperienceLevel, MovementPattern
from app.models.program import ProgramTemplate
from scripts.lint_library import (
    check_coverage,
    check_duplicates_and_orphans,
    check_reachability,
    check_schema_validity,
    lint_library,
)


def _exercise(
    slug: str,
    *,
    movement_pattern: MovementPattern = MovementPattern.ISOLATION,
    body_region: BodyRegion = BodyRegion.FULL_BODY,
    primary_muscles: list[str] | None = None,
    secondary_muscles: list[str] | None = None,
    equipment_tags: list[str] | None = None,
    contraindications: list[str] | None = None,
    difficulty_level: ExperienceLevel = ExperienceLevel.BEGINNER,
    is_active: bool = True,
) -> Exercise:
    return Exercise(
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
        contraindications=contraindications if contraindications is not None else [],
        is_active=is_active,
    )


def _template(
    slug: str,
    *,
    slots_by_session: list[list[dict[str, object]]],
    is_active: bool = True,
) -> ProgramTemplate:
    return ProgramTemplate(
        name=slug,
        slug=slug,
        description="",
        goals=["general"],
        experience_levels=["beginner"],
        days_per_week_min=1,
        days_per_week_max=1,
        session_duration_min=30,
        session_duration_max=45,
        split={
            "sessions": [
                {"key": f"s{i}", "name": f"s{i}", "order": i, "slots": slots}
                for i, slots in enumerate(slots_by_session)
            ]
        },
        progression_ref={"model_key": "linear_load", "params": {}},
        required_inputs=[],
        is_active=is_active,
    )


class TestCheckSchemaValidity:
    def test_clean_exercise_has_no_violations(self):
        exercise = _exercise("clean-1", equipment_tags=["barbell"], primary_muscles=["chest"])
        assert check_schema_validity([exercise]) == []

    def test_invalid_equipment_tag_is_flagged(self):
        exercise = _exercise("bad-equipment", equipment_tags=["not_a_real_tag"])
        violations = check_schema_validity([exercise])
        assert any("bad-equipment" in v and "equipment_tags" in v for v in violations)

    def test_invalid_primary_muscle_is_flagged(self):
        exercise = _exercise("bad-primary", primary_muscles=["not_a_real_muscle"])
        violations = check_schema_validity([exercise])
        assert any("bad-primary" in v and "primary_muscles" in v for v in violations)

    def test_invalid_secondary_muscle_is_flagged(self):
        exercise = _exercise("bad-secondary", secondary_muscles=["not_a_real_muscle"])
        violations = check_schema_validity([exercise])
        assert any("bad-secondary" in v and "secondary_muscles" in v for v in violations)

    def test_invalid_contraindication_is_flagged(self):
        exercise = _exercise("bad-contra", contraindications=["not_a_real_contraindication"])
        violations = check_schema_validity([exercise])
        assert any("bad-contra" in v and "contraindications" in v for v in violations)

    def test_equipment_allowlist_drift_is_detected(self, monkeypatch):
        monkeypatch.setattr("scripts.lint_library.ALLOWED_EQUIPMENT_TAGS", ["totally_made_up_equipment"])
        violations = check_schema_validity([])
        assert any("drifted" in v for v in violations)

    def test_covers_inactive_exercises_too(self):
        exercise = _exercise("inactive-bad", equipment_tags=["not_a_real_tag"], is_active=False)
        violations = check_schema_validity([exercise])
        assert any("inactive-bad" in v for v in violations)


class TestCheckReachability:
    def test_missing_exercise_for_pattern_is_flagged_for_every_non_other_preset(self):
        template = _template("t1", slots_by_session=[[{"pattern": "carry", "priority": "primary", "scheme": "main"}]])
        violations = check_reachability([], [template])
        # 6 non-"other" presets, each missing a beginner "carry" exercise.
        assert len(violations) == 6
        assert all("carry" in v for v in violations)
        assert all("other" not in v for v in violations)

    def test_exercise_with_no_equipment_requirement_satisfies_every_preset(self):
        template = _template(
            "t2", slots_by_session=[[{"pattern": "mobility", "priority": "primary", "scheme": "main"}]]
        )
        exercise = _exercise(
            "bodyweight-mobility",
            movement_pattern=MovementPattern.MOBILITY,
            equipment_tags=[],
            difficulty_level=ExperienceLevel.BEGINNER,
        )
        assert check_reachability([exercise], [template]) == []

    def test_non_beginner_exercise_does_not_satisfy_reachability(self):
        template = _template(
            "t3", slots_by_session=[[{"pattern": "mobility", "priority": "primary", "scheme": "main"}]]
        )
        exercise = _exercise(
            "advanced-mobility",
            movement_pattern=MovementPattern.MOBILITY,
            equipment_tags=[],
            difficulty_level=ExperienceLevel.ADVANCED,
        )
        assert check_reachability([exercise], [template]) != []

    def test_inactive_template_patterns_are_ignored(self):
        template = _template(
            "t4",
            slots_by_session=[[{"pattern": "carry", "priority": "primary", "scheme": "main"}]],
            is_active=False,
        )
        # No exercises at all -- if the inactive template's pattern were considered,
        # this would produce violations; since it's inactive, it shouldn't.
        assert check_reachability([], [template]) == []

    def test_region_only_slots_do_not_contribute_a_pattern(self):
        template = _template("t5", slots_by_session=[[{"region": "core", "priority": "accessory", "scheme": "main"}]])
        assert check_reachability([], [template]) == []

    def test_equipment_subset_semantics_partial_overlap_does_not_satisfy_preset(self):
        # Exercise has equipment_tags=["barbell", "chalk"] where "chalk" is not
        # a real equipment tag but exists on the exercise. A preset with only
        # ["barbell", "bench"] should NOT be considered satisfied because
        # {"barbell", "chalk"} is NOT a subset of {"barbell", "bench"}.
        # This verifies subset (<=) semantics, not intersection (&) semantics.
        template = _template("t6", slots_by_session=[[{"pattern": "squat", "priority": "primary", "scheme": "main"}]])
        exercise = _exercise(
            "squat-barbell-chalk",
            movement_pattern=MovementPattern.SQUAT,
            equipment_tags=["barbell", "chalk"],
            difficulty_level=ExperienceLevel.BEGINNER,
        )
        violations = check_reachability([exercise], [template])
        # All non-"other" presets should still lack a reachable squat exercise
        # because the barbell+chalk combo doesn't fit any single preset.
        assert len(violations) > 0
        assert all("squat" in v for v in violations)

    def test_intermediate_difficulty_does_not_satisfy_beginner_reachability(self):
        # Reachability requires difficulty_level == BEGINNER exactly (tolerance 0),
        # not the runtime tolerance-1 comparison selection.py uses. An INTERMEDIATE
        # exercise is only one tier off BEGINNER — unlike ADVANCED (two tiers off),
        # this is the case that would slip through a tolerance-1 bug undetected.
        template = _template("t7", slots_by_session=[[{"pattern": "squat", "priority": "primary", "scheme": "main"}]])
        exercise = _exercise(
            "squat-intermediate",
            movement_pattern=MovementPattern.SQUAT,
            equipment_tags=[],
            difficulty_level=ExperienceLevel.INTERMEDIATE,
        )
        violations = check_reachability([exercise], [template])
        assert len(violations) > 0
        assert all("squat" in v for v in violations)


class TestCheckCoverage:
    def test_group_with_fewer_than_three_exercises_is_flagged(self):
        exercises = [_exercise(f"chest-{i}", primary_muscles=["chest"], equipment_tags=[]) for i in range(2)]
        violations = check_coverage(exercises)
        assert any("'chest'" in v and "need >= 3" in v for v in violations)

    def test_group_reachable_in_only_one_preset_is_flagged(self):
        # "gymnastic_rings" only appears in the crossfit_box preset.
        exercises = [
            _exercise(f"chest-{i}", primary_muscles=["chest"], equipment_tags=["gymnastic_rings"]) for i in range(3)
        ]
        violations = check_coverage(exercises)
        assert any("'chest'" in v and "need >= 2" in v for v in violations)

    def test_group_with_enough_exercises_and_presets_passes(self):
        exercises = [
            _exercise("chest-1", primary_muscles=["chest"], equipment_tags=[]),
            _exercise("chest-2", primary_muscles=["chest"], equipment_tags=["dumbbells"]),
            _exercise("chest-3", primary_muscles=["chest"], equipment_tags=["barbell", "bench"]),
        ]
        violations = check_coverage(exercises)
        assert not any("'chest'" in v for v in violations)

    def test_inactive_exercises_do_not_count_toward_coverage(self):
        exercises = [
            _exercise(f"chest-{i}", primary_muscles=["chest"], equipment_tags=[], is_active=False) for i in range(3)
        ]
        violations = check_coverage(exercises)
        assert any("'chest'" in v and "need >= 3" in v for v in violations)

    def test_collective_preset_coverage_no_single_exercise_spans_two_presets(self):
        # Muscle group qualifies with >=3 exercises, but NO single exercise's
        # equipment_tags alone satisfies >=2 presets. The >=2-preset requirement
        # is satisfied collectively: exercise-1 only fits in "gym" (barbell+bench),
        # exercise-2 only fits in "home" (dumbbells), exercise-3 fits in both.
        # Together they span >=2 presets, so no violation.
        exercises = [
            _exercise("chest-1", primary_muscles=["chest"], equipment_tags=["barbell", "bench"]),
            _exercise("chest-2", primary_muscles=["chest"], equipment_tags=["dumbbells"]),
            _exercise("chest-3", primary_muscles=["chest"], equipment_tags=[]),
        ]
        violations = check_coverage(exercises)
        assert not any("'chest'" in v for v in violations)


class TestCheckDuplicatesAndOrphans:
    def test_duplicate_slug_is_flagged(self):
        exercises = [_exercise("same-slug"), _exercise("same-slug")]
        violations = check_duplicates_and_orphans(exercises)
        assert any("same-slug" in v and "Duplicate" in v for v in violations)

    def test_unique_slugs_are_not_flagged_as_duplicates(self):
        exercises = [_exercise("slug-a"), _exercise("slug-b")]
        violations = check_duplicates_and_orphans(exercises)
        assert not any("Duplicate" in v for v in violations)

    def test_active_exercise_unsatisfiable_in_any_preset_is_an_orphan(self):
        exercise = _exercise("orphan", equipment_tags=["totally_made_up_equipment"])
        violations = check_duplicates_and_orphans([exercise])
        assert any("orphan" in v and "orphaned" in v for v in violations)

    def test_inactive_orphan_equipment_is_not_flagged(self):
        exercise = _exercise("inactive-orphan", equipment_tags=["totally_made_up_equipment"], is_active=False)
        violations = check_duplicates_and_orphans([exercise])
        assert violations == []

    def test_satisfiable_equipment_is_not_an_orphan(self):
        exercise = _exercise("fine", equipment_tags=["barbell"])
        violations = check_duplicates_and_orphans([exercise])
        assert violations == []


class TestLintLibrary:
    def test_concatenates_all_four_checks(self):
        exercises = [_exercise("dup", equipment_tags=["not_a_real_tag"]), _exercise("dup")]
        violations = lint_library(exercises, [])
        assert any("Duplicate" in v for v in violations)
        assert any("equipment_tags" in v for v in violations)

    def test_empty_input_has_no_schema_or_duplicate_violations(self):
        violations = lint_library([], [])
        assert not any("Duplicate" in v or "invalid" in v for v in violations)


@pytest.mark.asyncio
async def test_real_seeded_catalog_passes_lint(db_session, seeded_templates, seeded_exercises):
    """CI-facing test: the real seed data must have zero lint violations.

    Uses ALL exercise rows (not just active) for schema-validity/duplicate
    checks per the linter's contract, and the active-only seeded_exercises
    fixture output for reachability/coverage via lint_library's own
    is_active filtering.
    """
    all_exercises = list((await db_session.execute(select(Exercise))).scalars().all())
    templates = list((await db_session.execute(select(ProgramTemplate))).scalars().all())

    violations = lint_library(all_exercises, templates)
    assert violations == [], "\n".join(violations)
