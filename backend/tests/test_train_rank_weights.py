import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from scripts.train_rank_weights import (
    MIN_SWAPS_TO_TRAIN,
    RankWeights,
    SwapRecord,
    fit_bradley_terry,
    load_swap_history_from_db,
    main,
    write_weights,
)

_BASE_DATE = datetime(2026, 1, 1)


def _record(
    *,
    user_id: int = 1,
    original: int = 1,
    swap: int = 2,
    completed: bool = True,
    day_offset: int = 0,
    rpe_feedback: float | None = None,
) -> SwapRecord:
    return SwapRecord(
        user_id=user_id,
        original_exercise_id=original,
        swap_exercise_id=swap,
        session_date=_BASE_DATE + timedelta(days=day_offset),
        completed=completed,
        rpe_feedback=rpe_feedback,
    )


class TestFitBradleyTerryDegradedCases:
    def test_empty_data_returns_uniform_result(self) -> None:
        result = fit_bradley_terry([])

        assert result.sufficient_data is False
        assert result.reason == "no_data"
        assert result.weights == {}
        assert result.pair_scores == {}
        assert result.n_swaps == 0
        assert result.n_exercises == 0

    def test_below_minimum_swaps_returns_uniform_weights(self) -> None:
        records = [_record(original=1, swap=2, day_offset=i) for i in range(MIN_SWAPS_TO_TRAIN - 1)]

        result = fit_bradley_terry(records)

        assert result.sufficient_data is False
        assert result.reason == "insufficient_data"
        assert result.n_swaps == MIN_SWAPS_TO_TRAIN - 1
        assert result.weights == {1: 0.0, 2: 0.0}
        assert result.pair_scores == {}

    def test_all_self_swaps_returns_uniform_weights(self) -> None:
        records = [_record(original=1, swap=1, day_offset=i) for i in range(MIN_SWAPS_TO_TRAIN + 5)]

        result = fit_bradley_terry(records)

        assert result.sufficient_data is False
        assert result.reason == "degenerate_pairs"
        assert result.weights == {1: 0.0}
        assert result.pair_scores == {}

    def test_all_identical_outcomes_returns_uniform_weights(self) -> None:
        records = [_record(original=1, swap=2, completed=True, day_offset=i) for i in range(MIN_SWAPS_TO_TRAIN + 5)]

        result = fit_bradley_terry(records)

        assert result.sufficient_data is False
        assert result.reason == "single_class"
        assert result.weights == {1: 0.0, 2: 0.0}


class TestFitBradleyTerryFullTraining:
    def _training_records(self) -> list[SwapRecord]:
        # Exercise 2 reliably "wins" swaps against 1; exercise 3 reliably "loses"
        # swaps against 1 -- enough signal for a non-trivial, well-separated fit.
        records = []
        for i in range(8):
            records.append(_record(user_id=i, original=1, swap=2, completed=True, day_offset=i))
        for i in range(8):
            records.append(_record(user_id=i, original=1, swap=3, completed=False, day_offset=i + 8))
        return records

    def test_produces_weights_for_every_exercise(self) -> None:
        result = fit_bradley_terry(self._training_records())

        assert result.sufficient_data is True
        assert result.reason is None
        assert set(result.weights.keys()) == {1, 2, 3}
        assert result.n_swaps == 16
        assert result.n_exercises == 3

    def test_learns_expected_ranking_direction(self) -> None:
        result = fit_bradley_terry(self._training_records())

        # 2 was swapped-in successfully every time -> should rank above the
        # original (1); 3 failed every time it was swapped in -> should rank below.
        assert result.weights[2] > result.weights[1]
        assert result.weights[3] < result.weights[1]

    def test_pair_scores_reflect_learned_direction(self) -> None:
        result = fit_bradley_terry(self._training_records())

        assert result.pair_scores["1->2"] > 0.5
        assert result.pair_scores["1->3"] < 0.5
        assert set(result.pair_scores.keys()) == {"1->2", "1->3"}

    def test_pair_scores_only_cover_observed_distinct_pairs(self) -> None:
        records = self._training_records() + [_record(user_id=99, original=2, swap=2, completed=True, day_offset=99)]

        result = fit_bradley_terry(records)

        assert "2->2" not in result.pair_scores

    def test_output_is_json_serializable(self) -> None:
        result = fit_bradley_terry(self._training_records())

        serialized = json.dumps(result.to_json_dict())
        payload = json.loads(serialized)

        assert payload["sufficient_data"] is True
        assert payload["weights"]["2"] > payload["weights"]["1"]
        assert payload["n_swaps"] == 16


class TestDeterminism:
    def test_same_input_twice_produces_identical_weights(self) -> None:
        records = []
        for i in range(8):
            records.append(_record(user_id=i, original=1, swap=2, completed=True, day_offset=i))
        for i in range(8):
            records.append(_record(user_id=i, original=1, swap=3, completed=False, day_offset=i + 8))

        first = fit_bradley_terry(records)
        second = fit_bradley_terry(records)

        assert first.weights == second.weights
        assert first.pair_scores == second.pair_scores

    def test_input_order_does_not_affect_fitted_weights(self) -> None:
        records = []
        for i in range(8):
            records.append(_record(user_id=i, original=1, swap=2, completed=True, day_offset=i))
        for i in range(8):
            records.append(_record(user_id=i, original=1, swap=3, completed=False, day_offset=i + 8))

        forward = fit_bradley_terry(records)
        shuffled = fit_bradley_terry(list(reversed(records)))

        assert forward.weights == shuffled.weights
        assert forward.pair_scores == shuffled.pair_scores

    def test_to_json_dict_is_byte_identical_across_runs(self) -> None:
        records = []
        for i in range(8):
            records.append(_record(user_id=i, original=1, swap=2, completed=True, day_offset=i))
        for i in range(8):
            records.append(_record(user_id=i, original=1, swap=3, completed=False, day_offset=i + 8))

        first = json.dumps(fit_bradley_terry(records).to_json_dict(), sort_keys=True)
        second = json.dumps(fit_bradley_terry(records).to_json_dict(), sort_keys=True)

        assert first == second


class TestWriteWeights:
    def test_writes_json_file_with_expected_shape(self, tmp_path: Path) -> None:
        result = RankWeights(
            weights={1: 0.1, 2: -0.1},
            pair_scores={"1->2": 0.475},
            n_swaps=12,
            n_exercises=2,
            sufficient_data=True,
            reason=None,
        )
        output_path = tmp_path / "nested" / "weights.json"

        write_weights(result, output_path)

        assert output_path.exists()
        payload = json.loads(output_path.read_text())
        assert payload["weights"] == {"1": 0.1, "2": -0.1}
        assert payload["pair_scores"] == {"1->2": 0.475}
        assert payload["sufficient_data"] is True
        assert payload["n_swaps"] == 12

    def test_creates_missing_parent_directories(self, tmp_path: Path) -> None:
        result = fit_bradley_terry([])
        output_path = tmp_path / "a" / "b" / "c" / "weights.json"

        write_weights(result, output_path)

        assert output_path.is_file()


class TestLoadSwapHistoryFromDb:
    @pytest.mark.asyncio
    async def test_returns_empty_list_when_table_missing(self, db_session: AsyncSession) -> None:
        # The in-memory test DB never creates an `exercise_swap_logs` table (no
        # ORM model exists yet -- see the script's module docstring), so this
        # exercises the graceful-degradation path a real deployment would hit
        # before that table is introduced.
        records = await load_swap_history_from_db(db_session)

        assert records == []

    @pytest.mark.asyncio
    async def test_parses_rows_once_the_assumed_table_exists(self, db_session: AsyncSession) -> None:
        from sqlalchemy import text

        await db_session.execute(
            text(
                "CREATE TABLE exercise_swap_logs ("
                "user_id INTEGER, original_exercise_id INTEGER, swap_exercise_id INTEGER, "
                "session_date TIMESTAMP, completed BOOLEAN, rpe_feedback FLOAT)"
            )
        )
        await db_session.execute(
            text("INSERT INTO exercise_swap_logs VALUES " "(1, 10, 20, :session_date, 1, 7.5)"),
            {"session_date": _BASE_DATE},
        )
        await db_session.commit()

        records = await load_swap_history_from_db(db_session)

        assert records == [
            SwapRecord(
                user_id=1,
                original_exercise_id=10,
                swap_exercise_id=20,
                session_date=_BASE_DATE,
                completed=True,
                rpe_feedback=7.5,
            )
        ]


class TestMainCli:
    def test_main_writes_uniform_weights_when_db_has_no_swap_table(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        import scripts.train_rank_weights as module

        # `load_swap_history_from_db` is monkeypatched directly (rather than
        # exercising a real session) since its DB-facing behavior is already
        # covered by TestLoadSwapHistoryFromDb; this only needs to prove main()
        # wires the loader's result through fit + write + the CLI messages.
        monkeypatch.setattr(module, "load_swap_history_from_db", lambda _session: _empty_records())
        monkeypatch.setattr(module, "async_session", lambda: _FakeSessionCtx())

        output_path = tmp_path / "weights.json"
        exit_code = main(["--output", str(output_path)])

        assert exit_code == 0
        assert output_path.exists()
        payload = json.loads(output_path.read_text())
        assert payload["sufficient_data"] is False
        assert payload["reason"] == "no_data"

        captured = capsys.readouterr()
        assert "Insufficient/degenerate data" in captured.out

    def test_main_reports_success_when_data_is_sufficient(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        import scripts.train_rank_weights as module

        records = []
        for i in range(8):
            records.append(_record(user_id=i, original=1, swap=2, completed=True, day_offset=i))
        for i in range(8):
            records.append(_record(user_id=i, original=1, swap=3, completed=False, day_offset=i + 8))

        monkeypatch.setattr(module, "load_swap_history_from_db", lambda _session: _records(records))
        monkeypatch.setattr(module, "async_session", lambda: _FakeSessionCtx())

        output_path = tmp_path / "weights.json"
        exit_code = main(["--output", str(output_path)])

        assert exit_code == 0
        payload = json.loads(output_path.read_text())
        assert payload["sufficient_data"] is True

        captured = capsys.readouterr()
        assert "Trained Bradley-Terry weights" in captured.out


class _FakeSessionCtx:
    async def __aenter__(self) -> "_FakeSessionCtx":
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        return None


async def _empty_records() -> list[SwapRecord]:
    return []


async def _records(records: list[SwapRecord]) -> list[SwapRecord]:
    return records
