# Program Engine Refactor — Phased Technical Plan

> **Status: review draft — no implementation started.** Source proposal: [`Program_Engine_Improvement_Proposal.md`](../../Program_Engine_Improvement_Proposal.md). Companion reading: [`PROGRAM_MATCHING_SUMMARY.html`](./PROGRAM_MATCHING_SUMMARY.html) (current-state engine walkthrough).

## Context

The improvement proposal defines five workstreams to evolve the template-matching/generation engine from a slot-and-scheme system into a physiologically grounded, closed-loop coaching system:

- **A — Matching math**: hard/soft constraint tiers, Gaussian range kernel, beam-search assembly
- **B — Volume Ledger**: per-muscle effective sets tracked against MEV/MAV/MRV bands
- **C — Graded safety**: structured injury taxonomy, regression graphs, traffic-light monitoring
- **D — Adaptive loop**: autoregulation, reactive deloads, learning-to-rank from swap behavior
- **E — Platform/trust**: version pinning, config externalization, library linter, telemetry, explanation API

This plan translates the proposal into concrete, code-grounded phases and tasks against the actual codebase (`backend/app/services/program/`, ~742 lines across 10 modules + `progression/`).

### Ground-truth deltas found during code exploration

These findings adjust the proposal's assumptions:

1. **The feasibility "hard gate" does not exist.** `template_is_feasible` is computed (`programs.py:90-92`, `selection.py:141-147`) but `rank_templates` only logs it (`matching.py:149,173-177`) — infeasible templates still rank. `test_matching.py::test_infeasible_template_still_ranked` codifies the bug. Phase 1 fixes this.
2. **Muscle taxonomy is mostly done.** `Exercise` already has `primary_muscles`/`secondary_muscles` over a 22-value `Muscle` enum (`models/exercise.py:115-136`). Workstream B needs a 22→~15-group mapping table, not a library re-tagging migration.
3. **No `environment_type` on Exercise.** Reachability linting must go through `ENVIRONMENT_TYPE_EQUIPMENT_PRESETS` (`core/constants.py`) × equipment_tags.
4. **Scorers are already injectable** (`TemplateScorer`/`ExerciseScorer` Protocols, `weights=` params) — new formulas slot in behind a config flag without touching `rank_templates`/`select_for_slot` call sites.
5. **`injuries_limitations` is free text** comma-split at `programs.py:47-48`; `effort_method` is per-draft-request only; `fitness_focus` is a single enum on `UserProfile`. Confirms proposal premises.
6. Catalog scale: 148 exercises (`db/seed/exercises.py`), 4 templates (`db/seed/program_templates.py`).

Each phase ships independently; later phases depend on earlier ones as noted. All new logic stays deterministic (pure functions / wrappers; learning trains offline, deploys as config).

---

## Phase 1 — Correct the mathematics (Workstream A + E prerequisites)

### 1.1 Engine config surface (E §7.2 — prerequisite for everything)
- New `backend/app/services/program/engine_config.py`: pydantic model `EngineConfig` with `config_version: str`, `match: MatchConfig` (tier weights, ε floor, α/β exponents, σ_days, σ_duration), `selection: SelectionConfig` (7 ranking weights + provenance field), `assembly: AssemblyConfig` (beam width, λ_v, λ_f placeholders), `flags` (`use_constraint_scorer`, `use_beam_search`).
- Values load from a versioned YAML/JSON at `backend/app/services/program/config/engine.yaml` (reviewed via PR, deployable without code change); defaults mirror today's hardcoded `MatchWeights` (`matching.py:31-39`) and `SelectionWeights` (`selection.py:13-22`).
- Inject via FastAPI dependency; `config_version` is attached to every generated draft (store in `WorkoutProgram.constraints["engine_config_version"]` — no migration needed).

### 1.2 Enforce the feasibility hard gate
- `rank_templates` (`matching.py:174-177`): filter templates where `feasibility[t.id] is False` before scoring. Add safety-feasibility hook point (no-op until Phase 3).
- Update `test_matching.py::test_infeasible_template_still_ranked` → `test_infeasible_template_excluded`. Add fallback behavior: if all templates infeasible, return best-effort with advisory flag (keeps the never-empty contract).

### 1.3 Constraint-tiered scorer (A §3.1)
- New `ConstraintTemplateScorer` in `matching.py` implementing:
  - `soft = Σ wᵢ·fᵢ / Σw` over days, duration, movement_preference, focus_complement, periodization (renormalized weights from config).
  - `fit = max(goal, ε)^α · max(experience, ε)^β · soft`, ε=0.10, α=β=1.0 from config.
- Goal factor generalized to `goal = Σ_{t∈T.goals} g_t` over a user goal vector. `MatchInput.fitness_focus` maps to `{focus: 1.0}` initially (backward compatible); `MatchInput` gains optional `goal_vector: dict[str, float]`.
- Selected via `flags.use_constraint_scorer`; legacy `HeuristicTemplateScorer` retained for rollback and A/B.

### 1.4 Gaussian range kernel (A §3.2)
- Replace `_range_fit` (`matching.py:84-88`) with `d = max(0, lo−v, v−hi); exp(−(d/σ)²)`, σ per dimension from config (σ_days=1.0, σ_duration=15). Used only by the new scorer; legacy keeps old kernel.

### 1.5 Beam-search session assembly (A §3.3)
- New `backend/app/services/program/assembly.py`: `assemble_session(slots, pool, ctx, width)` per proposal pseudocode — beams over ordered slots, `top_k` candidates per beam via existing `_extract_features`/`HeuristicExerciseScorer`, `session_objective = Σ slot_score` (+ ledger terms in Phase 2), deterministic tie-break `(score desc, exercise_id asc)`.
- `build_draft` (`drafting.py`) calls `assemble_session` per session when `flags.use_beam_search`, else current greedy loop. **width=1 must reproduce greedy output exactly** — regression-tested against the existing suite.
- Explicit tie-break also added to `_ranked_pool` sort (`selection.py:102-117`) — currently relies on stable-sort input order.

### 1.6 Fit presentation tiers (A §3.4)
- `TemplateMatchOut` (`schemas/program_api.py`) gains `tier: Literal["best","strong","possible"]` derived from score gaps; `fit_pct` retained in payload/telemetry. Frontend match screen switches label to tier (small change in the match results component).

### 1.7 Telemetry foundation (E §7.4, minimal)
- New model `EngineEvent` (`models/telemetry.py` + Alembic migration): `id, user_id, event_type, payload JSON, config_version, created_at`. Append-only, consistent with the existing immutable-log pattern.
- Log: per-match score breakdowns (both scorers during A/B), per-slot ranking features + chosen exercise, every `FeedbackAction` with full feature context (from `adaptation.py:38-88`). Behind a consent setting; retention note in the model docstring.

### 1.8 Synthetic-user A/B harness (E §7.7)
- `backend/tests/harness/`: profile generator (grid over goals × experience × days × duration × equipment presets × injury strings), runner that executes match→draft for old vs new formula, report (rank agreement, advisory rates, latency p95).
- Property tests: byte-identical determinism (run twice, compare serialized drafts), goal-mismatch never outranks goal-match within soft-score 0.3, width=1 ≡ greedy, p95 < 100ms.

**Exit criteria:** new formula + beam search live behind flags; feasibility enforced; harness comparison report generated; telemetry flowing; all existing tests green (with the one deliberate test update).

---

## Phase 2 — Volume Ledger (Workstream B + library linter pulled forward)

### 2.1 Muscle group taxonomy
- `core/constants.py` (or new `services/program/taxonomy.py`): `MUSCLE_GROUPS` (~15 groups) + mapping from the 22-value `Muscle` enum; `ROLE_FACTOR = {primary: 1.0, secondary: 0.5}` (stabilizer 0.25 deferred until the library tags it).

### 2.2 Library linter in CI (E §7.3)
- `backend/scripts/lint_library.py` + pytest wrapper `tests/test_library_lint.py`: schema validity of seed data (closed vocabularies), reachability (every `environment_type` preset × pattern used by an active template has ≥1 beginner-permissible exercise), coverage (every muscle group is primary for ≥3 exercises across ≥2 environment presets), duplicate/orphan detection. Wire into the existing CI workflow (`.github/workflows/`).

### 2.3 Ledger module
- New `services/program/ledger.py`: `compute_ledger(draft | assignment) -> Ledger` (`effective_sets_week`, `frequency_days`, `hard_set_share` per group); pure function over `WorkoutExercise` rows + exercise lookup; incremental `apply/remove` for beam search and swap recomputation.

### 2.4 Volume bands config
- Bands table (MEV / target / MRV guard by experience, per proposal §4.2) added to `engine.yaml` with a citation string per row; modifiers (emphasis +2–4, amber-injury −30% guard) as config.

### 2.5 Ledger in assembly + post-draft validation
- `session_objective` gains `−λ_v·Σ band_distance + λ_f·freq_bonus` (Phase 1 assembly hook).
- Post-draft validator in `drafting.py`: any group < MEV or > MRV triggers targeted re-selection via existing `_reselect` machinery (`adaptation.py:26-35`); unresolvable violations become structured advisories.
- Advisory schema: `Advisory {code, severity, message, subject}` in `schemas/program_api.py`; carried on `ProgramPreviewOut` and match output (frequency advisories at match time).

### 2.6 Complete prescriptions
- Pure derivations in `preview.py`: rest intervals by scheme intent, default tempo, warm-up ramp for first primary slot (≈40%×5 / 60%×3 / 80%×1 of derived working load). Extend `SlotPreviewOut` with `rest_seconds`, `tempo`, `warmup_sets`.

### 2.7 Goal vector + interference rules
- `UserProfile` gains `goal_weights JSON` (nullable; migration; `fitness_focus` retained and used to default the vector). Onboarding UI: optional split-slider (frontend task).
- Interference scheduler in `assembly.py`/`drafting.py`: conditioning-slot placement rules (strength before conditioning same-day + separation advisory; weight-loss vectors bias full-body/frequency templates via the goal factor).

**Exit criteria:** 100% of harness drafts band-valid or advised; linter green in CI and blocks seeded known-bad mutations; previews include rest/tempo/warm-up; citations shipping in config.

---

## Phase 3 — Graded safety (Workstream C + explanation API)

### 3.1 Structured injury records
- New model `InjuryRecord` (region/condition/phase/provocations/severity/reported_at/source per proposal §5.1) + migration; `injuries_limitations` text retained as provenance. CRUD endpoints under `/api/v1/users/me/injuries`.
- Provocation tag vocabulary added to constants; exercises gain `provocation_tags JSON` (seed migration, LLM-assisted first pass then human-verified, linter-enforced).

### 3.2 LLM intake with confirmation
- Endpoint: free text → proposed `InjuryRecord[]` (Claude API, structured output) → returned as *draft* records; a separate confirm endpoint persists. Unconfirmed extractions never touch generation. Frontend confirmation UI in onboarding/profile.

### 3.3 Regression/progression graphs
- Config-authored per-pattern graphs (nodes = exercise slugs, edges = relieving axes) in `services/program/config/regression_graphs.yaml`; linter validates node existence and edge axes.
- Selection change in `selection.py`: contraindication/provocation hit → walk graph to nearest permissible in-environment variant → cross-pattern substitute → exclusion **with advisory** (never silent). Safety-feasibility plugs into the Phase 1 hard-gate hook.
- Load cap + slower ramp on substituted slots for `rehabilitating` records.

### 3.4 Traffic-light check-in
- Post-session check-in model + endpoint (region → green/amber/red + note); state machine per proposal §5.3 (amber: −10–20% load next session, −1.0 selection bias, −30% ledger guard, 2× amber → regression step; red: pattern removed for mesocycle, draft acute InjuryRecord for confirmation, consult message). Frontend: 2-tap flow on session completion.

### 3.5 Ramp-rate guards
- `progression/ramp_guard.py` wrapper (same shape as `deload.py`): weekly volume/load caps by population (beginner +20%, post-amber +10%/+2.5%, returning-after-2-weeks restart at 70%). Applied in `derive_week` (`preview.py:51`) around `apply_deload(model.resolve(...))`.

### 3.6 Explanation API (E §7.6)
- Endpoints: `GET .../programs/{id}/explain/template` and `.../explain/slot/{we_id}` returning top contributing factors + ledger contribution + any safety substitution rationale — assembled from telemetry/stored breakdowns. Draft-review UI renders them per slot.

**Exit criteria:** zero silent safety exclusions in harness; every pattern graph has ≥2 regressions + ≥1 cross-pattern substitute (linter-checked); red-flag flow ≤2 taps; intake never mutates programs without confirmation.

---

## Phase 4 — Adaptive loop (Workstream D + version pinning)

### 4.1 Sensor layer
- Extend workout logging schema: per-set actual RPE + reps (`UserWorkoutLog`, append-only per existing pattern); one-tap session readiness (1–5) at session start. Frontend logging UI additions.

### 4.2 Autoregulation controller
- `progression/autoregulation.py`: `signal = EWMA(RPE_actual − RPE_target, span=3)`, `adjust = clamp(−k·signal, −7.5%, +5%)`, wrapped around `model.resolve` before `ramp_guard`. Pure function of logged history — determinism = same inputs incl. logs → same output. Epley e1RM for %1RM users.

### 4.3 Reactive deloads
- Extend `deload.py`: fire when ≥2 of {mean readiness₄ < 3, RPE signal > +1 on ≥2 primaries, e1RM drop ≥5%, active amber}; `deload_every` becomes backstop ceiling. Thresholds in config.

### 4.4 Learning-to-rank pipeline (offline)
- Swap events already carry full feature vectors (Phase 1 telemetry). `backend/scripts/train_rank_weights.py`: Bradley–Terry pairwise logistic, regularized toward current hand weights; output = candidate `SelectionConfig` weights with provenance. Deploy = config PR gated by the harness (no runtime ML). Trigger at ≥5,000 pairs.

### 4.5 Version pinning (E §7.1)
- Migration: `ProgramTemplate` gains `version` (unique on `(template_key, version)`); edits create new rows; matching uses latest. `WorkoutProgram` pins `template_version`, `model_key`, `model_version`, `params_snapshot` at accept time; `derive_week` resolves against pins. Progression registry keyed by `(key, version)`; golden-file test per (model, version).
- Backfill migration pins all in-flight programs to current versions.

### 4.6 Calibration job
- Scheduled script: at ≥1,000 matured programs, isotonic regression of score → 8-week completion (≥70% sessions logged); calibrated score replaces tier presentation (Phase 5 UI).

**Exit criteria:** controller unit-tested on synthetic trajectories (overshoot/undershoot/noisy); deloads fire in fatigue scenarios only; learned-weight deploy is pure config; pinned programs bit-stable across template/model edits.

---

## Phase 5 — Authoring at scale (gated on Phases 1–4 stability)

Sketch only; detailed planning deferred: form-based template builder; LLM-assisted authoring behind the §7.5 gate (schema validation → linter reachability → ~200-profile simulation gate → human review); per-segment learned weights; ILP assembler evaluation (Appendix D) if beam search plateaus in harness metrics; calibrated fit % restored to UI.

---

## Cross-cutting conventions

- TDD throughout (tests first, >80% coverage); strict mypy; all new I/O async; Alembic up/down tested for every migration (Phases 1.7, 2.7, 3.1, 3.4, 4.1, 4.5).
- Every new algorithm is a pure function or a wrapper on an existing extension point (scorer Protocols, progression wrappers, overlay `_reselect`); legacy paths retained behind flags for rollback.
- Latency: p95 generation < 100ms is an acceptance criterion in every phase (harness-asserted).

## Verification per phase

```bash
docker-compose exec backend pytest                      # full suite + harness properties
docker-compose exec backend pytest tests/harness -m ab  # A/B comparison report
docker-compose exec backend mypy app/ && docker-compose exec backend ruff check .
docker-compose exec backend alembic upgrade head && alembic downgrade -1 && alembic upgrade head
```

End-to-end: `docker-compose up`, run match→draft→feedback→accept via Swagger (`localhost:8000/docs`) with a seeded user; confirm determinism by drafting twice with identical inputs; confirm preview shows rest/tempo/warm-up (Phase 2+), advisories render (Phase 2+), and check-in flow works from the frontend (Phase 3+).
