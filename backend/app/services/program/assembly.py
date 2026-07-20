"""Beam-search session assembly (plan §1.5/§2.5).

`assemble_session` explores several partial slot assignments in parallel and returns
the one maximizing `session_objective = Σ slot_score − λ_v·Σ band_distance + λ_f·freq_bonus`,
where `slot_score` comes from the existing `HeuristicExerciseScorer`/`_extract_features`
machinery and the ledger term (plan §2.5) is active only when a real `EngineConfig` is
supplied. `width=1` reproduces `build_draft`'s greedy per-slot loop exactly (there is
only ever one beam, so no tie-break is exercised and each slot takes `ranked[0]`).

When `config` is `None` (every call site before Task 2.5a, and every direct unit test
in `test_assembly.py` that doesn't pass one), the ledger term's code path is skipped
entirely -- not merely multiplied by zero -- so there is zero risk of it perturbing the
pre-2.5a objective.
"""

from collections import Counter
from dataclasses import dataclass, field, replace

from app.models.exercise import Exercise
from app.schemas.template import SchemeDef, SlotRule
from app.services.program.engine_config import EngineConfig
from app.services.program.ledger import LedgerAccumulator, LedgerPick, band_for_experience
from app.services.program.selection import (
    HeuristicExerciseScorer,
    SelectionContext,
    _extract_features,
    ranked_pool_for_slot,
)


@dataclass(frozen=True)
class SlotAssignment:
    """One filled slot: its 1-based position in the session (so the caller can assign
    `WorkoutExercise.order` with the same gaps greedy leaves for skipped slots), the rule
    it satisfies, the chosen exercise, and the ranked candidate list at the moment of
    selection (needed for `rotation_pool_ids`)."""

    order: int
    rule: SlotRule
    exercise: Exercise
    ranked_candidates: list[Exercise]


@dataclass
class _Beam:
    assignments: list[SlotAssignment] = field(default_factory=list)
    used_movement_slugs: set[str] = field(default_factory=set)
    used_unilateral_flags: list[bool] = field(default_factory=list)
    muscle_coverage: "Counter[str]" = field(default_factory=Counter)
    ledger: LedgerAccumulator = field(default_factory=LedgerAccumulator)
    objective: float = 0.0

    def _latest_exercise_id(self) -> int:
        return self.assignments[-1].exercise.id if self.assignments else -1


def _ledger_adjustment(
    config: EngineConfig,
    experience: str,
    beam_ledger: LedgerAccumulator,
    rule: SlotRule,
    ex: Exercise,
    schemes: dict[str, SchemeDef],
    workout_key: str,
) -> tuple[float, LedgerAccumulator]:
    """Score the ledger impact of picking `ex` at `rule` against `beam_ledger`'s current
    running state (plan §2.5, proposal Appendix B). Returns `(ledger_term, hyp_ledger)`:
    `hyp_ledger` is `beam_ledger.clone()` with the pick applied, for the caller to carry
    forward as the winning child's ledger.

    `before`/`after` are both read off `beam_ledger` -- which already accumulates
    sequentially across this session's own slots (each winning child's ledger carries
    into the next slot) and starts seeded from `ctx.ledger` (prior sessions) -- rather
    than a separate frozen "session-start" snapshot. That's what makes `freq_bonus`
    naturally fire only for the specific slot that pushes a group from 1 to 2 distinct
    days: a later slot in the same session that touches an already-2-day group sees
    `before.frequency_days == 2`, not `1`, so the condition correctly doesn't re-fire.
    A frozen session-start snapshot would get this wrong (re-firing for every slot in
    the session that touches the group).
    """
    scheme = schemes[rule.scheme]
    pick = LedgerPick(exercise_id=ex.id, workout_key=workout_key, sets=scheme.sets, is_hard=(rule.scheme == "main"))
    before_snapshot = beam_ledger.snapshot()
    hyp_ledger = beam_ledger.clone()
    hyp_ledger.apply(pick, ex)
    after_snapshot = hyp_ledger.snapshot()

    band = band_for_experience(config.volume_bands, experience)
    band_distance_sum = sum(
        max(0.0, band.mev - g.effective_sets_week, g.effective_sets_week - band.mrv_guard)
        for g in after_snapshot.values()
    )
    freq_bonus = sum(
        1
        for group, before_g in before_snapshot.items()
        if before_g.frequency_days == 1
        and after_snapshot[group].frequency_days == 2
        and after_snapshot[group].effective_sets_week >= band.mev
    )
    ledger_term = -config.assembly.lambda_v * band_distance_sum + config.assembly.lambda_f * freq_bonus
    return ledger_term, hyp_ledger


def assemble_session(
    slots: list[SlotRule],
    pool: list[Exercise],
    ctx: SelectionContext,
    width: int,
    *,
    config: EngineConfig | None = None,
    schemes: dict[str, SchemeDef] | None = None,
    workout_key: str | None = None,
) -> list[SlotAssignment]:
    """Beam over ordered `slots`, returning the winning path's slot assignments.

    Pure function: `ctx` is treated as a read-only snapshot of the session's starting
    variety/coverage/ledger state and is never mutated. Each beam carries its own copies
    of the mutable context fields (`used_movement_slugs`, `used_unilateral_flags`,
    `muscle_coverage`, `ledger`) so speculative branches never leak state into one another.

    The ledger term (plan §2.5, `-lambda_v * band_distance + lambda_f * freq_bonus`) is
    active only when `config` is not `None` -- in which case `schemes` and `workout_key`
    must also be provided (an internal `build_draft` <-> `assemble_session` contract, not
    user input; violating it is a caller bug, hence the plain `assert`). When `config` is
    `None`, the ledger term's code path is skipped entirely: nothing is cloned, applied,
    or snapshotted beyond the initial (cheap, no-op-for-scoring) beam seed below.
    """
    if config is not None:
        assert (
            schemes is not None and workout_key is not None
        ), "assemble_session requires schemes and workout_key when config is provided"
    scorer = HeuristicExerciseScorer(ctx.weights)
    # Seed the first beam from ctx's accumulated state (variety/coverage/ledger span the
    # whole program, not just this session) -- copied so ctx itself is never mutated.
    beams: list[_Beam] = [
        _Beam(
            used_movement_slugs=set(ctx.used_movement_slugs),
            used_unilateral_flags=list(ctx.used_unilateral_flags),
            muscle_coverage=ctx.muscle_coverage.copy(),
            ledger=ctx.ledger.clone(),
        )
    ]
    for order, rule in enumerate(slots, start=1):
        next_beams: list[_Beam] = []
        for beam in beams:
            beam_ctx = replace(
                ctx,
                used_movement_slugs=beam.used_movement_slugs,
                used_unilateral_flags=beam.used_unilateral_flags,
                muscle_coverage=beam.muscle_coverage,
            )
            ranked = ranked_pool_for_slot(pool, rule, beam_ctx, set())
            if not ranked:  # empty pool: carry this beam forward unchanged (mirrors greedy skip)
                next_beams.append(beam)
                continue
            for ex in ranked[:width]:
                slot_score = scorer.score(_extract_features(ex, rule, beam_ctx))
                child_objective = beam.objective + slot_score
                child_ledger = beam.ledger
                if config is not None:
                    assert schemes is not None and workout_key is not None
                    ledger_term, hyp_ledger = _ledger_adjustment(
                        config, ctx.experience, beam.ledger, rule, ex, schemes, workout_key
                    )
                    child_objective = beam.objective + slot_score + ledger_term
                    child_ledger = hyp_ledger
                child = _Beam(
                    assignments=[*beam.assignments, SlotAssignment(order, rule, ex, ranked)],
                    used_movement_slugs=set(beam.used_movement_slugs),
                    used_unilateral_flags=list(beam.used_unilateral_flags),
                    muscle_coverage=beam.muscle_coverage.copy(),
                    ledger=child_ledger,
                    objective=child_objective,
                )
                child.used_movement_slugs.add(ex.movement_slug)
                child.used_unilateral_flags.append(ex.is_unilateral)
                for muscle in ex.primary_muscles:
                    child.muscle_coverage[muscle] += 1
                next_beams.append(child)
        # prune to `width`: objective desc, then most-recently-added exercise id asc on ties.
        beams = sorted(next_beams, key=lambda b: (-b.objective, b._latest_exercise_id()))[:width]
    # beams is sorted by the same objective/tie-break key, so beams[0] is the winner.
    return beams[0].assignments
