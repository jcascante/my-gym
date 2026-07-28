"""Tests for Phase 4 Task 4.5: template/model versioning.

Covers `app.services.program.versioning` (version resolution + reading the ranking
weights artifact), `get_model`'s version-aware lookup, `build_draft` stamping pinned
versions onto new programs, and `derive_week` accepting + falling back on them.
"""

import json
from pathlib import Path

import pytest

from app.core.constants import CURRENT_PROGRESSION_MODEL_VERSION, DEFAULT_RANKING_WEIGHTS_VERSION
from app.models import WorkoutProgram
from app.schemas.template import TemplateDefinition
from app.services.program.drafting import build_draft
from app.services.program.preview import derive_week
from app.services.program.progression.base import SetScheme, SlotBase, get_model, register
from app.services.program.selection import SelectionContext
from app.services.program.versioning import (
    get_current_model_version,
    get_current_ranking_weights_version,
    resolve_program_versions,
)


def _program(**overrides: object) -> WorkoutProgram:
    defaults: dict[str, object] = dict(
        user_id=1,
        template_id=1,
        environment_id=1,
        name="Test Program",
        duration_weeks=8,
        days_per_week=3,
        weight_unit="kg",
        constraints={},
    )
    defaults.update(overrides)
    return WorkoutProgram(**defaults)  # type: ignore[arg-type]


class TestGetCurrentModelVersion:
    def test_returns_the_constant(self) -> None:
        assert get_current_model_version() == CURRENT_PROGRESSION_MODEL_VERSION


class TestGetCurrentRankingWeightsVersion:
    def test_falls_back_when_file_missing(self, tmp_path: Path) -> None:
        missing = tmp_path / "does_not_exist.json"

        assert get_current_ranking_weights_version(missing) == DEFAULT_RANKING_WEIGHTS_VERSION

    def test_falls_back_when_file_is_malformed_json(self, tmp_path: Path) -> None:
        bad = tmp_path / "weights.json"
        bad.write_text("not json{")

        assert get_current_ranking_weights_version(bad) == DEFAULT_RANKING_WEIGHTS_VERSION

    def test_falls_back_when_metadata_field_is_missing(self, tmp_path: Path) -> None:
        """A pre-4.5 artifact (Task 4.4's shape) with no `_metadata` at all."""
        legacy = tmp_path / "weights.json"
        legacy.write_text(json.dumps({"weights": {"1": 0.1}, "pair_scores": {}}))

        assert get_current_ranking_weights_version(legacy) == DEFAULT_RANKING_WEIGHTS_VERSION

    def test_reads_weights_version_from_metadata(self, tmp_path: Path) -> None:
        artifact = tmp_path / "weights.json"
        artifact.write_text(json.dumps({"weights": {}, "_metadata": {"weights_version": "20260401T000000Z"}}))

        assert get_current_ranking_weights_version(artifact) == "20260401T000000Z"


class TestResolveProgramVersions:
    def test_no_program_no_overrides_uses_current_versions(self, tmp_path: Path) -> None:
        missing_weights = tmp_path / "missing.json"

        model_version, ranking_weights_version = resolve_program_versions(weights_path=missing_weights)

        assert model_version == CURRENT_PROGRESSION_MODEL_VERSION
        assert ranking_weights_version == DEFAULT_RANKING_WEIGHTS_VERSION

    def test_explicit_overrides_win_over_everything(self, tmp_path: Path) -> None:
        program = _program(model_version="9.9", ranking_weights_version="live-version")

        model_version, ranking_weights_version = resolve_program_versions(
            program,
            model_version="pinned-model",
            ranking_weights_version="pinned-weights",
            weights_path=tmp_path / "missing.json",
        )

        assert model_version == "pinned-model"
        assert ranking_weights_version == "pinned-weights"

    def test_stored_program_versions_win_over_current(self, tmp_path: Path) -> None:
        program = _program(model_version="0.9-legacy", ranking_weights_version="2026-01-01T00:00:00Z")

        model_version, ranking_weights_version = resolve_program_versions(
            program, weights_path=tmp_path / "missing.json"
        )

        assert model_version == "0.9-legacy"
        assert ranking_weights_version == "2026-01-01T00:00:00Z"

    def test_backward_compat_null_program_versions_fall_back_to_current(self, tmp_path: Path) -> None:
        """Existing (pre-4.5) programs have both columns null; resolution must not
        crash and must fall back to the live/current versions."""
        program = _program(model_version=None, ranking_weights_version=None)

        model_version, ranking_weights_version = resolve_program_versions(
            program, weights_path=tmp_path / "missing.json"
        )

        assert model_version == CURRENT_PROGRESSION_MODEL_VERSION
        assert ranking_weights_version == DEFAULT_RANKING_WEIGHTS_VERSION


class TestGetModelVersionAware:
    def _register_dummy(self) -> None:
        class Dummy:
            key = "versioning_dummy"

            def resolve(self, base: SlotBase, week: int, params: dict[str, object]) -> SetScheme:
                return SetScheme(
                    sets=base.sets, reps=base.reps_min, load=base.base_load, rest_seconds=base.rest_seconds
                )

        register(Dummy())

    def test_falls_back_to_bare_key_when_no_versioned_entry_registered(self) -> None:
        self._register_dummy()

        model = get_model("versioning_dummy", "1.0")

        assert model.key == "versioning_dummy"

    def test_prefers_versioned_entry_when_registered(self) -> None:
        self._register_dummy()

        class DummyV2:
            key = "versioning_dummy@2.0"

            def resolve(self, base: SlotBase, week: int, params: dict[str, object]) -> SetScheme:
                return SetScheme(sets=99, reps=base.reps_min, load=base.base_load, rest_seconds=base.rest_seconds)

        register(DummyV2())

        model = get_model("versioning_dummy", "2.0")
        out = model.resolve(SlotBase(sets=3, reps_min=5, reps_max=5, rest_seconds=120, base_load=60.0), 1, {})

        assert out.sets == 99

    def test_unknown_key_still_raises(self) -> None:
        with pytest.raises(KeyError):
            get_model("definitely_not_registered", "1.0")


@pytest.mark.asyncio
class TestBuildDraftStampsVersions:
    async def test_defaults_to_current_versions_when_unspecified(self, sample_template_orm, sample_exercises, tmp_path):
        definition = TemplateDefinition.from_orm_template(sample_template_orm)
        ctx = SelectionContext(
            equipment=["barbell", "bench", "squat_rack"],
            experience="intermediate",
            injuries=[],
            used_movement_slugs=set(),
        )
        program = build_draft(
            sample_template_orm,
            definition,
            ctx,
            sample_exercises,
            user_id=1,
            environment_id=1,
            days_per_week=3,
            duration_weeks=8,
            weight_unit="kg",
            required_inputs={"squat_start": 80},
        )

        assert program.model_version == CURRENT_PROGRESSION_MODEL_VERSION
        assert program.ranking_weights_version == DEFAULT_RANKING_WEIGHTS_VERSION

    async def test_honors_explicit_pinned_versions(self, sample_template_orm, sample_exercises):
        definition = TemplateDefinition.from_orm_template(sample_template_orm)
        ctx = SelectionContext(
            equipment=["barbell", "bench", "squat_rack"],
            experience="intermediate",
            injuries=[],
            used_movement_slugs=set(),
        )
        program = build_draft(
            sample_template_orm,
            definition,
            ctx,
            sample_exercises,
            user_id=1,
            environment_id=1,
            days_per_week=3,
            duration_weeks=8,
            weight_unit="kg",
            required_inputs={"squat_start": 80},
            model_version="1.0-pinned",
            ranking_weights_version="weights-abc123",
        )

        assert program.model_version == "1.0-pinned"
        assert program.ranking_weights_version == "weights-abc123"


@pytest.mark.asyncio
class TestDeriveWeekDeterminism:
    def _built_program(self, sample_template_orm, sample_exercises, definition, **draft_kwargs):
        ctx = SelectionContext(["barbell", "bench", "squat_rack"], "intermediate", [], set())
        program = build_draft(
            sample_template_orm,
            definition,
            ctx,
            sample_exercises,
            user_id=1,
            environment_id=1,
            days_per_week=3,
            duration_weeks=8,
            weight_unit="kg",
            required_inputs={"squat_start": 80},
            **draft_kwargs,
        )
        for w in program.workouts:
            w.id = w.order
            for j, ex in enumerate(w.exercises, 1):
                ex.id = j
        return program

    async def test_same_pinned_versions_produce_identical_output(self, sample_template_orm, sample_exercises):
        """Same user + same pinned versions -> byte-identical program preview."""
        definition = TemplateDefinition.from_orm_template(sample_template_orm)
        program = self._built_program(
            sample_template_orm,
            sample_exercises,
            definition,
            model_version="1.0",
            ranking_weights_version="weights-v1",
        )
        exercise_map = {e.id: e for e in sample_exercises}

        first = derive_week(program, definition, 1, exercise_map)
        second = derive_week(program, definition, 1, exercise_map)

        assert first == second

    async def test_explicit_version_params_match_programs_stored_versions(self, sample_template_orm, sample_exercises):
        """Passing the same versions explicitly as derive_week() args produces the
        same output as relying on the program's own stored pins."""
        definition = TemplateDefinition.from_orm_template(sample_template_orm)
        program = self._built_program(
            sample_template_orm,
            sample_exercises,
            definition,
            model_version="1.0",
            ranking_weights_version="weights-v1",
        )
        exercise_map = {e.id: e for e in sample_exercises}

        from_program = derive_week(program, definition, 1, exercise_map)
        from_explicit_args = derive_week(
            program, definition, 1, exercise_map, model_version="1.0", ranking_weights_version="weights-v1"
        )

        assert from_program == from_explicit_args

    async def test_backward_compat_null_program_versions_still_derive_a_week(
        self, sample_template_orm, sample_exercises
    ):
        """A program predating these columns (both null) must still preview fine,
        falling back to the current/live versions rather than raising."""
        definition = TemplateDefinition.from_orm_template(sample_template_orm)
        program = self._built_program(sample_template_orm, sample_exercises, definition)
        program.model_version = None
        program.ranking_weights_version = None
        exercise_map = {e.id: e for e in sample_exercises}

        days = derive_week(program, definition, 1, exercise_map)

        assert len(days) == len(program.workouts)
        assert any(slot["load"] is not None for day in days for slot in day["slots"])
