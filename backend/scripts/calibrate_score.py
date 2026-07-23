"""Offline isotonic regression learner for RPE calibration (Phase 4, Task 4.6).

Learns, from a history of prescribed target RPE vs. actual logged RPE per workout session,
a monotonic calibration function that maps predicted RPE → calibrated (expected) RPE.
This enables accurate confidence intervals and risk assessments for adaptive program
modifications.

Uses isotonic regression (sklearn) to fit a monotonically increasing function, with
graceful degradation to identity (1:1 mapping) when insufficient data or errors occur.

Run directly (loads the real DB and writes the calibration artifact):

    python -m app.scripts.calibrate_score [--output-path PATH] [--lookback-days N]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import math
import sys
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.isotonic import IsotonicRegression
from sqlalchemy import func, select, text
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session
from app.models import UserWorkoutLog, WorkoutSetLog

logger = logging.getLogger(__name__)

# Minimum number of complete (target + actual RPE) sessions to train on.
# Below this, we return the identity function with a warning.
MIN_SESSIONS_TO_TRAIN = 20

# Identity calibration function: predicted RPE maps 1:1 to calibrated RPE.
# Used when insufficient data or errors occur.
DEFAULT_CALIBRATION = [
    {"predicted_rpe": 0.0, "calibrated_rpe": 0.0},
    {"predicted_rpe": 5.0, "calibrated_rpe": 5.0},
    {"predicted_rpe": 10.0, "calibrated_rpe": 10.0},
]

DEFAULT_OUTPUT_PATH = Path(__file__).resolve().parents[1] / "data" / "rpe_calibration.json"


def _default_calibration_version() -> str:
    """Generate a version label for the calibration artifact.

    Similar to Task 4.4's pattern: includes timestamp so artifacts can be versioned.
    """
    return datetime.now(UTC).strftime("%Y-%m-%d_%H%M%S_v1")


@dataclass(frozen=True)
class CalibrationResult:
    """Fitted (or degraded-to-identity) isotonic regression calibration."""

    sufficient_data: bool
    reason: str | None
    n_training_samples: int
    source_sessions: int
    fit_details: dict[str, Any]
    calibration_function: list[dict[str, float]]
    fit_residuals: dict[str, float]

    def to_json_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict with version/timestamp metadata."""
        return {
            "calibration_function": self.calibration_function,
            "fit_details": self.fit_details,
            "fit_residuals": self.fit_residuals,
            "generated_at": datetime.now(UTC).isoformat(),
            "reason": self.reason,
            "source_sessions": self.source_sessions,
            "sufficient_data": self.sufficient_data,
            "version": _default_calibration_version(),
        }


def _clamp_rpe(value: float) -> float:
    """Clamp RPE value to [0, 10] range."""
    return max(0.0, min(10.0, value))


def _is_valid_rpe(value: float) -> bool:
    """Check if RPE value is valid (not NaN, not negative, in range)."""
    try:
        return not math.isnan(value) and value >= 0.0 and value <= 10.0
    except (TypeError, ValueError):
        return False


def fit_isotonic_regression(targets: list[float], actuals: list[float]) -> CalibrationResult:
    """Fit isotonic regression to (target_rpe, actual_rpe) pairs.

    Deterministic: fixed `random_state`, inputs sorted before fitting, outputs
    rounded to fixed precision.

    Degrades gracefully (identity function + logged warning, never raises) when:
    - Fewer than MIN_SESSIONS_TO_TRAIN valid pairs
    - All data is invalid/NaN
    - Singular matrix or convergence failure
    """
    if not targets or not actuals or len(targets) != len(actuals):
        logger.warning("Empty or mismatched target/actual RPE lists; using identity calibration.")
        return CalibrationResult(
            sufficient_data=False,
            reason="no_data",
            n_training_samples=0,
            source_sessions=0,
            fit_details={
                "algorithm": "isotonic_regression",
                "error": "empty_or_mismatched_input",
            },
            calibration_function=DEFAULT_CALIBRATION,
            fit_residuals={},
        )

    # Filter to valid pairs
    valid_pairs = [(t, a) for t, a in zip(targets, actuals) if _is_valid_rpe(t) and _is_valid_rpe(a)]

    if len(valid_pairs) < MIN_SESSIONS_TO_TRAIN:
        logger.warning(
            "Only %d valid (target, actual) RPE pairs found (minimum %d); using identity calibration.",
            len(valid_pairs),
            MIN_SESSIONS_TO_TRAIN,
        )
        return CalibrationResult(
            sufficient_data=False,
            reason="insufficient_data",
            n_training_samples=len(valid_pairs),
            source_sessions=len(targets),
            fit_details={
                "algorithm": "isotonic_regression",
                "min_required_samples": MIN_SESSIONS_TO_TRAIN,
            },
            calibration_function=DEFAULT_CALIBRATION,
            fit_residuals={},
        )

    # Sort for determinism
    valid_pairs = sorted(valid_pairs, key=lambda p: (p[0], p[1]))

    targets_clean = np.array([t for t, _ in valid_pairs], dtype=np.float64)
    actuals_clean = np.array([a for _, a in valid_pairs], dtype=np.float64)

    try:
        # Fit isotonic regression: monotonically increasing, clip out-of-bounds predictions
        model = IsotonicRegression(increasing=True, out_of_bounds="clip")
        model.fit(targets_clean, actuals_clean)

        # Generate calibration function by evaluating model at key RPE points
        # Include endpoints and intermediate points for a reasonable resolution
        rpe_points = np.array([0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
        calibrated_rpes = model.predict(rpe_points)

        calibration_function = [
            {"predicted_rpe": round(float(p), 2), "calibrated_rpe": round(float(c), 2)}
            for p, c in zip(rpe_points, calibrated_rpes)
        ]

        # Compute fit statistics
        predictions = model.predict(targets_clean)
        residuals = actuals_clean - predictions
        mae = np.mean(np.abs(residuals))
        rmse = np.sqrt(np.mean(residuals**2))

        fit_details = {
            "algorithm": "isotonic_regression",
            "n_training_samples": len(valid_pairs),
            "min_target_rpe": round(float(np.min(targets_clean)), 2),
            "max_target_rpe": round(float(np.max(targets_clean)), 2),
            "mean_actual_rpe": round(float(np.mean(actuals_clean)), 2),
            "std_actual_rpe": round(float(np.std(actuals_clean)), 2),
        }

        fit_residuals = {
            "mean_absolute_error": round(float(mae), 4),
            "rmse": round(float(rmse), 4),
        }

        return CalibrationResult(
            sufficient_data=True,
            reason=None,
            n_training_samples=len(valid_pairs),
            source_sessions=len(targets),
            fit_details=fit_details,
            calibration_function=calibration_function,
            fit_residuals=fit_residuals,
        )

    except Exception as exc:
        logger.error("Isotonic regression fitting failed (%s); using identity calibration.", exc)
        return CalibrationResult(
            sufficient_data=False,
            reason=f"fit_error: {type(exc).__name__}",
            n_training_samples=len(valid_pairs),
            source_sessions=len(targets),
            fit_details={
                "algorithm": "isotonic_regression",
                "error": str(exc),
            },
            calibration_function=DEFAULT_CALIBRATION,
            fit_residuals={},
        )


async def load_rpe_data_from_db(
    session: AsyncSession, user_id: int, lookback_days: int = 90
) -> tuple[list[float], list[float]]:
    """Load (target_rpe, actual_rpe) pairs from UserWorkoutLog and WorkoutSetLog.

    For each UserWorkoutLog row within the lookback window:
    - Compute average target_rpe from associated WorkoutExercise rows
    - Compute average actual_rpe from associated WorkoutSetLog rows
    - Include the pair if both are available

    Returns: (targets, actuals) tuple of parallel lists
    """
    try:
        cutoff_date = datetime.now(UTC) - timedelta(days=lookback_days)

        # Query UserWorkoutLog rows for this user within lookback window
        stmt = (
            select(UserWorkoutLog)
            .where((UserWorkoutLog.user_id == user_id) & (UserWorkoutLog.created_at >= cutoff_date))
            .order_by(UserWorkoutLog.created_at)
        )
        result = await session.execute(stmt)
        logs = list(result.scalars().all())

        if not logs:
            logger.info("No UserWorkoutLog entries found for user %d; no calibration data.", user_id)
            return [], []

        targets = []
        actuals = []

        for log in logs:
            # Get actual RPE from WorkoutSetLog rows for this session
            actual_rpe_stmt = select(func.avg(WorkoutSetLog.actual_rpe)).where(
                (WorkoutSetLog.workout_id == log.workout_id)
                & (WorkoutSetLog.user_id == user_id)
                & (WorkoutSetLog.actual_rpe.isnot(None))
            )
            actual_rpe_result = await session.execute(actual_rpe_stmt)
            avg_actual_rpe = actual_rpe_result.scalar()

            # For target_rpe, we need to average from WorkoutExercise.target_rpe
            # (which are prescribed values for the exercises in that workout)
            target_rpe_stmt = text(
                """
                SELECT AVG(we.target_rpe) FROM workout_exercises we
                WHERE we.workout_id = :workout_id AND we.target_rpe IS NOT NULL
                """
            )
            target_rpe_result = await session.execute(target_rpe_stmt, {"workout_id": log.workout_id})
            avg_target_rpe = target_rpe_result.scalar()

            # Only include if both are available
            if avg_target_rpe is not None and avg_actual_rpe is not None:
                targets.append(float(avg_target_rpe))
                actuals.append(float(avg_actual_rpe))

        return targets, actuals

    except (ProgrammingError, OperationalError) as exc:
        logger.warning("Failed to load RPE data from DB (%s); will use default calibration.", exc)
        await session.rollback()
        return [], []


def write_calibration(result: CalibrationResult, output_path: Path) -> None:
    """Persist calibration result as JSON with metadata."""
    payload = result.to_json_dict()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


async def _load_and_fit(user_id: int, lookback_days: int) -> CalibrationResult:
    """Load data from DB and fit calibration model."""
    async with async_session() as db:
        targets, actuals = await load_rpe_data_from_db(db, user_id, lookback_days)
    return fit_isotonic_regression(targets, actuals)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for calibration job.

    Args:
        argv: Command-line arguments (or None to use sys.argv)

    Returns:
        Exit code (0 on success, non-zero on failure)
    """
    parser = argparse.ArgumentParser(
        description="Train isotonic regression calibration for RPE predictions (Task 4.6)."
    )
    parser.add_argument(
        "--output-path",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Path to write the RPE calibration JSON artifact (default: backend/data/rpe_calibration.json).",
    )
    parser.add_argument(
        "--lookback-days",
        type=int,
        default=90,
        help="Only use sessions from the last N days (default: 90).",
    )
    parser.add_argument(
        "--user-id",
        type=int,
        default=1,
        help="User ID to calibrate for (default: 1). For now, single-user calibration.",
    )

    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO)

    try:
        result = asyncio.run(_load_and_fit(args.user_id, args.lookback_days))
        write_calibration(result, args.output_path)

        if result.sufficient_data:
            print(
                f"Trained isotonic regression calibration from {result.source_sessions} session(s) "
                f"({result.n_training_samples} valid samples) -> {args.output_path}"
            )
        else:
            print(
                f"Insufficient/degenerate data (reason={result.reason}); "
                f"wrote identity calibration to {args.output_path}"
            )
        return 0
    except Exception as exc:
        logger.error("Calibration job failed with error: %s", exc, exc_info=True)
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
