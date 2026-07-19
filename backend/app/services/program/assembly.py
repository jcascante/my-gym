"""Beam-search session assembly (plan §1.5).

`assemble_session` explores several partial slot assignments in parallel and returns
the one maximizing `session_objective = Σ slot_score`, where each slot's score comes
from the existing `HeuristicExerciseScorer`/`_extract_features` machinery. `width=1`
reproduces `build_draft`'s greedy per-slot loop exactly (there is only ever one beam,
so no tie-break is exercised and each slot takes `ranked[0]`).

Ledger/volume terms (plan §2.x) are intentionally out of scope here: the objective is
purely the sum of per-slot exercise scores.
"""

from collections import Counter
from dataclasses import dataclass, field, replace

from app.models.exercise import Exercise
from app.schemas.template import SlotRule
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
    objective: float = 0.0

    def _latest_exercise_id(self) -> int:
        return self.assignments[-1].exercise.id if self.assignments else -1


def assemble_session(
    slots: list[SlotRule],
    pool: list[Exercise],
    ctx: SelectionContext,
    width: int,
) -> list[SlotAssignment]:
    """Beam over ordered `slots`, returning the winning path's slot assignments.

    Pure function: `ctx` is treated as a read-only snapshot of the session's starting
    variety/coverage state and is never mutated. Each beam carries its own copies of the
    three mutable context fields (`used_movement_slugs`, `used_unilateral_flags`,
    `muscle_coverage`) so speculative branches never leak state into one another.
    """
    scorer = HeuristicExerciseScorer(ctx.weights)
    # Seed the first beam from ctx's accumulated state (variety/coverage span the whole
    # program, not just this session) -- copied so ctx itself is never mutated.
    beams: list[_Beam] = [
        _Beam(
            used_movement_slugs=set(ctx.used_movement_slugs),
            used_unilateral_flags=list(ctx.used_unilateral_flags),
            muscle_coverage=ctx.muscle_coverage.copy(),
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
                child = _Beam(
                    assignments=[*beam.assignments, SlotAssignment(order, rule, ex, ranked)],
                    used_movement_slugs=set(beam.used_movement_slugs),
                    used_unilateral_flags=list(beam.used_unilateral_flags),
                    muscle_coverage=beam.muscle_coverage.copy(),
                    objective=beam.objective + slot_score,
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
