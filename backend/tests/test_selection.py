# backend/tests/test_selection.py
from app.schemas.template import SlotRule
from app.services.program.selection import SelectionContext, select_for_slot


class _Ex:
    def __init__(self, id, slug, mslug, pattern, region, muscles, equip, diff, contra):
        self.id, self.slug, self.movement_slug = id, slug, mslug
        self.movement_pattern = type("P", (), {"value": pattern})
        self.body_region = type("R", (), {"value": region})
        self.primary_muscles, self.equipment_tags = muscles, equip
        self.difficulty_level = type("D", (), {"value": diff})
        self.contraindications = contra


def _ctx(equip, injuries=()):
    return SelectionContext(list(equip), "intermediate", list(injuries), set())


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
