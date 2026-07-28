# backend/tests/test_assembly.py
"""Beam-search session assembly (plan §1.5/§2.5)."""
from dataclasses import replace

import pytest

from app.schemas.template import SchemeDef, SlotRule
from app.services.program.assembly import _ledger_adjustment, assemble_session
from app.services.program.engine_config import AssemblyConfig, EngineConfig
from app.services.program.ledger import LedgerAccumulator, LedgerPick
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
        secondary_muscles=(),
    ):
        self.id, self.movement_slug = id, mslug
        self.movement_pattern = type("P", (), {"value": pattern})
        self.body_region = type("R", (), {"value": "upper_body"})
        self.primary_muscles, self.equipment_tags = list(muscles), list(equip)
        self.secondary_muscles = list(secondary_muscles)
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


# --- Ledger term (plan §2.5) ------------------------------------------------------

_SCHEMES = {"accessory": SchemeDef(sets=3, reps_min=8, reps_max=12, rest_seconds=60)}


def _greedy_vs_beam_fixture_real_muscles():
    """Same shape/tie structure as `_greedy_vs_beam_fixture`, but with real `Muscle`
    enum values (not the fake "a"/"b"/"c" labels) -- needed for any test that exercises
    the ledger path, since `LedgerAccumulator.apply` looks up `Muscle(m)` for real."""
    a = _Ex(1, "shared", "horizontal_push", ["chest", "triceps"])
    b = _Ex(2, "b_only", "horizontal_push", ["chest"])
    c = _Ex(3, "shared", "horizontal_pull", ["lats", "biceps", "traps"])
    d = _Ex(4, "d_only", "horizontal_pull", ["lats"])
    r1 = SlotRule(pattern="horizontal_push", priority="accessory", scheme="accessory", muscles=["chest", "triceps"])
    r2 = SlotRule(
        pattern="horizontal_pull", priority="accessory", scheme="accessory", muscles=["lats", "biceps", "traps"]
    )
    return [r1, r2], [a, b, c, d]


def test_lambda_zero_config_matches_config_none_byte_identical():
    """The byte-identical invariant: a real EngineConfig at today's default lambdas
    (0.0/0.0) must produce EXACTLY the same assignments as config=None, proving
    "lambda=0" -- not literally `config is None` -- is what keeps existing callers inert."""
    slots, pool = _greedy_vs_beam_fixture_real_muscles()
    ctx = _ctx()
    baseline = assemble_session(slots, pool, ctx, width=2)
    config = EngineConfig(config_version="x")  # AssemblyConfig defaults: lambda_v=lambda_f=0.0
    with_inert_config = assemble_session(
        slots, pool, ctx, width=2, config=config, schemes=_SCHEMES, workout_key="day_1"
    )
    assert [x.exercise.id for x in with_inert_config] == [x.exercise.id for x in baseline]
    assert [x.order for x in with_inert_config] == [x.order for x in baseline]


def test_ledger_term_changes_winning_candidate():
    """A and B tie exactly on slot_score (both hit "chest" for muscle_fit=1.0, distinct
    fresh slugs for variety=1.0). B additionally has "quads" as a primary muscle -- with
    an empty starting ledger, quads is far below intermediate MEV (8 sets), so crediting
    it lowers band_distance_sum more than A's pick (which only touches "chest", credited
    identically by both). With lambda_v=0 this is a pure tie and the lower-id candidate
    (A, id=1) wins the tie-break; with lambda_v>0, B (id=2, no better slot_score) must
    win instead -- proving the ledger term actually reorders the winner, not merely
    computes-and-ignores."""
    a = _Ex(1, "sA", "horizontal_push", ["chest"])
    b = _Ex(2, "sB", "horizontal_push", ["chest", "quads"])
    rule = SlotRule(pattern="horizontal_push", priority="accessory", scheme="accessory", muscles=["chest"])
    ctx = _ctx()

    baseline_config = EngineConfig(config_version="x")
    baseline = assemble_session(
        [rule], [a, b], ctx, width=2, config=baseline_config, schemes=_SCHEMES, workout_key="day_1"
    )
    assert [x.exercise.id for x in baseline] == [1]  # tie -> lower id wins

    lambda_config = EngineConfig(config_version="x", assembly=AssemblyConfig(lambda_v=1.0))
    with_ledger = assemble_session(
        [rule], [a, b], ctx, width=2, config=lambda_config, schemes=_SCHEMES, workout_key="day_1"
    )
    assert [x.exercise.id for x in with_ledger] == [2]  # ledger term flips the winner to B


def test_ledger_term_is_skipped_entirely_when_config_is_none():
    """`ctx.ledger` is never touched (not even seed-cloned) on the config=None path --
    a stronger check than "produces the same output", verifying the code path really is
    skipped rather than computed-and-discarded."""
    slots, pool = _greedy_vs_beam_fixture()
    ctx = _ctx()
    before = ctx.ledger.snapshot()
    assemble_session(slots, pool, ctx, width=2)
    assert ctx.ledger.snapshot() == before


def test_freq_bonus_fires_once_not_per_subsequent_slot_touching_group():
    """The freq_bonus's defining property: only the slot whose pick pushes a group from
    1 to 2 distinct workout-days gets credited, not every later slot in the same session
    that also happens to touch that already-2-day group."""
    config = EngineConfig(config_version="x", assembly=AssemblyConfig(lambda_f=1.0))
    rule = SlotRule(pattern="p", priority="accessory", scheme="accessory")
    ex1 = _Ex(1, "s1", "p", ["chest"])
    ex2 = _Ex(2, "s2", "p", ["chest"])

    ledger = LedgerAccumulator()
    seed_ex = _Ex(99, "seed", "p", ["chest"])
    # Seed one prior day's pick: chest starts at frequency_days=1, already >= MEV (8),
    # so the bonus's third condition is trivially satisfied for both slots below.
    ledger.apply(LedgerPick(exercise_id=99, workout_key="day_1", sets=10, is_hard=True), seed_ex)

    term1, ledger_after_1 = _ledger_adjustment(config, "intermediate", ledger, rule, ex1, _SCHEMES, "day_2")
    assert term1 == pytest.approx(1.0)  # chest: day_1 + day_2 -> frequency_days 1 -> 2, bonus fires
    assert ledger_after_1.snapshot()["chest"].frequency_days == 2

    term2, _ = _ledger_adjustment(config, "intermediate", ledger_after_1, rule, ex2, _SCHEMES, "day_2")
    assert term2 == pytest.approx(0.0)  # same day_2: frequency_days was already 2, no bonus
