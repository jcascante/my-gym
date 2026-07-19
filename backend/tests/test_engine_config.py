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
