"""Program engine config surface (plan §1.1).

Values are loaded from `config/engine.yaml` — reviewed via PR, deployable without a code
change. Defaults mirror today's hardcoded scoring (`matching.MatchWeights`,
`selection.SelectionWeights`) exactly, so introducing this module changes zero runtime
behavior. `AssemblyConfig` and `MatchConfig`'s kernel fields (epsilon/alpha/beta/sigma_*)
are placeholders consumed by later tasks (plan §1.3/§1.4/§1.5); `flags` gates them off
until those tasks land.
"""

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict

_CONFIG_PATH = Path(__file__).parent / "config" / "engine.yaml"


class MatchConfig(BaseModel):
    """Template-matching weights (`matching.HeuristicTemplateScorer`) plus the
    constraint-tiered scorer's kernel parameters (plan §1.3/§1.4, unused until then)."""

    model_config = ConfigDict(frozen=True)

    goal: float = 0.25
    experience: float = 0.20
    days: float = 0.12
    duration: float = 0.08
    movement_preference: float = 0.15
    focus_complement: float = 0.12
    periodization: float = 0.08

    # fit = max(goal, epsilon)^alpha * max(experience, epsilon)^beta * soft (plan §1.3).
    epsilon: float = 0.10
    alpha: float = 1.0
    beta: float = 1.0

    # Gaussian kernel sigmas replacing `_range_fit` (plan §1.4).
    sigma_days: float = 1.0
    sigma_duration: float = 15.0


class SelectionConfig(BaseModel):
    """Exercise-selection weights (`selection.HeuristicExerciseScorer`).

    `provenance` records where the weights came from ("heuristic" hand-tuned defaults vs.
    a trained candidate set, plan §2.4) — informational only in this task.
    """

    model_config = ConfigDict(frozen=True)

    variety: float = 1.0
    priority_fit: float = 1.5
    muscle_fit: float = 1.0
    difficulty: float = 0.75
    unilateral_balance: float = 0.5
    movement_preference: float = 1.25
    complementary_coverage: float = 1.25
    provenance: str = "heuristic"


class AssemblyConfig(BaseModel):
    """Beam-search assembly placeholders (plan §1.5/§2.5) — inert until `flags.use_beam_search`."""

    model_config = ConfigDict(frozen=True)

    beam_width: int = 1
    lambda_v: float = 0.0
    lambda_f: float = 0.0


class EngineFlags(BaseModel):
    model_config = ConfigDict(frozen=True)

    use_constraint_scorer: bool = False
    use_beam_search: bool = False


class EngineConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    config_version: str
    match: MatchConfig = MatchConfig()
    selection: SelectionConfig = SelectionConfig()
    assembly: AssemblyConfig = AssemblyConfig()
    flags: EngineFlags = EngineFlags()


@lru_cache(maxsize=1)
def get_engine_config() -> EngineConfig:
    """Load and validate `config/engine.yaml`. Cached: the file is read once per process.

    Usable as a FastAPI dependency: `Depends(get_engine_config)`.
    """
    with open(_CONFIG_PATH) as f:
        raw = yaml.safe_load(f)
    return EngineConfig.model_validate(raw)
