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
from typing import Literal, Self

import yaml
from pydantic import BaseModel, ConfigDict, model_validator

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
    """Beam-search assembly-objective scoring weights (plan §1.5/§2.5) — inert until
    `flags.use_beam_search`. `lambda_v`/`lambda_f` only affect beam-search candidate
    scoring; they do not gate the post-draft volume validator (a separate mechanism,
    gated by its own `flags.use_volume_validator`)."""

    model_config = ConfigDict(frozen=True)

    beam_width: int = 1
    lambda_v: float = 0.0
    lambda_f: float = 0.0


class EngineFlags(BaseModel):
    model_config = ConfigDict(frozen=True)

    use_constraint_scorer: bool = False
    use_beam_search: bool = False
    use_volume_validator: bool = False
    use_frequency_advisories: bool = False
    use_interference_scheduler: bool = False
    use_safety_substitution: bool = False


class VolumeBandRow(BaseModel):
    """Volume band row (MEV / target / MRV) per experience level (plan §2.4).

    Enforces ordering: MEV <= target_min <= target_max <= MRV guard.
    """

    model_config = ConfigDict(frozen=True)

    experience: Literal["beginner", "intermediate", "advanced"]
    mev: int
    target_min: int
    target_max: int
    mrv_guard: int
    citation: str

    @model_validator(mode="after")
    def _ordering(self) -> Self:
        # All four fields are present by the time an "after" validator runs, unlike
        # per-field validators (which only see earlier-declared fields) — that
        # distinction previously left some cross-field checks unreachable dead code.
        if not (self.mev <= self.target_min <= self.target_max <= self.mrv_guard):
            raise ValueError(
                f"volume band ordering violated: mev ({self.mev}) <= target_min ({self.target_min}) "
                f"<= target_max ({self.target_max}) <= mrv_guard ({self.mrv_guard}) must hold"
            )
        return self


class VolumeModifiers(BaseModel):
    """Volume band modifiers (plan §2.4)."""

    model_config = ConfigDict(frozen=True)

    emphasis_target_bonus_min: int = 2
    emphasis_target_bonus_max: int = 4
    amber_injury_guard_reduction_pct: float = 0.30


class VolumeBandsConfig(BaseModel):
    """Volume bands config surface (plan §2.4).

    Bands table (MEV / target / MRV guard by experience) plus modifiers.
    """

    model_config = ConfigDict(frozen=True)

    bands: list[VolumeBandRow]
    modifiers: VolumeModifiers = VolumeModifiers()


class EngineConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    config_version: str
    match: MatchConfig = MatchConfig()
    selection: SelectionConfig = SelectionConfig()
    assembly: AssemblyConfig = AssemblyConfig()
    flags: EngineFlags = EngineFlags()
    volume_bands: VolumeBandsConfig = VolumeBandsConfig(
        bands=[
            VolumeBandRow(
                experience="beginner",
                mev=6,
                target_min=8,
                target_max=12,
                mrv_guard=16,
                citation="Schoenfeld, Ogborn & Krieger (2017), dose-response of weekly set volume and hypertrophy, J Sports Sci; Schoenfeld et al. (2019), volume and hypertrophy in trained men, MSSE; Israetel et al., MEV/MAV/MRV volume landmarks framework, Renaissance Periodization; Ralston et al. (2017), weekly set volume and strength gain, Sports Med.",
            ),
            VolumeBandRow(
                experience="intermediate",
                mev=8,
                target_min=10,
                target_max=18,
                mrv_guard=22,
                citation="Schoenfeld, Ogborn & Krieger (2017), dose-response of weekly set volume and hypertrophy, J Sports Sci; Schoenfeld et al. (2019), volume and hypertrophy in trained men, MSSE; Israetel et al., MEV/MAV/MRV volume landmarks framework, Renaissance Periodization; Ralston et al. (2017), weekly set volume and strength gain, Sports Med.",
            ),
            VolumeBandRow(
                experience="advanced",
                mev=10,
                target_min=12,
                target_max=20,
                mrv_guard=26,
                citation="Schoenfeld, Ogborn & Krieger (2017), dose-response of weekly set volume and hypertrophy, J Sports Sci; Schoenfeld et al. (2019), volume and hypertrophy in trained men, MSSE; Israetel et al., MEV/MAV/MRV volume landmarks framework, Renaissance Periodization; Ralston et al. (2017), weekly set volume and strength gain, Sports Med.",
            ),
        ]
    )


@lru_cache(maxsize=1)
def get_engine_config() -> EngineConfig:
    """Load and validate `config/engine.yaml`. Cached: the file is read once per process.

    Usable as a FastAPI dependency: `Depends(get_engine_config)`.
    """
    with open(_CONFIG_PATH) as f:
        raw = yaml.safe_load(f)
    return EngineConfig.model_validate(raw)
