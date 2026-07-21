# backend/tests/test_selection.py
from datetime import date

from app.models.injury import InjuryCondition, InjuryPhase, InjuryRecord, InjuryRegion, InjurySource
from app.schemas.template import SlotRule
from app.services.program.selection import SelectionContext, select_for_slot, selection_hazards_from_injury_records


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


def test_movement_preference_biases_selection_without_excluding_others():
    from app.schemas.template import SlotRule
    from app.services.program.selection import SelectionContext, select_for_slot

    barbell_ex = _Ex(1, "bb-row", "row", "horizontal_pull", "upper_body", ["lats"], ["barbell"], "intermediate", [])
    kb_ex = _Ex(2, "kb-row", "kb_row", "horizontal_pull", "upper_body", ["lats"], ["kettlebell"], "intermediate", [])
    rule = SlotRule(pattern="horizontal_pull", priority="accessory", scheme="accessory")
    ctx = SelectionContext(
        ["barbell", "kettlebell"],
        "intermediate",
        [],
        set(),
        movement_preferences={"kettlebell": 2.0, "barbell": 0.2},
    )
    chosen = select_for_slot([barbell_ex, kb_ex], rule, ctx, None, set())
    assert chosen.id == 2  # kettlebell strongly preferred


def _injury(
    region: str,
    *,
    phase: str = "rehabilitating",
    provocations: list[str] | None = None,
) -> InjuryRecord:
    return InjuryRecord(
        user_id=1,
        region=InjuryRegion(region),
        condition=InjuryCondition.TENDINOPATHY,
        phase=InjuryPhase(phase),
        provocations=provocations or [],
        severity=2,
        reported_at=date(2026, 1, 1),
        source=InjurySource.USER_REPORTED,
    )


def test_selection_hazards_maps_region_to_contraindication_tag():
    injuries, provocations = selection_hazards_from_injury_records([_injury("knee", provocations=[])])
    assert injuries == ["knee"]
    assert provocations == []


def test_selection_hazards_maps_region_synonyms():
    injuries, _ = selection_hazards_from_injury_records([_injury("cervical"), _injury("lumbar"), _injury("ankle_foot")])
    assert set(injuries) == {"neck", "lower_back", "ankle"}


def test_selection_hazards_thoracic_has_no_contraindication_tag():
    injuries, _ = selection_hazards_from_injury_records([_injury("thoracic")])
    assert injuries == []


def test_selection_hazards_cleared_record_contributes_nothing():
    injuries, provocations = selection_hazards_from_injury_records(
        [_injury("knee", phase="cleared", provocations=["deep_knee_flexion"])]
    )
    assert injuries == []
    assert provocations == []


def test_selection_hazards_tracks_rehabilitating_flag_per_provocation():
    injuries, provocations = selection_hazards_from_injury_records(
        [
            _injury("knee", phase="rehabilitating", provocations=["deep_knee_flexion"]),
            _injury("shoulder", phase="acute", provocations=["overhead"]),
        ]
    )
    assert injuries == ["knee", "shoulder"]
    by_provocation = {p.provocation: p.is_rehabilitating for p in provocations}
    assert by_provocation == {"deep_knee_flexion": True, "overhead": False}


def test_movement_preference_never_empties_a_slot():
    from app.schemas.template import SlotRule
    from app.services.program.selection import SelectionContext, select_for_slot

    only_option = _Ex(1, "bb-row", "row", "horizontal_pull", "upper_body", ["lats"], ["barbell"], "intermediate", [])
    rule = SlotRule(pattern="horizontal_pull", priority="accessory", scheme="accessory")
    ctx = SelectionContext(["barbell"], "intermediate", [], set(), movement_preferences={"barbell": 0.0})
    chosen = select_for_slot([only_option], rule, ctx, None, set())
    assert chosen.id == 1


def test_ranked_pool_breaks_score_ties_on_exercise_id_ascending():
    from app.schemas.template import SlotRule
    from app.services.program.selection import SelectionContext, ranked_pool_for_slot

    # Two exercises that score identically; the lower id must win the tie regardless
    # of input order (previously relied on Python's stable sort preserving input order).
    hi = _Ex(5, "row-a", "row", "horizontal_pull", "upper_body", ["lats"], [], "intermediate", [])
    lo = _Ex(3, "row-b", "row", "horizontal_pull", "upper_body", ["lats"], [], "intermediate", [])
    rule = SlotRule(pattern="horizontal_pull", priority="accessory", scheme="accessory")
    ctx = SelectionContext(["barbell"], "intermediate", [], set())
    ranked = ranked_pool_for_slot([hi, lo], rule, ctx, set())
    assert [ex.id for ex in ranked] == [3, 5]


def test_ranked_pool_for_slot_returns_descending_order():
    from app.schemas.template import SlotRule
    from app.services.program.selection import SelectionContext, ranked_pool_for_slot

    preferred = _Ex(
        1, "kb-row", "kb_row", "horizontal_pull", "upper_body", ["lats"], ["kettlebell"], "intermediate", []
    )
    other = _Ex(2, "bb-row", "row", "horizontal_pull", "upper_body", ["lats"], ["barbell"], "intermediate", [])
    rule = SlotRule(pattern="horizontal_pull", priority="accessory", scheme="accessory")
    ctx = SelectionContext(
        ["barbell", "kettlebell"], "intermediate", [], set(), movement_preferences={"kettlebell": 2.0}
    )
    ranked = ranked_pool_for_slot([other, preferred], rule, ctx, set())
    assert [ex.id for ex in ranked] == [1, 2]
