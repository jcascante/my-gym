"""Offline Bradley-Terry learner for exercise substitution ranking (Phase 4, Task 4.4).

Learns, from a history of user-initiated exercise swaps, which substitutions tend
to "work" (the user completes the swapped-in exercise as prescribed) versus which
tend to fail. Fitted per-exercise strengths and derived pairwise scores are written
to a JSON artifact for later stages (Task 4.5 template/model versioning) to load --
this script does not wire into live program generation.

**Schema assumption (flagged, not yet modeled):** no `ExerciseSwapLog` table/ORM
model exists in `app/models` today. This script assumes one will exist named
`exercise_swap_logs` with columns `(user_id, original_exercise_id, swap_exercise_id,
session_date, completed, rpe_feedback)`, matching the shape of `SwapRecord` below.
`load_swap_history_from_db` queries it by name (not via an ORM model, since none
exists) and degrades to an empty result with a warning if the table is missing, so
a scheduled run doesn't hard-crash before the table is introduced.

Run directly (loads the real DB and writes the weights artifact):

    uv run python -m scripts.train_rank_weights [--output PATH]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import math
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session

logger = logging.getLogger(__name__)

# Below this many total swap records, there isn't enough signal for a stable
# Bradley-Terry fit; fall back to uniform (zero) weights rather than overfit noise.
MIN_SWAPS_TO_TRAIN = 10

# L2 penalty keeps unregularized weights from diverging on near-separable data and,
# combined with the +1/-1 comparison encoding (no intercept), pulls the fitted
# strengths toward a zero-sum reference point -- standard Bradley-Terry-via-logistic-
# regression identifiability trick.
_L2_PENALTY_C = 1.0
_MAX_ITER = 1000
RANDOM_STATE = 42

DEFAULT_OUTPUT_PATH = Path(__file__).resolve().parents[1] / "data" / "exercise_substitution_weights.json"


@dataclass(frozen=True)
class SwapRecord:
    """One observed exercise-substitution event.

    `completed=True` is treated as the swap "winning" its pairwise Bradley-Terry
    comparison against the original exercise; `completed=False` means the user
    did not finish the session with the substitution (a loss for the swap).
    """

    user_id: int
    original_exercise_id: int
    swap_exercise_id: int
    session_date: datetime
    completed: bool
    rpe_feedback: float | None = None


def _default_weights_version() -> str:
    # A label for *which run* produced the artifact (Task 4.5: template/model
    # versioning), not a hyperparameter of the fit itself -- deliberately kept out of
    # `RankWeights`/`to_json_dict()` so the fit stays a pure, byte-deterministic
    # function of its input records; only `write_weights` (an inherently time-stamped
    # side effect) stamps a version onto the persisted artifact.
    return datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")


@dataclass(frozen=True)
class RankWeights:
    """Fitted (or degraded-to-uniform) Bradley-Terry output."""

    weights: dict[int, float]
    pair_scores: dict[str, float]
    n_swaps: int
    n_exercises: int
    sufficient_data: bool
    reason: str | None = None

    def to_json_dict(self) -> dict[str, object]:
        return {
            "sufficient_data": self.sufficient_data,
            "reason": self.reason,
            "n_swaps": self.n_swaps,
            "n_exercises": self.n_exercises,
            "weights": {str(exercise_id): weight for exercise_id, weight in sorted(self.weights.items())},
            "pair_scores": dict(sorted(self.pair_scores.items())),
        }


def _sigmoid(z: float) -> float:
    # Guard against overflow on extreme (degenerate-data) weight differences;
    # math.exp(-z) overflows silently to inf for large negative z, which is fine,
    # but very large positive z would raise OverflowError without this split.
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    exp_z = math.exp(z)
    return exp_z / (1.0 + exp_z)


def _sort_key(record: SwapRecord) -> tuple[int, str, int, int]:
    return (record.user_id, record.session_date.isoformat(), record.original_exercise_id, record.swap_exercise_id)


def _uniform_result(exercise_ids: list[int], n_swaps: int, reason: str, message: str, *args: object) -> RankWeights:
    logger.warning(message, *args)
    return RankWeights(
        weights=dict.fromkeys(exercise_ids, 0.0),
        pair_scores={},
        n_swaps=n_swaps,
        n_exercises=len(exercise_ids),
        sufficient_data=False,
        reason=reason,
    )


def fit_bradley_terry(records: Sequence[SwapRecord]) -> RankWeights:
    """Fit per-exercise Bradley-Terry strengths from a history of swap outcomes.

    Deterministic: fixed `random_state`, records are sorted before the design
    matrix is built (so column/row order -- and therefore the fit -- doesn't
    depend on input ordering), and outputs are rounded to 6 decimal places.

    Degrades gracefully (uniform zero weights + a logged warning, never raises)
    when there isn't enough data to fit a meaningful ranking: no records, fewer
    than `MIN_SWAPS_TO_TRAIN`, every swap comparing an exercise to itself, or
    every outcome being identical (no contrast for logistic regression to learn).
    """
    if not records:
        return _uniform_result([], 0, "no_data", "No swap records provided; returning uniform (empty) weights.")

    ordered = sorted(records, key=_sort_key)
    exercise_ids = sorted({r.original_exercise_id for r in ordered} | {r.swap_exercise_id for r in ordered})

    if len(ordered) < MIN_SWAPS_TO_TRAIN:
        return _uniform_result(
            exercise_ids,
            len(ordered),
            "insufficient_data",
            "Only %d swap record(s) found (minimum %d); using uniform weights.",
            len(ordered),
            MIN_SWAPS_TO_TRAIN,
        )

    distinct_pairs = {
        (r.original_exercise_id, r.swap_exercise_id) for r in ordered if r.original_exercise_id != r.swap_exercise_id
    }
    if not distinct_pairs:
        return _uniform_result(
            exercise_ids,
            len(ordered),
            "degenerate_pairs",
            "All swap records compare an exercise to itself; cannot rank. Using uniform weights.",
        )

    labels = {r.completed for r in ordered}
    if len(labels) < 2:
        return _uniform_result(
            exercise_ids,
            len(ordered),
            "single_class",
            "All swap outcomes are identical (completed=%s for every record); Bradley-Terry "
            "needs both outcomes to learn a contrast. Using uniform weights.",
            next(iter(labels)),
        )

    index = {exercise_id: position for position, exercise_id in enumerate(exercise_ids)}
    x = np.zeros((len(ordered), len(exercise_ids)))
    y = np.zeros(len(ordered), dtype=int)
    for row, record in enumerate(ordered):
        x[row, index[record.swap_exercise_id]] += 1.0
        x[row, index[record.original_exercise_id]] -= 1.0
        y[row] = 1 if record.completed else 0

    model = LogisticRegression(
        # L2 is already the default penalty; left implicit since sklearn 1.8+
        # deprecates the explicit `penalty="l2"` spelling in favor of `l1_ratio`.
        C=_L2_PENALTY_C,
        fit_intercept=False,
        solver="lbfgs",
        max_iter=_MAX_ITER,
        random_state=RANDOM_STATE,
    )
    model.fit(x, y)
    coefficients = model.coef_[0]
    weights = {exercise_id: round(float(coefficients[index[exercise_id]]), 6) for exercise_id in exercise_ids}

    pair_scores = {
        f"{original}->{swap}": round(_sigmoid(weights[swap] - weights[original]), 6)
        for original, swap in sorted(distinct_pairs)
    }

    return RankWeights(
        weights=weights,
        pair_scores=pair_scores,
        n_swaps=len(ordered),
        n_exercises=len(exercise_ids),
        sufficient_data=True,
        reason=None,
    )


async def load_swap_history_from_db(session: AsyncSession) -> list[SwapRecord]:
    """Load swap events from the (assumed) `exercise_swap_logs` table.

    Queried by raw SQL rather than an ORM model since none exists yet -- see the
    module docstring. Missing-table errors are caught and logged rather than
    propagated, so a scheduled run doesn't crash before the table is added.
    """
    try:
        result = await session.execute(
            text(
                "SELECT user_id, original_exercise_id, swap_exercise_id, session_date, "
                "completed, rpe_feedback FROM exercise_swap_logs"
            )
        )
    except (ProgrammingError, OperationalError) as exc:
        logger.warning("exercise_swap_logs table not available (%s); skipping training run.", exc)
        await session.rollback()
        return []

    records = []
    for row in result.mappings():
        session_date = row["session_date"]
        # Raw `text()` queries skip SQLAlchemy's column type coercion, so SQLite
        # (used in tests) hands back an ISO string where Postgres (production)
        # already hands back a native datetime.
        if isinstance(session_date, str):
            session_date = datetime.fromisoformat(session_date)
        records.append(
            SwapRecord(
                user_id=row["user_id"],
                original_exercise_id=row["original_exercise_id"],
                swap_exercise_id=row["swap_exercise_id"],
                session_date=session_date,
                completed=bool(row["completed"]),
                rpe_feedback=row["rpe_feedback"],
            )
        )
    return records


def write_weights(weights: RankWeights, output_path: Path, *, weights_version: str | None = None) -> None:
    """Persist `weights` as JSON, plus a Task 4.5 `_metadata.weights_version` label
    identifying this training run -- read back by
    `app.services.program.versioning.get_current_ranking_weights_version` so a newly
    generated `WorkoutProgram` can pin to whichever artifact was live at draft time."""
    payload = weights.to_json_dict()
    payload["_metadata"] = {"weights_version": weights_version or _default_weights_version()}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


async def _load_and_fit() -> RankWeights:
    async with async_session() as db:
        records = await load_swap_history_from_db(db)
    return fit_bradley_terry(records)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Train Bradley-Terry exercise substitution weights offline (Task 4.4)."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Path to write the substitution weights JSON artifact.",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO)
    result = asyncio.run(_load_and_fit())
    write_weights(result, args.output)

    if result.sufficient_data:
        print(
            f"Trained Bradley-Terry weights for {result.n_exercises} exercise(s) "
            f"from {result.n_swaps} swap(s) -> {args.output}"
        )
    else:
        print(f"Insufficient/degenerate data (reason={result.reason}); wrote uniform " f"weights to {args.output}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
