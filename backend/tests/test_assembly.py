# backend/tests/test_assembly.py
"""Beam-search session assembly (plan §1.5)."""
from dataclasses import replace

from app.schemas.template import SlotRule
from app.services.program.assembly import assemble_session
from app.services.program.selection import (
    HeuristicExerciseScorer,
    SelectionContext,
    SelectionWeights,
    _extract_features,
)


class _Ex:
    def __init__(
        self,
        id,
        mslug,
        pattern,
        muscles,
        equip=(),
        diff="intermediate",
        contra=(),
        is_compound=True,
        is_unilateral=False,
    ):
        self.id, self.movement_slug = id, mslug
        self.movement_pattern = type("P", (), {"value": pattern})
        self.body_region = type("R", (), {"value": "upper_body"})
        self.primary_muscles, self.equipment_tags = list(muscles), list(equip)
        self.difficulty_level = type("D", (), {"value": diff})
        self.contraindications = list(contra)
        self.is_compound = is_compound
        self.is_unilateral = is_unilateral


# Only variety + muscle_fit are active, so intrinsic scores are controllable via
# muscle overlap and slug reuse. Everything else is zeroed out.
_ISOLATED_WEIGHTS = SelectionWeights(
    variety=1.0,
    priority_fit=0.0,
    muscle_fit=1.0,
    difficulty=0.0,
    unilateral_balance=0.0,
    movement_preference=0.0,
    complementary_coverage=0.0,
)


def _ctx(weights=None):
    return SelectionContext(
        equipment=[],
        experience="intermediate",
        injuries=[],
        used_movement_slugs=set(),
        weights=weights or _ISOLATED_WEIGHTS,
    )


def _replay_objective(assignments, base_ctx):
    """Independent oracle: sum slot scores by replaying picks through the scorer,
    accumulating variety/unilateral/coverage state exactly as build_draft would."""
    ctx = replace(
        base_ctx,
        used_movement_slugs=set(base_ctx.used_movement_slugs),
        used_unilateral_flags=list(base_ctx.used_unilateral_flags),
        muscle_coverage=base_ctx.muscle_coverage.copy(),
    )
    scorer = HeuristicExerciseScorer(ctx.weights)
    total = 0.0
    for a in assignments:
        total += scorer.score(_extract_features(a.exercise, a.rule, ctx))
        ctx.used_movement_slugs.add(a.exercise.movement_slug)
        ctx.used_unilateral_flags.append(a.exercise.is_unilateral)
        for m in a.exercise.primary_muscles:
            ctx.muscle_coverage[m] += 1
    return total


def test_single_slot_returns_best_candidate():
    a = _Ex(1, "s1", "horizontal_push", ["a", "b"])
    b = _Ex(2, "s2", "horizontal_push", ["a"])
    rule = SlotRule(pattern="horizontal_push", priority="accessory", scheme="accessory", muscles=["a", "b"])
    result = assemble_session([rule], [a, b], _ctx(), width=2)
    assert [x.exercise.id for x in result] == [1]
    assert [x.id for x in result[0].ranked_candidates] == [1, 2]


def test_multi_slot_session_fills_every_slot():
    a = _Ex(1, "s1", "horizontal_push", ["a"])
    c = _Ex(3, "s3", "horizontal_pull", ["c"])
    r1 = SlotRule(pattern="horizontal_push", priority="accessory", scheme="accessory", muscles=["a"])
    r2 = SlotRule(pattern="horizontal_pull", priority="accessory", scheme="accessory", muscles=["c"])
    result = assemble_session([r1, r2], [a, c], _ctx(), width=3)
    assert [x.exercise.id for x in result] == [1, 3]


def _greedy_vs_beam_fixture():
    # Slot1 picks A greedily (mf 1.0) but A's slug "shared" is also slot2's best (C).
    # Freeing "shared" by taking B at slot1 lets C win slot2 with a big variety gain,
    # so the global optimum is B,C -- which only width>1 finds.
    a = _Ex(1, "shared", "horizontal_push", ["a", "b"])
    b = _Ex(2, "b_only", "horizontal_push", ["a"])
    c = _Ex(3, "shared", "horizontal_pull", ["c", "d", "e"])
    d = _Ex(4, "d_only", "horizontal_pull", ["c"])
    r1 = SlotRule(pattern="horizontal_push", priority="accessory", scheme="accessory", muscles=["a", "b"])
    r2 = SlotRule(pattern="horizontal_pull", priority="accessory", scheme="accessory", muscles=["c", "d", "e"])
    return [r1, r2], [a, b, c, d]


def test_width_one_reproduces_greedy_local_choice():
    slots, pool = _greedy_vs_beam_fixture()
    result = assemble_session(slots, pool, _ctx(), width=1)
    assert [x.exercise.id for x in result] == [1, 4]  # A then D (locally optimal per slot)


def test_beam_finds_better_objective_than_greedy():
    slots, pool = _greedy_vs_beam_fixture()
    ctx = _ctx()
    greedy = assemble_session(slots, pool, ctx, width=1)
    beam = assemble_session(slots, pool, ctx, width=2)
    assert [x.exercise.id for x in beam] == [2, 3]  # B then C -- the global optimum
    assert [x.exercise.id for x in greedy] == [1, 4]
    assert _replay_objective(beam, ctx) > _replay_objective(greedy, ctx)


def test_assemble_session_is_deterministic():
    slots, pool = _greedy_vs_beam_fixture()
    ctx = _ctx()
    first = assemble_session(slots, pool, ctx, width=2)
    second = assemble_session(slots, pool, ctx, width=2)
    assert [x.exercise.id for x in first] == [x.exercise.id for x in second]


def test_assemble_session_does_not_mutate_ctx():
    slots, pool = _greedy_vs_beam_fixture()
    ctx = _ctx()
    assemble_session(slots, pool, ctx, width=2)
    assert ctx.used_movement_slugs == set()
    assert ctx.used_unilateral_flags == []
    assert sum(ctx.muscle_coverage.values()) == 0


def test_empty_pool_slot_is_skipped():
    a = _Ex(1, "s1", "horizontal_push", ["a"])
    r1 = SlotRule(pattern="horizontal_push", priority="accessory", scheme="accessory", muscles=["a"])
    # No candidate matches this pattern -> pool empty for slot 2.
    r2 = SlotRule(pattern="vertical_pull", priority="accessory", scheme="accessory", muscles=["z"])
    result = assemble_session([r1, r2], [a], _ctx(), width=2)
    assert [x.exercise.id for x in result] == [1]  # slot 2 contributed nothing


def test_beam_prune_tie_break_prefers_lower_latest_exercise_id():
    # Slot 1: A and B tie exactly (same muscles, both fresh slugs), so width=2 carries
    # both forward as separate beams, beam-A processed before beam-B.
    # Slot 2: C shares A's slug and D shares B's slug, so variety flips which one each
    # beam prefers -- D is beam-A's best continuation, C is beam-B's best continuation --
    # and both continuations tie exactly (mf 1.0 + variety 1.0, on top of the equal
    # slot-1 score). C gets the lower id (5), D the higher id (100), and beam-A's (A, D)
    # is appended to next_beams *before* beam-B's (B, C). A stable sort on objective
    # alone would therefore keep (A, D) as the winner; only the explicit
    # `latest_exercise_id` ascending tie-break correctly promotes (B, C).
    a = _Ex(1, "sA", "push1", ["a"])
    b = _Ex(2, "sB", "push1", ["a"])
    c = _Ex(5, "sA", "pull1", ["m1"])
    d = _Ex(100, "sB", "pull1", ["m1"])
    r1 = SlotRule(pattern="push1", priority="accessory", scheme="accessory", muscles=["a"])
    r2 = SlotRule(pattern="pull1", priority="accessory", scheme="accessory", muscles=["m1"])
    result = assemble_session([r1, r2], [a, b, c, d], _ctx(), width=2)
    assert [x.exercise.id for x in result] == [2, 5]  # B then C -- lower latest id wins the tie
