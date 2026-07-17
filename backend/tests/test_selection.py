# backend/tests/test_selection.py
from app.schemas.template import SlotRule
from app.services.program.selection import SelectionContext, select_for_slot


class _Ex:
    def __init__(
        self,
        id,
        slug,
        mslug,
        pattern,
        region,
        muscles,
        equip,
        diff,
        contra,
        is_compound=True,
        is_unilateral=False,
    ):
        self.id, self.slug, self.movement_slug = id, slug, mslug
        self.movement_pattern = type("P", (), {"value": pattern})
        self.body_region = type("R", (), {"value": region})
        self.primary_muscles, self.equipment_tags = muscles, equip
        self.difficulty_level = type("D", (), {"value": diff})
        self.contraindications = contra
        self.is_compound = is_compound
        self.is_unilateral = is_unilateral


def _ctx(equip, injuries=(), used_unilateral_flags=None):
    return SelectionContext(list(equip), "intermediate", list(injuries), set(), used_unilateral_flags or [])


def test_filters_by_equipment_and_injury():
    bench = _Ex(
        1, "bb-bench", "bench", "horizontal_push", "upper_body", ["chest"], ["barbell"], "intermediate", ["shoulder"]
    )
    pushup = _Ex(2, "pushup", "pushup", "horizontal_push", "upper_body", ["chest"], [], "beginner", [])
    rule = SlotRule(pattern="horizontal_push", priority="primary", scheme="main")
    # shoulder injury excludes bench; no barbell anyway -> pushup chosen
    chosen = select_for_slot([bench, pushup], rule, _ctx([], injuries=["shoulder"]), None, set())
    assert chosen.id == 2


def test_locked_overrides_selection():
    a = _Ex(1, "a", "a", "squat", "lower_body", ["quads"], [], "beginner", [])
    b = _Ex(2, "b", "b", "squat", "lower_body", ["quads"], [], "beginner", [])
    rule = SlotRule(pattern="squat", priority="primary", scheme="main")
    assert select_for_slot([a, b], rule, _ctx([]), locked_exercise_id=2, excluded_ids=set()).id == 2


def test_primary_slot_prefers_compound_exercise():
    compound = _Ex(1, "squat", "squat", "squat", "lower_body", ["quads"], [], "intermediate", [], is_compound=True)
    isolation = _Ex(
        2, "leg-ext", "leg_ext", "squat", "lower_body", ["quads"], [], "intermediate", [], is_compound=False
    )
    rule = SlotRule(pattern="squat", priority="primary", scheme="main")
    chosen = select_for_slot([isolation, compound], rule, _ctx([]), None, set())
    assert chosen.id == 1


def test_accessory_slot_prefers_isolation_exercise():
    compound = _Ex(1, "squat", "squat", "squat", "lower_body", ["quads"], [], "intermediate", [], is_compound=True)
    isolation = _Ex(
        2, "leg-ext", "leg_ext", "squat", "lower_body", ["quads"], [], "intermediate", [], is_compound=False
    )
    rule = SlotRule(pattern="squat", priority="accessory", scheme="accessory")
    chosen = select_for_slot([compound, isolation], rule, _ctx([]), None, set())
    assert chosen.id == 2


def test_penalizes_repeating_unilateral_mode_back_to_back():
    unilateral = _Ex(
        1,
        "split-squat",
        "split_squat",
        "lunge",
        "lower_body",
        ["quads"],
        [],
        "intermediate",
        [],
        is_unilateral=True,
    )
    bilateral = _Ex(2, "squat", "squat", "lunge", "lower_body", ["quads"], [], "intermediate", [], is_unilateral=False)
    rule = SlotRule(pattern="lunge", priority="accessory", scheme="accessory")
    # last pick in the session was already unilateral -> bilateral should win the tie
    chosen = select_for_slot([unilateral, bilateral], rule, _ctx([], used_unilateral_flags=[True]), None, set())
    assert chosen.id == 2
