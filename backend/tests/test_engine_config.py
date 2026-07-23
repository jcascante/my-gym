import pytest
import yaml
from pydantic import ValidationError

from app.services.program.engine_config import (
    _CONFIG_PATH,
    AssemblyConfig,
    EngineConfig,
    EngineFlags,
    MatchConfig,
    SelectionConfig,
    VolumeBandRow,
    VolumeBandsConfig,
    VolumeModifiers,
    get_engine_config,
)
from app.services.program.matching import MatchWeights
from app.services.program.selection import SelectionWeights


def test_match_config_mirrors_match_weights_defaults():
    match = MatchConfig()
    weights = MatchWeights()
    assert match.goal == weights.goal
    assert match.experience == weights.experience
    assert match.days == weights.days
    assert match.duration == weights.duration
    assert match.movement_preference == weights.movement_preference
    assert match.focus_complement == weights.focus_complement
    assert match.periodization == weights.periodization


def test_match_config_scorer_kernel_defaults():
    match = MatchConfig()
    assert match.epsilon == 0.10
    assert match.alpha == 1.0
    assert match.beta == 1.0
    assert match.sigma_days == 1.0
    assert match.sigma_duration == 15.0


def test_selection_config_mirrors_selection_weights_defaults():
    selection = SelectionConfig()
    weights = SelectionWeights()
    assert selection.variety == weights.variety
    assert selection.priority_fit == weights.priority_fit
    assert selection.muscle_fit == weights.muscle_fit
    assert selection.difficulty == weights.difficulty
    assert selection.unilateral_balance == weights.unilateral_balance
    assert selection.movement_preference == weights.movement_preference
    assert selection.complementary_coverage == weights.complementary_coverage


def test_selection_config_has_provenance_field():
    selection = SelectionConfig()
    assert selection.provenance == "heuristic"


def test_assembly_config_placeholder_defaults():
    assembly = AssemblyConfig()
    assert assembly.beam_width == 1
    assert assembly.lambda_v == 0.0
    assert assembly.lambda_f == 0.0


def test_flags_default_off():
    flags = EngineFlags()
    assert flags.use_constraint_scorer is False
    assert flags.use_beam_search is False


def test_engine_config_requires_config_version():
    with pytest.raises(ValidationError):
        EngineConfig()  # type: ignore[call-arg]


def test_engine_config_builds_with_only_config_version():
    config = EngineConfig(config_version="1")
    assert config.config_version == "1"
    assert config.match == MatchConfig()
    assert config.selection == SelectionConfig()
    assert config.assembly == AssemblyConfig()
    assert config.flags == EngineFlags()


def test_engine_yaml_file_exists_and_parses():
    assert _CONFIG_PATH.exists()
    with open(_CONFIG_PATH) as f:
        raw = yaml.safe_load(f)
    assert raw["config_version"] == "1"


def test_engine_yaml_round_trips_to_code_level_defaults():
    with open(_CONFIG_PATH) as f:
        raw = yaml.safe_load(f)
    from_yaml = EngineConfig.model_validate(raw)
    from_code = EngineConfig(config_version="1")
    assert from_yaml == from_code


def test_get_engine_config_returns_validated_engine_config():
    config = get_engine_config()
    assert isinstance(config, EngineConfig)
    assert config.config_version == "1"
    assert config.flags.use_constraint_scorer is False
    assert config.flags.use_beam_search is False


def test_get_engine_config_is_cached_singleton():
    assert get_engine_config() is get_engine_config()


def test_volume_modifiers_default_values():
    modifiers = VolumeModifiers()
    assert modifiers.emphasis_target_bonus_min == 2
    assert modifiers.emphasis_target_bonus_max == 4
    assert modifiers.amber_injury_guard_reduction_pct == 0.30


def test_volume_band_row_rejects_invalid_ordering_target_min_greater_than_max():
    with pytest.raises(ValidationError):
        VolumeBandRow(
            experience="beginner",
            mev=6,
            target_min=13,  # Invalid: greater than target_max
            target_max=12,
            mrv_guard=16,
            citation="test",
        )


def test_volume_band_row_rejects_invalid_ordering_mev_greater_than_target_min():
    with pytest.raises(ValidationError):
        VolumeBandRow(
            experience="beginner",
            mev=9,  # Invalid: greater than target_min
            target_min=8,
            target_max=12,
            mrv_guard=16,
            citation="test",
        )


def test_volume_band_row_rejects_invalid_ordering_target_max_greater_than_mrv():
    with pytest.raises(ValidationError):
        VolumeBandRow(
            experience="beginner",
            mev=6,
            target_min=8,
            target_max=17,  # Invalid: greater than mrv_guard
            mrv_guard=16,
            citation="test",
        )


def test_volume_band_row_accepts_valid_ordering():
    row = VolumeBandRow(
        experience="beginner",
        mev=6,
        target_min=8,
        target_max=12,
        mrv_guard=16,
        citation="test",
    )
    assert row.mev == 6
    assert row.target_min == 8
    assert row.target_max == 12
    assert row.mrv_guard == 16


def test_volume_bands_config_creates_with_defaults():
    config = VolumeBandsConfig(bands=[])
    assert config.bands == []
    assert config.modifiers == VolumeModifiers()


def test_engine_config_has_volume_bands_field():
    config = EngineConfig(config_version="1")
    assert hasattr(config, "volume_bands")
    assert isinstance(config.volume_bands, VolumeBandsConfig)


def test_engine_config_volume_bands_has_all_three_experience_levels():
    config = EngineConfig(config_version="1")
    experiences = {band.experience for band in config.volume_bands.bands}
    assert experiences == {"beginner", "intermediate", "advanced"}


def test_volume_band_rows_have_correct_values():
    config = EngineConfig(config_version="1")
    bands_by_exp = {band.experience: band for band in config.volume_bands.bands}

    # Check beginner
    beginner = bands_by_exp["beginner"]
    assert beginner.mev == 6
    assert beginner.target_min == 8
    assert beginner.target_max == 12
    assert beginner.mrv_guard == 16

    # Check intermediate
    intermediate = bands_by_exp["intermediate"]
    assert intermediate.mev == 8
    assert intermediate.target_min == 10
    assert intermediate.target_max == 18
    assert intermediate.mrv_guard == 22

    # Check advanced
    advanced = bands_by_exp["advanced"]
    assert advanced.mev == 10
    assert advanced.target_min == 12
    assert advanced.target_max == 20
    assert advanced.mrv_guard == 26


def test_volume_band_rows_have_citation():
    config = EngineConfig(config_version="1")
    for band in config.volume_bands.bands:
        assert band.citation
        assert len(band.citation) > 0


def test_volume_band_rows_all_have_same_citation():
    config = EngineConfig(config_version="1")
    citations = {band.citation for band in config.volume_bands.bands}
    assert len(citations) == 1  # All rows should have the same citation


def test_engine_yaml_round_trips_volume_bands():
    with open(_CONFIG_PATH) as f:
        raw = yaml.safe_load(f)
    from_yaml = EngineConfig.model_validate(raw)
    from_code = EngineConfig(config_version="1")
    assert from_yaml.volume_bands == from_code.volume_bands
