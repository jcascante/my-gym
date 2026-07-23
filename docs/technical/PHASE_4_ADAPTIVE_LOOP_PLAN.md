# Phase 4 Implementation Plan — Adaptive Loop

**Branch**: `engine-refactor-phase4`
**Status**: Planning
**Baseline**: engine-refactor (Phase 3 merged)
**Exit Criteria**: All 6 tasks complete; pytest/mypy/ruff clean; determinism tests pass; e2e readiness workflow validated

---

## Overview

Phase 4 ("Adaptive loop") closes the feedback loop: users log actual RPE/reps, the engine reacts with load adjustments, and learned swap patterns inform ranking weights. Five of six tasks are backend-heavy; task 4.1 (sensor layer) is frontend-first data collection.

**Dependency order** (all independent except as noted):
1. **4.1 Sensor layer** ← prerequisite: collects the data Phase 4 needs
2. **4.2 Autoregulation controller** ← depends on 4.1 (reads `WorkoutSetLog.actual_rpe`)
3. **4.3 Reactive deloads** ← depends on 4.2 (uses autoregulation signals)
4. **4.4 Learning-to-rank pipeline** ← independent (offline training on phase 1 telemetry)
5. **4.5 Version pinning** ← independent (schema + migration)
6. **4.6 Calibration job** ← depends on 4.5 (needs pinned versions for reproducibility)

**Parallel tracks**: 4.1 + 4.4 + 4.5 can start independently; 4.2 waits on 4.1; 4.3 waits on 4.2; 4.6 waits on 4.5.

---

## Task 4.1 — Sensor Layer

**Scope**: Frontend + backend logging endpoints for per-set RPE, session readiness.

**Code locations**:
- Frontend: `frontend/src/components/SetLogger.tsx`, `frontend/src/pages/WorkoutTrackingPage.tsx`
- Backend: `backend/app/schemas/logging.py`, `backend/app/api/v1/endpoints/logging.py`

**Subtasks**:
1. **4.1a** — `SetLoggerSchema`: Pydantic `WorkoutSetLogCreate` (user_id, workout_id, workout_exercise_id, set_number, actual_weight, actual_reps, actual_rpe) + POST endpoint.
2. **4.1b** — Frontend `SetLogger` component: per-set actual-RPE input respecting user's `effort_method` (RPE/RIR/Borg).
3. **4.1c** — `WorkoutReadinessSchema`: Pydantic `UserWorkoutLogCreate` + PATCH endpoint (post-session readiness 1-5).
4. **4.1d** — Frontend `WorkoutTrackingPage`: one-tap readiness prompt (1-5) at session start + post-completion.

**Testing**:
- Unit: schema validation (valid RPE 1–10, reps 1–100, weight ≥ 0).
- Integration: POST → verify `WorkoutSetLog` row created; PATCH → verify `UserWorkoutLog.readiness` updated.
- Frontend: `SetLogger.test.tsx` (input validation, value clamping).

**Acceptance**: Backend endpoints respond 201/200 on valid input; schema rejects invalid RPE/reps; frontend inputs clamp to valid ranges; existing `WorkoutTrackingPage` flow unchanged.

---

## Task 4.2 — Autoregulation Controller

**Scope**: Reactive load adjustment based on logged RPE vs target.

**Code locations**:
- `backend/app/services/progression/autoregulation.py` (new module)
- `backend/app/services/progression/__init__.py` (export)
- `backend/app/services/program/preview.py` (integrate into week derivation)

**Algorithm**:
- Input: draft week + prior N sessions' logs (actual RPE, target RPE, exercise_id).
- Compute: `signal = EWMA(actual_rpe − target_rpe, span=3)` per exercise pattern (e.g., squat, bench).
- Adjust: `factor = clamp(1.0 − k·signal, 0.925, 1.05)` where k ≈ 0.075 (5% max decrease, 2.5% max increase, from plan).
- Output: adjusted load % + reason string (e.g., "recent RPE 8.5 vs 7 target → 3% load reduction").

**Subtasks**:
1. **4.2a** — `autoregulation.py`: pure function `compute_adjustment(session_logs, exercise_id) -> (factor, reason)`.
2. **4.2b** — Integration into `preview.py`: wrap `model.resolve()` call with adjustment, apply before `ramp_guard`.
3. **4.2c** — Schema: `PreviewOut` gains optional `autoregulation_adjustment` (factor, reason, applied_loads).

**Testing**:
- Unit: property test determinism (same inputs = same output); EWMA correctness (span=3 decay).
- Trajectory tests: constant RPE above target → steady decrease; noisy RPE → stable signal.
- Integration: draft a week, log RPE > target on primary, derive next week, verify load reduced.

**Acceptance**: `pytest backend/tests/services/progression/test_autoregulation.py` all green; determinism property holds; e2e: logged RPE > target by ±1 triggers ±3% adjustment.

---

## Task 4.3 — Reactive Deloads

**Scope**: Automatic deload trigger when fatigue or recovery signals deteriorate.

**Code locations**:
- `backend/app/services/progression/deload.py` (existing module, extend)
- `backend/app/services/program/preview.py` (integrate trigger check)
- `backend/app/core/constants.py` (deload thresholds)

**Trigger logic** (any of these fires a deload):
- Mean readiness over last 4 sessions < 3 (1-5 scale).
- RPE signal (autoregulation) > +1.0 on ≥2 primary patterns (overtrained).
- Estimated 1RM drop ≥5% (fatigue).
- ≥2 active amber injury flags.

**Subtasks**:
1. **4.3a** — Threshold constants in `engine.yaml` (or hardcoded in `constants.py`).
2. **4.3b** — `should_deload(logs, injuries) -> (bool, reason)` helper in `deload.py`.
3. **4.3c** — Call in `preview.py` before applying deload (reactive override of schedule).
4. **4.3d** — Schema: `PreviewOut` gains optional `reactive_deload_reason` when fired.

**Testing**:
- Unit: trigger logic on synthetic 4-session readiness < 3, RPE signal > +1, 1RM drop.
- Integration: log 4 sessions readiness 2–2.5, derive next week, verify deload fires.

**Acceptance**: Tests all green; reactive deload only fires when threshold met; `deload_every` remains as backstop ceiling.

---

## Task 4.4 — Learning-to-Rank Pipeline

**Scope**: Offline training of exercise-selection weights from phase 1 telemetry swaps.

**Code locations**:
- `backend/scripts/train_rank_weights.py` (new script)
- `backend/tests/test_train_rank_weights.py` (unit tests)
- `backend/app/services/program/config/engine.yaml` (updated weights)

**Algorithm**:
- Input: `EngineEvent` table, filter for swap events (user swapped exercise A → B).
- Feature extraction: A vs B feature vectors (difficulty, muscle fit, availability).
- Bradley–Terry pairwise logistic regression: model P(B chosen | A, B) across all pairs.
- Regularization: L2 penalty toward current hand-weights (prevent wild swings).
- Output: new `SelectionWeights` with provenance (e.g., "trained on 5,432 pairs, 2026-07-22").

**Subtasks**:
1. **4.4a** — `train_rank_weights.py`: Bradley–Terry trainer (pure sklearn/scipy, no TF).
2. **4.4b** — Schema: `SelectionWeights` gains `source: str` field (hand-tuned | trained).
3. **4.4c** — Validation: must improve or match performance on existing harness suite.
4. **4.4d** — Dry-run mode: train without mutating `engine.yaml`, output candidate weights to stdout.

**Testing**:
- Synthetic: create mock swap pairs (A obviously better → higher weight), verify trainer recovers preference.
- Determinism: train twice on same data, verify byte-identical output.
- Gating: only trigger when ≥5,000 pairs (stub for now; real gate happens post-MVP).

**Acceptance**: `pytest backend/tests/test_train_rank_weights.py` all green; dry-run mode works; schema updated.

---

## Task 4.5 — Version Pinning

**Scope**: Template and model versioning so programs remain deterministic across template edits.

**Code locations**:
- Schema changes: `backend/app/models/program.py` (ProgramTemplate, WorkoutProgram)
- Migration: `backend/alembic/versions/` (add version columns, backfill)
- Resolution: `backend/app/services/program/preview.py`, `selection.py` (resolve by pin)

**Subtasks**:
1. **4.5a** — Migration: `ProgramTemplate` gains `version: int` (unique on (template_key, version)).
2. **4.5b** — Migration: `WorkoutProgram` gains `template_version, model_key, model_version, params_snapshot JSON` (all nullable for backfill).
3. **4.5c** — Backfill: set all in-flight programs to current template/model versions.
4. **4.5d** — At-accept logic: `POST /api/v1/programs/{id}/accept` pins versions + snapshots.
5. **4.5e** — Resolution: `derive_week` resolves against pinned versions, not latest.
6. **4.5f** — Progression registry: `ProgressionModel` keyed by (key, version); fallback to latest if version missing (grace period).

**Testing**:
- Migration: up → down → up consistency.
- Integration: create program (v1), edit template (creates v2), derive week on v1 program, verify v1 exercises used.
- Golden file: per (model, version) pair, regression-test determinism across code changes.

**Acceptance**: Migrations both directions clean; pinned programs bit-stable; `pytest tests/test_version_pinning.py` all green.

---

## Task 4.6 — Calibration Job

**Scope**: Learn score → completion probability mapping via isotonic regression.

**Code locations**:
- `backend/scripts/calibrate_score.py` (new script)
- `backend/app/models/telemetry.py` (optional `CalibrationRun` model for audit)

**Algorithm**:
- Input: all `WorkoutProgram` rows with ≥70% of target sessions logged (matured).
- Features: `score` (from match time), `completion_rate` (sessions logged / intended).
- Isotonic regression: fit nonparametric monotonic score → completion curve.
- Output: candidate calibrated-score formula + diagnostics (R², RMSE, deciles).
- Dry-run mode: output to stdout, don't persist.

**Subtasks**:
1. **4.6a** — `calibrate_score.py`: load mature programs, fit isotonic model, dump candidate curve.
2. **4.6b** — Gating: log warning if < 1,000 mature programs (defer real deployment).
3. **4.6c** — Schema: `PreviewOut` gains optional `calibrated_completion_pct` (used post-MVP in UI tier badge).

**Testing**:
- Synthetic: create mock programs with score/completion pairs, verify isotonic fit is monotonic.
- Determinism: fit twice on same data, verify byte-identical curve.

**Acceptance**: Script runs without error on seeded data; gating message appears if < 1,000 programs.

---

## Implementation Order

**Week 1**:
- 4.1 (sensor layer) — frontend + backend logging endpoints.
- 4.4 (learning-to-rank) — training script in parallel.

**Week 2**:
- 4.5 (version pinning) — migration + resolution logic.

**Week 2–3**:
- 4.2 (autoregulation) — controller logic once 4.1 data is flowing.
- 4.3 (reactive deloads) — depends on 4.2.

**Week 3**:
- 4.6 (calibration) — once 4.5 pinning is in place.

---

## Exit Criteria

- ✅ `pytest backend/` (all tests pass, ≥80% coverage on new modules).
- ✅ `mypy app/`, `ruff check .`, `black --check .` all clean.
- ✅ Alembic migrations up/down tested for 4.5.
- ✅ Frontend: `npm run test`, `lint`, `type-check`, `build` all clean.
- ✅ E2E: log RPE > target → autoregulation triggers; readiness < 3 → deload fires; version pin holds across template edit.
- ✅ Determinism: same inputs (logs, program) → same output (adjusted loads, deload decision).

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Autoregulation overshoots, user load crashes | Clamp to ±5% / ±2.5%; log all adjustments; flag sudden drops. |
| Deload fires too often | Tune thresholds on phase 1 telemetry before shipping. |
| Learned weights diverge from hand-tuned | Regularization toward hand weights; always require explicit PR to deploy. |
| Version pin breaks existing program resolves | Grace period: fall back to latest if pinned version missing. |
| Calibration job trains on noisy data | Gating: ≥1,000 mature programs before real deployment (stub now). |

---

## Notes

- Autoregulation signal is deterministic (EWMA on logs) — no ML/LLM.
- Learning-to-rank is offline (no runtime model serving).
- All version pins backward-compatible (nullable fields, graceful fallback).
- Phase 4 enables Phase 5 (authoring at scale); Phase 5 deferred post-MVP.
