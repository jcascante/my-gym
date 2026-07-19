# Formal Proposal: Evolving the Template Matching & Program Generation Engine into a Scientifically Grounded Coaching System

**Document type:** Technical & Product Proposal
**Prepared by:** Expert Review Board (Movement Science · Physical Therapy · Applied Mathematics · Software & Infrastructure Architecture)
**Date:** July 2026
**Status:** For review and approval
**Scope of reference:** `PROGRAM_MATCHING_SUMMARY` (matching algorithm, template authoring model, generation pipeline) and the underlying services in `backend/app/services/program/`

---

## 1. Executive Summary

The current engine is a well-architected v1: the three-layer template model (split → slot rules → progression reference), the equipment feasibility gate, base-week-plus-overlay storage, and deterministic sub-100ms generation are sound decisions that this proposal deliberately preserves. Its limitations are not structural but conceptual: the system reasons about *slots and schemes* while the human body responds to *per-muscle volume, frequency, intensity, and recovery*; the scoring mathematics is compensatory where it should be constraining; injury handling is binary where it should be graded; and the pipeline is open-loop where an effective coaching system must be closed-loop.

This proposal defines five coordinated workstreams that upgrade the engine along scientific, mathematical, safety, adaptive, and platform dimensions, sequenced into a five-phase roadmap. Each workstream is specified to implementation depth — data structures, formulas, pseudocode, and acceptance criteria are included in the appendices — so that engineering can begin Phase 1 immediately upon approval.

The workstreams are:

**A. Mathematical redesign of matching and selection.** Replace the fully compensatory weighted sum with a hard/soft constraint architecture, symmetric smooth range kernels, and beam-search slot assignment. No new data collection is required; this is a correctness and quality upgrade to existing logic.

**B. Physiological accounting layer ("the Volume Ledger").** Introduce per-muscle weekly effective-set and frequency accounting, validated against experience-adjusted, evidence-based volume landmarks (MEV/MAV/MRV bands). The ledger becomes a post-draft validator, a re-selection trigger, and the scientific citation backbone of the product.

**C. Graded safety and injury model.** Replace free-text injuries and binary contraindication exclusion with a structured injury taxonomy, per-pattern regression/progression graphs, substitution-before-exclusion policy, traffic-light session monitoring, and ramp-rate guards.

**D. Closed adaptive loop.** Make logged RPE and readiness first-class inputs driving autoregulated load adjustment and reactive (rather than calendar) deloads; log every swap as a labeled preference pair to enable learning-to-rank; calibrate the fit score against adherence outcomes.

**E. Platform, authoring, and trust infrastructure.** Version-pin templates and progression models, externalize all tunable parameters to configuration, lint the exercise library in CI, build the telemetry pipeline, gate future LLM-assisted authoring behind schema validation and simulation, and expose an explanation API.

**Headline success criteria:** by end of Phase 4, every generated program is provably within evidence-based volume bands for its user; no user with a structured injury record is prescribed a provoking movement without a graded substitution path; ranking weights are learned from at least 5,000 logged swap preferences; and 8-week program completion rate is measured and improving against the v1 baseline.

---

## 2. Current-State Assessment

### 2.1 What is working and must be preserved

The assessment begins with the strengths, because several of them are load-bearing constraints on everything proposed below.

The **three-layer template model** (split, slot rules, progression reference) correctly separates reusable structure from concrete exercise selection, which is what makes the catalog small, auditable, and forward-compatible with automated authoring. The **feasibility gate** correctly treats equipment availability as a hard constraint rather than a scored preference. **Base-week + constraints-overlay storage** keeps re-adaptation cheap and localized — an edit re-runs a handful of slots, not the program — and **derive-at-read progression** avoids materializing weeks. **Determinism** (same inputs → same program) is essential for testing, support, and user trust, and every proposal in this document is required to preserve it: all new algorithms specified here are deterministic, including the learning components, which train offline and deploy as fixed parameter sets.

### 2.2 Deficiencies, by discipline

**Movement science.** The system has no representation of the quantities that training outcomes actually depend on. Weekly per-muscle set volume, per-muscle training frequency, and intensity distribution are nowhere computed or bounded. `complementary_coverage` (weight 1.25 in slot ranking) nudges muscle spread but is a soft ranking signal, not a budget — a template plus greedy selection can silently produce 26 weekly pressing sets and 4 hamstring sets, and nothing in the pipeline would notice. Progression is open-loop: `deload_every: 4` deloads on a calendar regardless of accumulated fatigue, and the user's `effort_method: RPE` preference changes display, not behavior. `fitness_focus` as a single enum cannot represent the majority case of mixed goals ("lose fat and get stronger"), and the system encodes no concurrent-training interference rules. Prescriptions omit rest intervals, tempo, and warm-up/ramping sets — cheap to derive, and their absence is the most visible quality gap to an experienced user.

**Physical therapy.** `injuries_limitations` is free text, yet the filter `contraindications ∩ injuries = ∅` presumes structured, matchable data; in practice the intersection is either unreliable or vacuous. The model is binary — a resolved decade-old ankle sprain and an acute lumbar disc issue produce the same behavior — and exclusionary: a knee complaint deletes the squat pattern rather than regressing it to a box squat or hip-dominant variant at capped load. There is no in-program monitoring: a user experiencing escalating discomfort has no structured way to report it and the system no way to respond. There are no ramp-rate guards limiting week-over-week volume increases for beginners, which is both a safety and an adherence issue.

**Mathematics.** Three structural problems. First, the linear weighted sum is *fully compensatory*: with goal weighted 0.25, a template scoring 0.0 on goal can still reach 75% fit — but a pure-strength template for a weight-loss-focused user is a category error, not a 75% answer. Second, `range_fit` normalizes distance by `max(low, 1)`, making the penalty asymmetric and unstable: templates with small lower bounds are punished savagely for the same absolute miss, and the function is non-smooth at the interval boundary. Third, greedy per-slot selection is order-dependent and suboptimal by construction, because two ranking factors (`variety`, `complementary_coverage`) depend on picks already made; the quality of a session therefore depends on the arbitrary order slots are authored in. Additionally, the fit percentage implies a calibration ("87% fit") that has never been validated against any outcome, and the fourteen hand-tuned weights across matching and ranking encode one author's intuition with no mechanism to improve.

**Software & infrastructure.** Active programs reference templates and progression models by mutable key: editing a template or changing `linear_load`'s code silently rewrites the derived weeks of every in-flight program. Scoring weights and thresholds live in code, so no experiment can compare formulas without a deploy. The exercise library — whose tags drive filtering, ranking, feasibility, and safety — has no schema validation, no reachability checks (is every `pattern` fillable in every `environment_type`?), and no CI gate. Rich decision data (score breakdowns, swaps, locks, completions) is discarded rather than logged, forfeiting both the learning opportunity and the ability to explain decisions to users.

### 2.3 Assessment summary

| Dimension | Current state | Target state |
|---|---|---|
| Training dose | Unmodeled | Per-muscle volume/frequency ledger with evidence-based bands |
| Goals | Single enum | Weight vector with interference rules |
| Injury handling | Free text, binary exclusion | Structured taxonomy, graded substitution, monitoring |
| Matching math | Compensatory linear sum, unstable kernel | Hard/soft split, geometric aggregation, smooth kernels |
| Slot assignment | Greedy, order-dependent | Beam search over sessions with ledger-aware objective |
| Progression | Calendar-driven, open-loop | Autoregulated, reactive to logged RPE/readiness |
| Weights | Hand-tuned in code | Config-externalized, then learned from swap telemetry |
| Template/model refs | Mutable keys | Version-pinned at accept time |
| Exercise library | Unvalidated | Schema + reachability CI, publishing gate |
| Explainability | None | Per-decision explanation API |

---
## 3. Workstream A — Mathematical Redesign of Matching and Selection

**Objective.** Make template matching non-compensatory where it must be, smooth and symmetric where it scores, and make slot assignment optimize whole sessions rather than isolated slots — all while remaining deterministic and fast.

### 3.1 Constraint architecture: hard, near-hard, and soft factors

Reclassify the seven matching factors into three tiers.

*Hard constraints* (filter, never scored): equipment feasibility (already implemented — retained unchanged) and safety feasibility (new, from Workstream C: a template is infeasible if any required pattern has no permissible variant for the user's injury profile even after regression).

*Near-hard factors* (multiplicative, can collapse a score but not to zero): `goal` and `experience`. A template that misses on these should rank far below any template that satisfies them, regardless of soft-factor performance.

*Soft factors* (compensatory among themselves): `days`, `duration`, `movement_preference`, `focus_complement`, `periodization`.

The aggregation replaces the linear sum with a floored weighted geometric mean over near-hard factors, multiplied by a weighted arithmetic mean over soft factors:

```
soft  = (w_d·days + w_u·duration + w_m·move_pref + w_f·focus + w_p·period) / Σw
fit   = goal'^α · experience'^β · soft
        where x' = max(x, ε),  ε = 0.10,  α = β = 1 initially
```

The floor ε prevents literal zeroing (a goal-mismatched template can still appear if the user has exhausted matches, but at ≤10% of an otherwise-equal matched template's score). Exponents α, β are config-tunable severity knobs. This preserves the existing 0–1 scale and top-3 return contract.

**Goal factor generalization (feeds Workstream B).** Replace the binary membership test with a cosine-style overlap between the user's goal weight vector *g* (e.g., `{weight_loss: 0.6, strength: 0.4}`) and the template's goal set *T*:

```
goal = Σ_{t ∈ T} g_t        (sum of user weight mass covered by the template)
```

This is backward compatible: a single-focus user reduces to the current binary behavior.

### 3.2 Symmetric smooth range kernel

Replace `range_fit` with a Gaussian kernel on the distance to the interval:

```
d(v, lo, hi)      = max(0, lo − v, v − hi)
range_fit(v)      = exp( −(d/σ)² )
```

with per-dimension tolerances in config: σ_days = 1.0 day, σ_duration = 15 minutes (initial values; tunable). Properties: equals 1.0 inside the interval, symmetric in absolute distance regardless of interval position, smooth at the boundary, and strictly monotone decreasing — so ranking among near-miss templates is stable and intuitive. A template asking for 5+ days penalizes a 3-day request exactly as a 2-day-max template penalizes a 4-day request.

### 3.3 Beam search for session assembly

Replace greedy per-slot selection with deterministic beam search over each session's ordered slots, scoring *partial sessions* rather than isolated picks.

```
function assemble_session(slots, pool, ledger, width=4):
    beams = [ (empty_assignment, ledger.copy()) ]
    for slot in slots:                                # authored order retained
        candidates = filter(pool, slot, user)         # existing filters + safety graph
        next_beams = []
        for (assign, led) in beams:
            for ex in top_k(candidates, k=width, key=slot_score(·, assign, led)):
                next_beams.append( (assign + {slot: ex}, led.apply(ex, slot)) )
        beams = top_n(next_beams, n=width, key=session_objective)
        # deterministic tie-break: (score desc, exercise_id asc)
    return argmax(beams, session_objective).assignment
```

`session_objective` is the sum of existing slot-ranking factors **plus two session-level terms** supplied by Workstream B: a volume-band penalty (distance of any muscle's projected weekly effective sets from its target band) and a frequency bonus. Complexity is O(slots × width² × pool), comfortably sub-100ms at ~135 exercises and width 4; width is a config knob and width = 1 reproduces current greedy behavior exactly, giving a safe rollback path. Cross-session effects (weekly volume, weekly variety) are handled by threading the ledger sequentially through sessions in split order, which is deterministic; full cross-session joint optimization is deferred to a later ILP formulation if evidence warrants (see §3.5).

### 3.4 Presentation of fit

Until the score is calibrated against outcomes (Workstream D §6.4), stop presenting an uncalibrated percentage as if it were a probability. Present ranked tiers — "Best match," "Strong match," "Possible match" — derived from score gaps, with the numeric score retained internally and in telemetry. When calibration data exists, the number returns with a defined meaning (predicted 8-week completion likelihood).

### 3.5 Formulation note for future optimization

The slot-assignment problem is a constrained assignment: binary variables x_{s,e} (exercise e fills slot s), linear objective from the ranking factors, and linear constraints from the volume ledger bands, variety, and feasibility. It is solvable exactly with an ILP solver in milliseconds at this scale. Beam search is proposed first because it requires no new dependency, degrades gracefully, and is easier to explain; the ILP formulation is documented in Appendix D as the sanctioned upgrade path if beam-search quality plateaus.

**Deliverables (Workstream A):** new scoring module behind a config flag; kernel and tier parameters in config; beam-search assembler with width knob; tie-break determinism tests; A/B harness comparing old vs. new formula on synthetic users; updated fit presentation.

**Acceptance criteria:** byte-identical determinism across runs; goal-mismatched templates never outrank goal-matched templates with soft scores within 0.3; p95 generation latency < 100ms retained; width=1 mode reproduces legacy output on the full synthetic-user suite.

---

## 4. Workstream B — The Physiological Accounting Layer (Volume Ledger)

**Objective.** Give the engine an explicit model of training dose — per-muscle weekly effective sets, frequency, and intensity distribution — validated against evidence-based landmarks, so that every generated program is *provably* within productive and safe ranges for its user.

### 4.1 The ledger data structure

The ledger is computed from a draft (and recomputed on any overlay mutation) — it is derived state, never stored as source of truth, consistent with the engine's derive-at-read philosophy.

```
Ledger = {
  muscle: {
    effective_sets_week: float,   # Σ over slots: sets × role_factor
    frequency_days: int,          # distinct training days hitting the muscle
    hard_set_share: float,        # share of sets at RPE ≥ 8 / ≥ 85% 1RM
  } for muscle in MUSCLE_TAXONOMY
}
role_factor: primary_mover = 1.0, secondary/synergist = 0.5, isometric/stabilizer = 0.25
```

`MUSCLE_TAXONOMY` is a fixed enumeration (~15 groups: quadriceps, hamstrings, glutes, calves, chest, lats, upper back, front/side/rear delts, biceps, triceps, forearms, core-anterior, core-posterior/erectors). Every exercise in the library must declare primary and secondary muscles from this taxonomy — enforced by the Workstream E library linter.

### 4.2 Volume landmark bands

Per-muscle weekly effective-set bands, parameterized by experience and goal emphasis, stored in config with literature citations attached to each row. Initial values (to be reviewed by the movement-science owner before ship):

| Experience | MEV (min effective) | Target band | MRV guard (max) |
|---|---|---|---|
| Beginner | 6 | 8–12 | 16 |
| Intermediate | 8 | 10–18 | 22 |
| Advanced | 10 | 12–20 | 26 |

Modifiers: muscles receiving goal emphasis (e.g., user's stated focus regions, future feature) shift the target band up by 2–4 sets; muscles under an amber injury flag (Workstream C) have their guard reduced by 30%. Sources for initial values: Schoenfeld et al. dose-response meta-analyses (2017, 2019); Israetel et al. MEV/MAV/MRV framework; Ralston et al. (2017) on weekly set volume and strength. Citations live in the config file itself so the product's scientific basis is auditable in one place.

### 4.3 Ledger as validator and objective term

The ledger operates at three points in the pipeline:

*During assembly* (Workstream A §3.3): the session objective includes `−λ_v · Σ_m band_distance(m)` and `+λ_f · frequency_bonus`, steering beam search toward balanced weeks (initial λ_v = 1.5, λ_f = 0.5, config).

*Post-draft validation:* after a full draft, any muscle below MEV or above the MRV guard triggers targeted re-selection of the lowest-scoring contributing (or non-contributing) slots — the same localized mechanism the feedback loop already uses, so implementation reuses `adaptation.py` machinery. If re-selection cannot satisfy the band (e.g., a concentrated-focus user with a 2-day split), the violation is *surfaced, not silently accepted*: the draft carries a structured advisory ("hamstrings receive 5 weekly sets, below the 8-set minimum for your level — consider adding a day or swapping X for Y").

*Frequency check:* each muscle at or above MEV volume should be trained on ≥2 distinct days where the split allows; a template whose structure makes this impossible for a muscle carrying significant volume receives an advisory at match time, feeding the match presentation.

### 4.4 Complete prescriptions: rest, tempo, warm-up

Derive-at-read is extended to produce full session prescriptions:

*Rest intervals* by scheme intent: main/strength schemes (≤6 reps or ≥85%): 2.5–4 min; hypertrophy schemes (6–12): 1.5–2.5 min; muscular-endurance/metabolic (>12): 45–90s. *Tempo* is prescribed only where it changes intent (e.g., eccentric emphasis in early rehab-adjacent regressions from Workstream C); default is "controlled." *Warm-up ramping* for the first primary slot of each session: an algorithmic ramp (e.g., ~40%×5, ~60%×3, ~80%×1 of first working load) generated from the derived working load, plus a general preparation note. All are pure functions of scheme + goal + load — no storage change.

### 4.5 Mixed goals and interference management

With the goal vector from §3.1, encode concurrent-training rules as scheduling constraints applied when a template includes conditioning slots or the user's goal vector includes endurance mass:

1. High-intensity endurance work and heavy lower-body strength work are not scheduled in the same session block; where the split forces same-day placement, strength precedes conditioning and an advisory recommends ≥6h separation.
2. Low-intensity steady-state carries no separation constraint.
3. For weight-loss-weighted vectors, the engine biases toward higher-frequency full-body structures and appends optional conditioning finishers rather than displacing strength slots — preserving the resistance-training base that protects lean mass in a deficit.

**Deliverables (B):** muscle taxonomy + library tag migration; ledger computation module; banded config with citations; assembly objective terms; post-draft validator with advisory schema; rest/tempo/warm-up derivation; interference scheduler.

**Acceptance criteria:** 100% of synthetic-suite drafts either satisfy all bands or carry an explicit advisory; ledger recomputation after a single swap touches only affected muscles' entries; every band row in config carries at least one citation; latency budget retained.

---
## 5. Workstream C — Graded Safety and Injury Model

**Objective.** Replace free-text injuries and binary exclusion with a structured, phase-aware injury model whose default response is *graded substitution*, backed by in-program monitoring and conservative ramp guards.

### 5.1 Structured injury taxonomy

```
InjuryRecord = {
  region:        enum   # shoulder, elbow, wrist, cervical, thoracic, lumbar,
                        # hip, knee, ankle/foot  (matches contraindication regions)
  condition:     enum   # acute_pain, post_surgical, tendinopathy, joint_instability,
                        # chronic_recurrent, resolved_cautious, unspecified
  phase:         enum   # acute | rehabilitating | resolved_cautious | cleared
  provocations:  set    # loaded_spinal_flexion, overhead, deep_knee_flexion,
                        # impact, heavy_hinge, end_range_shoulder, grip_intensive, ...
  severity:      1–3
  reported_at:   date
  source:        user_reported | professional_cleared
}
```

*Intake.* Existing and future `injuries_limitations` free text is mapped into `InjuryRecord[]` by an LLM intake step whose output is **always shown to the user for confirmation** before it affects any program — the LLM proposes, the user disposes, and only the confirmed structured record enters the pipeline. This is the highest-leverage, lowest-risk use of an LLM in the system: structured extraction with human confirmation, never direct program generation. The intake prompt, schema, and confirmation UI are deliverables; the free-text field is retained as provenance.

*Scope boundary.* The product provides training accommodation, not diagnosis or treatment. Acute-phase or severity-3 records trigger a standing recommendation to consult a qualified professional, and certain combinations (e.g., acute + post_surgical) hard-exclude the affected patterns entirely until the record is updated — the one place binary exclusion remains correct.

### 5.2 Regression/progression graphs per movement pattern

For each movement `pattern` in the template vocabulary, author a small directed graph of variants ordered by demand along named axes (load axis, range-of-motion axis, stability axis, impact axis). Example for `squat`:

```
back_squat ── load ──▶ goblet_squat ── ROM ──▶ box_squat_high ──▶ split_squat_supported
     │
     └── axis: hip_dominant_alternative ──▶ hip_hinge variants (cross-pattern substitute)
```

Graph edges carry the provocation axes they relieve (`deep_knee_flexion`, `spinal_loading`, …). Selection logic changes from *exclude if contraindicated* to:

1. If a candidate's contraindication tags intersect the user's active provocations, walk the regression graph along the relieving axes to the nearest permissible variant available in the user's environment.
2. Apply a load cap and slower ramp (see §5.4) to substituted slots for `rehabilitating`-phase records.
3. Only if no permissible variant exists in the environment does the slot fall back to a cross-pattern substitute; only if that also fails is the pattern excluded — and the exclusion is surfaced as an advisory, never silent.

The graphs double as a beginner-progression asset: a user failing a movement in-program can be regressed along the same edges, and a `resolved_cautious` user can be *progressed* back toward the canonical variant over mesocycles.

*Feasibility interaction.* Workstream A's safety-feasibility hard gate is defined precisely here: a template is safety-infeasible for a user iff some slot's pattern has an empty permissible set after graph traversal and cross-pattern fallback.

### 5.3 Traffic-light session monitoring

Append a 10-second post-session check-in: per body region touched today, the user taps green / amber / red (optionally with a note).

*Green:* no action. *Amber (discomfort, ≤3/10, no next-day worsening):* automatic 10–20% load reduction on the provoking pattern next session, selection bias (−1.0 score adjustment) against the flagged variant, ledger guard on that region reduced 30%; two consecutive ambers on the same region escalate to a regression-graph step down. *Red (pain ≥4/10, sharp, or worsening):* the provoking pattern is removed via graph fallback for the mesocycle, an `InjuryRecord` draft (phase: acute) is created for user confirmation, and the professional-consultation message is shown. All transitions are logged (Workstream E) and reversible by the user updating the record.

### 5.4 Ramp-rate guards

Deterministic caps on week-over-week increases in per-muscle effective volume and per-lift load, layered *on top of* whatever the progression model proposes:

| Population | Volume ramp cap (weekly) | Load ramp cap (per lift) |
|---|---|---|
| Beginner | +20% | model default |
| Post-amber / rehabilitating slot | +10% | +2.5% or smallest increment |
| Returning after ≥2 missed weeks | restart at 70% of last completed week | −10%, re-ramp |

Because progression is derived at read time, guards are implemented as a wrapper (like the existing `deload` wrapper) around progression models — no storage change.

**Deliverables (C):** taxonomy + migration; LLM intake with confirmation UI; regression graphs for all patterns in the template vocabulary (initial authoring: movement-science owner, reviewed by PT consultant); graph-aware selection; check-in UI + state machine; ramp wrapper; advisory surfaces.

**Acceptance criteria:** zero silent exclusions in the synthetic suite (every safety-driven change carries an advisory); every pattern has a graph with ≥2 regression steps and ≥1 cross-pattern substitute; red-flag flow reachable in ≤2 taps post-session; intake never mutates a program without explicit confirmation.

---

## 6. Workstream D — Closing the Adaptive Loop

**Objective.** Convert logged training data into program adjustments (autoregulation), convert user edits into better ranking (learning-to-rank), and convert outcomes into a calibrated fit score — while keeping runtime behavior deterministic.

### 6.1 RPE and readiness as inputs

Per working set (or per exercise, configurable friction level), the user logs actual RPE and reps; a one-tap session readiness score (1–5) is requested at session start. These are the loop's sensor layer. For `%1RM` users, estimated 1RM from logged load×reps (Epley) serves the same role.

### 6.2 Autoregulated load adjustment

A deterministic controller wraps the progression model at derive-time:

```
signal   = EWMA(actual_RPE − target_RPE, span = 3 sessions, per lift)
adjust   = clamp(−k · signal, −7.5%, +5%)          # k = 2.5%/RPE-point, config
next_load = ramp_guard( model_load(week) × (1 + adjust) )
```

Overshooting users (signal > +1 for two sessions) get backed off before failure; sandbagging or fast-adapting users (signal < −1) progress faster than the calendar. The controller is a pure function of logged history — determinism is preserved as "same inputs *including logs* → same output."

### 6.3 Reactive deloads

Replace calendar-only deloads with a fatigue trigger evaluated weekly: deload fires when **any two** of the following hold — mean readiness < 3 over the last 4 sessions; RPE signal > +1 across ≥2 primary lifts; performance regression (e1RM down ≥5% on a primary lift); ≥1 amber flag active. The calendar `deload_every` remains as a backstop ceiling (deload no later than N weeks) rather than the driver. Implemented as a condition inside the existing `deload` wrapper.

### 6.4 Learning-to-rank from swap telemetry

Every swap is a labeled preference: in context c (user, slot, session state, ledger), the user rejected exercise e⁻ for e⁺. Log the full feature vector already computed for ranking (priority_fit, movement_preference, complementary_coverage, variety, muscle_fit, difficulty, unilateral_balance, plus ledger terms) for both exercises. Offline, fit a pairwise logistic (Bradley–Terry) model:

```
P(e⁺ ≻ e⁻ | c) = σ( wᵀ(φ(e⁺,c) − φ(e⁻,c)) )
```

The learned w replaces the hand-tuned ranking weights *as a config deploy*, keeping runtime deterministic and the model fully inspectable (it is literally a better-informed version of today's weight table). Trigger: first training at ≥5,000 logged swap pairs; guard: new weights ship behind the A/B harness and must not regress advisory rates or latency. Regularize toward current hand weights so early data cannot produce wild swings. The same pipeline later admits per-segment weights (by experience level or goal vector) if data volume supports it.

### 6.5 Outcome calibration of fit

Define the target outcome as 8-week program completion (≥70% of scheduled sessions logged). Once ≥1,000 accepted programs have matured, calibrate the match score against completion via isotonic regression; thereafter the fit number shown to users is the calibrated completion likelihood — a number with defined, honest meaning — replacing the tiered presentation of §3.4.

**Deliverables (D):** logging schema for sets/readiness; controller + reactive-deload wrappers; swap-preference logging; offline training pipeline + weight-deploy path; calibration job; A/B harness integration.

**Acceptance criteria:** controller unit-tested against synthetic log trajectories (overshoot, undershoot, noisy); deload fires in synthetic fatigue scenarios and not in control scenarios; learned-weight deploy is a pure config change; all logging opt-out respects user privacy settings.

---
## 7. Workstream E — Platform, Authoring, and Trust Infrastructure

**Objective.** Harden the substrate every other workstream depends on: immutability where users depend on stability, configuration where experimentation is needed, validation where data drives behavior, telemetry where learning happens, and explanation where trust is earned.

### 7.1 Versioning and pinning

Templates and progression models become immutable versioned artifacts. `ProgramTemplate` gains `(template_key, version)`; edits create a new version, and matching always uses the latest. At **accept time**, the program pins `(template_key, template_version)` and `(model_key, model_version, params_snapshot)`; derive-at-read resolves against pinned versions, so no code or catalog change ever silently rewrites an in-flight program's weeks. Progression model code is versioned by registering each behavioral change as a new `model_version` in the progression registry; a CI test derives a golden-file week set per (model, version) to catch accidental behavioral drift.

### 7.2 Configuration externalization

One reviewed, versioned config surface (file or table, per existing conventions) holds: matching tiers, exponents, floors; range-kernel σ per dimension; beam width; ranking weights (hand or learned, with provenance field); ledger bands + citations; band modifiers; ramp caps; controller gains; deload trigger thresholds. Config changes are deployable without code release and are recorded in telemetry alongside every generation, so any program can be reproduced exactly from (inputs, config version, catalog versions) — extending the determinism guarantee across time.

### 7.3 Exercise library as validated data

The library is the true dependency of every downstream behavior; treat it like code. A CI linter enforces: schema validity (all tags from closed vocabularies, including the new muscle taxonomy and provocation tags); *reachability* — for every `environment_type` × `pattern` used by any active template, at least one exercise is available at beginner-permissible difficulty, and at least one regression-graph path is intact; *graph integrity* — every graph node exists in the library, every edge's relieving axes are declared; *coverage* — every muscle in the taxonomy is a primary mover of ≥3 exercises across ≥2 environments; orphan and duplicate detection. The linter runs on every library or template change and is the publishing gate for §7.5.

### 7.4 Telemetry pipeline

Log, with user consent and privacy controls: per-match score breakdowns (all factors, both formulas during A/B); per-slot ranking features and the chosen exercise; every feedback action (swap/exclude/lock/adjust) with full context; session logs, readiness, flags; advisory impressions and dismissals; config/catalog versions. This single pipeline feeds Workstream D's learning, §7.6's explanations, product analytics, and support/debug reproduction. Retention and anonymization policy is a deliverable, not an afterthought.

### 7.5 Gated LLM-assisted authoring (roadmap item, de-risked)

When the planned form-based and LLM-assisted template builders arrive, publication requires passing, in order: JSON-schema validation of the three-layer shape → library-linter reachability against all claimed `environment_type`s and experience levels → **simulation gate**: the candidate template is drafted against a fixed panel of ~200 synthetic users (spanning goals, experience, equipment, injury profiles) and must produce zero crashes, zero empty pools, zero un-advised band violations, and match-rate sanity vs. catalog peers → human review of the simulation report. LLMs author *candidates*; the deterministic pipeline remains the arbiter of what ships.

### 7.6 Explanation API

Because every factor is already computed, explanations are nearly free. Two endpoints: *why this template* (top contributing factors, any advisories: "matches your strength focus and 4-day availability; note: rear delts run below target volume — an accessory swap is suggested") and *why this exercise* (top ranking factors + ledger contribution: "chosen because it targets your under-covered hamstrings, fits your barbell preference, and hasn't appeared elsewhere this week"). Explanations render in the draft-review UI next to each slot and materially change the feedback loop: users who understand *why* make better swaps, and better swaps make better training data (§6.4). Safety-driven substitutions always explain themselves ("box squat substituted for back squat due to your reported knee issue — depth reduced, load capped").

### 7.7 Testing strategy

Three layers. *Property-based tests* on invariants: feasibility gates never emit unfillable templates; ledger totals are conserved under swaps; ramp guards never exceeded; determinism (byte-identical output for identical inputs+config+catalog). *Golden files* per progression model version and per template version. *Synthetic-user simulation harness* (shared with §7.5): thousands of sampled profiles run through the full pipeline on every merge, asserting no crashes, no empty candidate pools, latency budget, and advisory-rate bounds — this harness is also the A/B evaluation environment for Workstreams A and D.

**Deliverables (E):** version pinning + migration for in-flight programs; config surface; library linter in CI; telemetry schema + pipeline + retention policy; simulation harness; explanation endpoints + UI integration; authoring gate spec.

**Acceptance criteria:** an in-flight program's derived weeks are bit-stable across template edits and model code changes; any historical program is reproducible from logged versions; linter blocks a seeded set of known-bad library mutations; explanation coverage on 100% of drafted slots.

---

## 8. Phased Roadmap

Phases are sequenced by dependency, not by discipline; every phase ships user-visible value.

**Phase 1 — Correct the mathematics (≈ 4–6 weeks).** Workstream A in full, plus the config surface (§7.2) and the simulation/A-B harness (§7.7) needed to validate it, plus swap/score telemetry logging (§7.4) so the data flywheel starts immediately even though nothing consumes it yet. *Exit:* new formula live behind flag, harness comparison report, telemetry flowing.

**Phase 2 — Physiological ledger (≈ 6–8 weeks).** Muscle taxonomy migration and library linter (§7.3, pulled forward as a dependency), full Workstream B: ledger, bands, assembly terms, validator + advisories, rest/tempo/warm-up, goal vectors + interference rules. *Exit:* every draft band-validated or advised; complete session prescriptions; citations shipping in config.

**Phase 3 — Graded safety (≈ 6–8 weeks).** Workstream C in full: taxonomy + LLM intake with confirmation, regression graphs, substitution selection, traffic-light monitoring, ramp guards; explanation API (§7.6) ships here because safety substitutions must explain themselves. *Exit:* zero silent safety exclusions; monitoring live; PT-consultant sign-off on graphs and copy.

**Phase 4 — Adaptive loop (≈ 8–10 weeks).** Workstream D: set/readiness logging, autoregulation controller, reactive deloads; first learned-weight training when the 5,000-swap threshold is met; calibration job scheduled. Version pinning (§7.1) completes here before behavior becomes history-dependent. *Exit:* autoregulation live for RPE users; deload triggers validated; learning pipeline producing candidate weights.

**Phase 5 — Authoring at scale (timeline gated on Phases 1–4 stability).** Form-based builder, LLM-assisted authoring behind the §7.5 gate, catalog expansion, per-segment learned weights, ILP assembler evaluation (Appendix D), calibrated fit percentage restored to the UI. *Exit:* externally authored template published through the full gate; calibrated fit live.

**Program-level success metrics** (tracked from Phase 1 baseline): 8-week completion rate; swap rate per draft (expected to *fall* as ranking improves); advisory violation rate; amber/red flag rates and their trend post-Phase-3; p95 generation latency; support tickets attributable to program changes (expected to fall to ~zero after pinning).

---

## 9. Risks and Mitigations

**Scientific-liability creep.** As the product cites literature and handles injuries, it edges toward medical territory. *Mitigation:* the §5.1 scope boundary (accommodate, never diagnose), professional-consultation triggers, PT-consultant review of all graphs and copy, and legal review of advisory language in Phase 3.

**Evidence contestability.** Volume landmarks are an active research area with genuine disagreement. *Mitigation:* bands are config with citations, deliberately wide, owned by a named movement-science owner with a scheduled annual literature review; the system's claim is "within evidence-based ranges," not "optimal."

**Complexity vs. the engine's core virtue (simplicity/speed).** *Mitigation:* every addition is a pure function or a wrapper on existing extension points (progression wrappers, overlay re-selection); width=1 and legacy-formula flags preserve full rollback; latency is an acceptance criterion in every phase.

**Cold-start and low data volume for learning.** *Mitigation:* hand weights remain the prior (regularization target); explicit data thresholds (5,000 swaps; 1,000 matured programs) before any learned artifact ships; harness gate on every weight deploy.

**User friction from logging and check-ins.** *Mitigation:* all sensors are optional and tiered (per-session readiness is one tap; per-set RPE is opt-in); the system degrades gracefully to calendar behavior when data is absent.

**LLM intake errors on injury data.** *Mitigation:* confirmation-required design — no LLM output touches a program without explicit user approval; conservative default (unconfirmed extraction is ignored, free text preserved).

**Library tagging debt.** The muscle-taxonomy and provocation-tag migration across ~135 exercises is tedious and error-prone. *Mitigation:* LLM-assisted first pass, human-verified, linter-enforced thereafter; budgeted explicitly in Phase 2.

---

## 10. Governance and Ownership

Each workstream names a single accountable owner: A — backend/algorithms engineer; B — movement-science owner (with engineering pair); C — movement-science owner with external PT consultant sign-off; D — ML-inclined engineer; E — infrastructure engineer. A standing fortnightly review evaluates harness reports and advisory-rate dashboards. Config changes to bands, weights, or safety thresholds require review by the relevant domain owner. The annual scientific-review cycle (§9) is a calendared obligation with a written changelog.

---

## Appendix A — Matching Formula (consolidated)

```
# Hard gates (filter)
feasible(t, u)        : equipment feasibility ∧ safety feasibility (graph-aware)

# Factors (all ∈ [0,1])
goal(t, u)            = Σ_{g ∈ t.goals} u.goal_vector[g]
experience(t, u)      = 1.0 if u.exp ∈ t.exp_levels else 0.3
days(t, u)            = exp(−(d(u.days, t.d_min, t.d_max)/σ_days)²)
duration(t, u)        = exp(−(d(u.dur,  t.s_min, t.s_max)/σ_dur)²)
move_pref, focus, per : as currently defined

# Aggregation
soft = (0.24·days + 0.16·duration + 0.30·move_pref + 0.24·focus + 0.06·per)   # renormalized soft weights, config
fit  = max(goal, 0.10)^α · max(experience, 0.10)^β · soft                      # α = β = 1.0, config
d(v, lo, hi) = max(0, lo − v, v − hi)
```

## Appendix B — Volume Ledger (consolidated)

```
effective_sets(m) = Σ_slots sets(slot) · role(m, exercise(slot))     role ∈ {1.0, 0.5, 0.25}
band(m, u)        = table[u.experience] shifted by emphasis/injury modifiers (§4.2)
band_distance(m)  = max(0, MEV − v, v − MRV_guard) where v = effective_sets(m)
session_objective = Σ_slot slot_score(slot) − λ_v·Σ_m band_distance(m) + λ_f·freq_bonus
```

## Appendix C — Autoregulation Controller (consolidated)

```
signal(lift)   = EWMA(RPE_actual − RPE_target, span=3)
adjust(lift)   = clamp(−0.025 · signal, −0.075, +0.05)
load(lift, wk) = ramp_guard( model_load(lift, wk) · (1 + adjust(lift)) )
deload fires when ≥2 of: mean_readiness₄ < 3 · signal > 1 on ≥2 primaries ·
                         e1RM drop ≥ 5% on a primary · active amber flag
backstop: deload no later than template.deload_every weeks
```

## Appendix D — ILP Formulation (future assembler)

Variables x_{s,e} ∈ {0,1}. Objective: maximize Σ score(s,e)·x_{s,e} − λ_v·Σ_m slack_m. Constraints: Σ_e x_{s,e} = 1 per slot; feasibility fixes x = 0 for filtered pairs; variety: Σ_s x_{s,e} ≤ 1 per movement per week (soft via penalty if preferred); ledger: MEV_m − slack_m ≤ Σ x·sets·role ≤ MRV_m + slack_m. Deterministic given a fixed solver seed and tie-break ordering; adopt only if beam-search quality measurably plateaus in harness metrics.

## Appendix E — Key References (initial band sourcing)

Schoenfeld, Ogborn & Krieger (2017), dose-response of weekly set volume and hypertrophy, *J Sports Sci*. Schoenfeld et al. (2019), volume and hypertrophy in trained men, *MSSE*. Ralston et al. (2017), weekly set volume and strength gain, *Sports Med*. Israetel et al., volume landmarks framework (MEV/MAV/MRV), Renaissance Periodization. Helms et al., RPE-based autoregulation in resistance training. Wilson et al. (2012), concurrent training interference meta-analysis, *JSCR*. Grgic et al. (2018), training frequency and hypertrophy, *Sports Med*. Full citation list to be finalized by the movement-science owner during Phase 2 config authoring.

---

*End of proposal. Approval of Phase 1 authorizes Workstream A plus the config, harness, and telemetry prerequisites drawn from Workstream E.*
