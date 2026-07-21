"""Regression/progression graph config (plan §3.3, proposal §5.1/§5.2).

Loaded from `config/regression_graphs.yaml` - reviewed via PR, deployable without a
code change (same pattern as `engine_config.py`). Each movement pattern lists edges
from a "main" exercise slug to a substitute slug: `regression` edges stay within the
same pattern and are tried first (nearest permissible variant); `cross_pattern` edges
switch to a different pattern and are tried only if no regression relieves the
offending provocation. `relieves` names the Provocation axis/axes the substitute
addresses - authored judgment, not required to match `derive_provocation_tags`'
first-pass heuristic (app/db/seed/exercise_classification.py), which is deliberately
coarse (see task 3.1) and doesn't capture every real biomechanical nuance a human
reviewer would.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.exercise import MovementPattern, Provocation

_CONFIG_PATH = Path(__file__).parent / "config" / "regression_graphs.yaml"


class RegressionEdge(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    from_slug: str = Field(alias="from")
    to: str
    kind: Literal["regression", "cross_pattern"]
    relieves: list[Provocation]


class RegressionGraphsConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    config_version: str
    rehabilitating_load_multiplier: float = 0.8
    patterns: dict[str, list[RegressionEdge]] = {}

    @model_validator(mode="after")
    def _valid_pattern_keys(self) -> Self:
        valid = {p.value for p in MovementPattern}
        invalid = set(self.patterns) - valid
        if invalid:
            raise ValueError(f"regression_graphs.yaml: unknown movement pattern key(s) {sorted(invalid)}")
        return self


@lru_cache(maxsize=1)
def get_regression_graphs() -> RegressionGraphsConfig:
    """Load and validate `config/regression_graphs.yaml`. Cached: read once per process."""
    with open(_CONFIG_PATH) as f:
        raw = yaml.safe_load(f)
    return RegressionGraphsConfig.model_validate(raw)
