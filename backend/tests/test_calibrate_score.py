"""Tests for isotonic regression RPE calibration (Task 4.6).

Tests cover:
- Sufficient data → valid calibration function
- Insufficient data → default (identity), warning logged
- Missing/malformed input → graceful fallback
- Determinism (same input → identical JSON)
- Monotonicity of function
- CLI invocation
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.exc import OperationalError

from scripts.calibrate_score import (
    DEFAULT_CALIBRATION,
    CalibrationResult,
    fit_isotonic_regression,
    load_rpe_data_from_db,
    main,
    write_calibration,
)


@pytest.fixture
def temp_output_path():
    """Temporary file path for output artifacts."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        path = Path(f.name)
    yield path
    path.unlink(missing_ok=True)


class TestFitIsotonicRegression:
    """Tests for isotonic regression fitting logic."""

    def test_sufficient_data_produces_valid_function(self):
        """With ≥20 valid samples, fit a valid calibration function."""
        # Simulate 25 (target_rpe, actual_rpe) pairs with some noise
        targets = [2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0] * 3  # 24 values
        targets.append(5.5)  # 25 total
        actuals = [2.1, 2.9, 4.2, 4.8, 6.1, 6.9, 8.2, 9.1] * 3
        actuals.append(5.4)

        result = fit_isotonic_regression(targets, actuals)

        assert result.sufficient_data
        assert result.reason is None
        assert len(result.calibration_function) > 0
        assert all(
            isinstance(p, dict) and "predicted_rpe" in p and "calibrated_rpe" in p for p in result.calibration_function
        )

    def test_insufficient_data_returns_default(self):
        """With <20 valid samples, return default (identity) function and log warning."""
        targets = [2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0]  # 8 < 20
        actuals = [2.1, 2.9, 4.2, 4.8, 6.1, 6.9, 8.2, 9.1]

        with patch("scripts.calibrate_score.logger") as mock_logger:
            result = fit_isotonic_regression(targets, actuals)

        assert not result.sufficient_data
        assert result.reason == "insufficient_data"
        mock_logger.warning.assert_called()
        # Default should be identity function
        assert result.calibration_function == DEFAULT_CALIBRATION

    def test_empty_data_returns_default(self):
        """With no samples, return default function."""
        with patch("scripts.calibrate_score.logger"):
            result = fit_isotonic_regression([], [])

        assert not result.sufficient_data
        assert result.reason == "no_data"
        assert result.calibration_function == DEFAULT_CALIBRATION

    def test_nan_values_are_filtered(self):
        """NaN values in target or actual are filtered out; remaining valid pairs fit."""
        # 25 pairs total with 2 NaN values → 22+ valid pairs after filtering
        targets = (
            [2.0, float("nan"), 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0]
            + [2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
            + [2.5, 3.5, 4.5, 5.5, 6.5, 7.5, float("nan")]
        )
        actuals = (
            [2.1, 2.9, 3.1, 4.2, 4.8, 6.1, 6.9, 8.2, 9.1]
            + [2.2, 3.2, 4.1, 5.2, 6.2, 7.1, 8.1, 9.2, 10.1]
            + [2.6, 3.6, 4.6, 5.6, 6.6, 7.6, 7.5]
        )

        with patch("scripts.calibrate_score.logger"):
            result = fit_isotonic_regression(targets, actuals)

        # With 22+ valid pairs (>20), should fit successfully
        assert result.sufficient_data
        assert result.n_training_samples >= 22
        assert len(result.calibration_function) > 0

    def test_negative_rpe_values_are_filtered(self):
        """Negative RPE values are filtered out; remaining valid pairs fit."""
        # 25 pairs total with 2 negative values → 22+ valid pairs after filtering
        targets = (
            [2.0, -1.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0]
            + [2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
            + [2.5, 3.5, 4.5, 5.5, 6.5, 7.5, -0.5]
        )
        actuals = (
            [2.1, 2.9, 3.1, 4.2, 4.8, 6.1, 6.9, 8.2, 9.1]
            + [2.2, 3.2, 4.1, 5.2, 6.2, 7.1, 8.1, 9.2, 10.1]
            + [2.6, 3.6, 4.6, 5.6, 6.6, 7.6, 7.5]
        )

        with patch("scripts.calibrate_score.logger"):
            result = fit_isotonic_regression(targets, actuals)

        # After filtering negatives, should have 22+ valid pairs (>20)
        assert result.sufficient_data
        assert result.n_training_samples >= 22
        assert len(result.calibration_function) > 0

    def test_out_of_range_rpe_filtered(self):
        """RPE values >10 are filtered out; remaining valid pairs fit."""
        # 25 pairs total with 2 out-of-range values → 22+ valid pairs after filtering
        targets = (
            [2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 12.0]
            + [2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
            + [2.5, 3.5, 4.5, 5.5, 6.5, 7.5, 11.0]
        )
        actuals = (
            [2.1, 2.9, 4.2, 4.8, 6.1, 6.9, 8.2, 9.1, 9.0]
            + [2.2, 3.2, 4.1, 5.2, 6.2, 7.1, 8.1, 9.2, 10.1]
            + [2.6, 3.6, 4.6, 5.6, 6.6, 7.6, 7.5]
        )

        with patch("scripts.calibrate_score.logger"):
            result = fit_isotonic_regression(targets, actuals)

        # After filtering out-of-range, should have 22+ valid pairs (>20)
        assert result.sufficient_data
        assert result.n_training_samples >= 22
        assert len(result.calibration_function) > 0

    def test_calibration_function_is_monotonic(self):
        """Output calibration function must be monotonically increasing."""
        targets = [2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0] * 3
        actuals = [2.1, 2.9, 4.2, 4.8, 6.1, 6.9, 8.2, 9.1] * 3

        result = fit_isotonic_regression(targets, actuals)

        if result.sufficient_data and len(result.calibration_function) > 1:
            for i in range(len(result.calibration_function) - 1):
                assert (
                    result.calibration_function[i]["calibrated_rpe"]
                    <= result.calibration_function[i + 1]["calibrated_rpe"]
                ), "Calibration function must be monotonically increasing"

    def test_determinism_same_input_same_output(self):
        """Same input data must produce identical calibration function."""
        targets = [2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0] * 3
        actuals = [2.1, 2.9, 4.2, 4.8, 6.1, 6.9, 8.2, 9.1] * 3

        result1 = fit_isotonic_regression(targets.copy(), actuals.copy())
        result2 = fit_isotonic_regression(targets.copy(), actuals.copy())

        # Compare calibration function and fit details (ignoring timestamp metadata)
        assert json.dumps(result1.calibration_function, sort_keys=True) == json.dumps(
            result2.calibration_function, sort_keys=True
        ), "Determinism: calibration function should be identical"
        assert json.dumps(result1.fit_details, sort_keys=True) == json.dumps(
            result2.fit_details, sort_keys=True
        ), "Determinism: fit details should be identical"

    def test_determinism_shuffled_input_same_output(self):
        """Input order should not affect output (sorted internally)."""
        targets = [2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0] * 3
        actuals = [2.1, 2.9, 4.2, 4.8, 6.1, 6.9, 8.2, 9.1] * 3

        # Shuffle in a deterministic way
        import random

        rng = random.Random(42)
        shuffled_idx = list(range(len(targets)))
        rng.shuffle(shuffled_idx)

        targets_shuffled = [targets[i] for i in shuffled_idx]
        actuals_shuffled = [actuals[i] for i in shuffled_idx]

        result1 = fit_isotonic_regression(targets, actuals)
        result2 = fit_isotonic_regression(targets_shuffled, actuals_shuffled)

        # Compare calibration function and fit details (ignoring timestamp metadata)
        assert json.dumps(result1.calibration_function, sort_keys=True) == json.dumps(
            result2.calibration_function, sort_keys=True
        ), "Shuffled input should produce identical calibration function"
        assert json.dumps(result1.fit_details, sort_keys=True) == json.dumps(
            result2.fit_details, sort_keys=True
        ), "Shuffled input should produce identical fit details"


class TestLoadRPEDataFromDB:
    """Tests for loading RPE data from database (unit tests with mocks)."""

    @pytest.mark.asyncio
    async def test_load_returns_empty_on_no_logs(self):
        """With no UserWorkoutLog entries, return empty lists."""
        from unittest.mock import MagicMock

        mock_session = AsyncMock()
        # Mock the chained calls: execute -> scalars -> all
        # Note: scalars() is sync, not async
        mock_scalars_obj = MagicMock()
        mock_scalars_obj.all.return_value = []

        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars_obj

        mock_session.execute = AsyncMock(return_value=mock_result)

        targets, actuals = await load_rpe_data_from_db(mock_session, user_id=1, lookback_days=90)

        assert targets == []
        assert actuals == []

    @pytest.mark.asyncio
    async def test_load_handles_query_error(self):
        """With database query error, log warning and return empty lists."""
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=OperationalError("Connection failed", "", ""))

        with patch("scripts.calibrate_score.logger"):
            targets, actuals = await load_rpe_data_from_db(mock_session, user_id=1, lookback_days=90)

        assert targets == []
        assert actuals == []


class TestCalibrationResult:
    """Tests for CalibrationResult data class."""

    def test_to_json_dict_has_required_fields(self):
        """Output JSON must have all required fields."""
        result = CalibrationResult(
            sufficient_data=True,
            reason=None,
            n_training_samples=25,
            source_sessions=30,
            fit_details={
                "algorithm": "isotonic_regression",
                "min_target_rpe": 2.0,
                "max_target_rpe": 9.0,
                "mean_actual_rpe": 6.8,
                "std_actual_rpe": 1.2,
            },
            calibration_function=[
                {"predicted_rpe": 0.0, "calibrated_rpe": 0.0},
                {"predicted_rpe": 5.0, "calibrated_rpe": 5.1},
                {"predicted_rpe": 10.0, "calibrated_rpe": 10.0},
            ],
            fit_residuals={"mean_absolute_error": 0.45, "rmse": 0.62},
        )

        json_dict = result.to_json_dict()

        assert "version" in json_dict
        assert "generated_at" in json_dict
        assert "source_sessions" in json_dict
        assert "fit_details" in json_dict
        assert "calibration_function" in json_dict
        assert "fit_residuals" in json_dict


class TestWriteCalibration:
    """Tests for writing calibration artifact."""

    def test_write_creates_file(self, temp_output_path: Path):
        """Write should create JSON file with all fields."""
        result = CalibrationResult(
            sufficient_data=True,
            reason=None,
            n_training_samples=25,
            source_sessions=30,
            fit_details={
                "algorithm": "isotonic_regression",
                "min_target_rpe": 2.0,
                "max_target_rpe": 9.0,
                "mean_actual_rpe": 6.8,
                "std_actual_rpe": 1.2,
            },
            calibration_function=[
                {"predicted_rpe": 0.0, "calibrated_rpe": 0.0},
                {"predicted_rpe": 5.0, "calibrated_rpe": 5.1},
                {"predicted_rpe": 10.0, "calibrated_rpe": 10.0},
            ],
            fit_residuals={"mean_absolute_error": 0.45, "rmse": 0.62},
        )

        write_calibration(result, temp_output_path)

        assert temp_output_path.exists()
        content = json.loads(temp_output_path.read_text())
        assert content["sufficient_data"] is True
        assert len(content["calibration_function"]) == 3

    def test_write_uses_sorted_keys(self, temp_output_path: Path):
        """Written JSON should use sorted keys for determinism."""
        result = CalibrationResult(
            sufficient_data=True,
            reason=None,
            n_training_samples=25,
            source_sessions=30,
            fit_details={
                "algorithm": "isotonic_regression",
                "min_target_rpe": 2.0,
                "max_target_rpe": 9.0,
                "mean_actual_rpe": 6.8,
                "std_actual_rpe": 1.2,
            },
            calibration_function=[
                {"predicted_rpe": 0.0, "calibrated_rpe": 0.0},
            ],
            fit_residuals={"mean_absolute_error": 0.45, "rmse": 0.62},
        )

        write_calibration(result, temp_output_path)

        content_text = temp_output_path.read_text()
        # Check that keys are in sorted order by looking at substrings
        assert content_text.find('"calibration_function"') < content_text.find('"fit_details"')


class TestCLI:
    """Tests for CLI invocation."""

    def test_main_returns_zero_on_success(self, temp_output_path: Path):
        """Main should return exit code 0 on success (with mocked DB)."""
        with patch("scripts.calibrate_score.load_rpe_data_from_db", new_callable=AsyncMock) as mock_load:
            mock_load.return_value = ([], [])  # Empty data → uses default
            with patch("scripts.calibrate_score.async_session"):
                exit_code = main(
                    [
                        "--output-path",
                        str(temp_output_path),
                        "--lookback-days",
                        "90",
                    ]
                )

        assert exit_code == 0

    def test_main_creates_output_file(self, temp_output_path: Path):
        """Main should create output file (with mocked DB)."""
        temp_output_path.unlink(missing_ok=True)  # Start fresh

        with patch("scripts.calibrate_score.load_rpe_data_from_db", new_callable=AsyncMock) as mock_load:
            mock_load.return_value = ([], [])  # Empty data → uses default
            with patch("scripts.calibrate_score.async_session"):
                main(
                    [
                        "--output-path",
                        str(temp_output_path),
                        "--lookback-days",
                        "90",
                    ]
                )

        assert temp_output_path.exists()

    def test_main_with_custom_output_path(self, temp_output_path: Path):
        """Main should work with explicit output path (with mocked DB)."""
        with patch("scripts.calibrate_score.load_rpe_data_from_db", new_callable=AsyncMock) as mock_load:
            mock_load.return_value = ([], [])
            with patch("scripts.calibrate_score.async_session"):
                exit_code = main(["--output-path", str(temp_output_path)])

        # Should succeed and create file
        assert exit_code == 0
        assert temp_output_path.exists()
