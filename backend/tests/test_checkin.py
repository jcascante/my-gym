import pytest

from app.models.checkin import CheckInStatus
from app.models.injury import InjuryPhase, InjuryRegion
from app.models.program import WorkoutProgram
from app.services.program.checkin import (
    AMBER_LEDGER_GUARD_ADJUSTMENT_PCT,
    AMBER_LOAD_ADJUSTMENT_PCT,
    AMBER_SELECTION_BIAS,
    apply_check_in,
)


def _program(constraints: dict | None = None) -> WorkoutProgram:
    return WorkoutProgram(
        id=1,
        user_id=1,
        template_id=1,
        environment_id=1,
        name="Test Program",
        focus=None,
        status="draft",
        duration_weeks=8,
        days_per_week=3,
        weight_unit="kg",
        constraints=constraints if constraints is not None else {},
    )


def test_green_check_in_resets_amber_streak():
    program = _program({"check_in_state": {"knee": {"amber_streak": 1, "excluded": False}}})

    effects = apply_check_in(program, InjuryRegion.KNEE, CheckInStatus.GREEN)

    assert effects.excluded is False
    assert program.constraints["check_in_state"]["knee"]["amber_streak"] == 0


def test_first_amber_applies_bias_and_load_adjustment_without_excluding():
    program = _program()

    effects = apply_check_in(program, InjuryRegion.KNEE, CheckInStatus.AMBER)

    assert effects.excluded is False
    assert effects.advisories == []
    assert program.constraints["region_score_penalties"]["knee"] == AMBER_SELECTION_BIAS
    assert program.constraints["check_in_load_adjustments"]["knee"] == {
        "load_pct": AMBER_LOAD_ADJUSTMENT_PCT,
        "ledger_guard_pct": AMBER_LEDGER_GUARD_ADJUSTMENT_PCT,
    }
    assert program.constraints["check_in_state"]["knee"]["amber_streak"] == 1


def test_second_consecutive_amber_triggers_regression_step_and_excludes():
    program = _program()
    apply_check_in(program, InjuryRegion.KNEE, CheckInStatus.AMBER)

    effects = apply_check_in(program, InjuryRegion.KNEE, CheckInStatus.AMBER)

    assert effects.excluded is True
    assert len(effects.advisories) == 1
    assert effects.advisories[0].code == "CHECK_IN_REGRESSION_STEP"
    assert effects.advisories[0].severity == "warning"
    assert program.constraints["check_in_state"]["knee"]["excluded"] is True


def test_red_immediately_excludes_and_drafts_injury_record():
    program = _program()

    effects = apply_check_in(program, InjuryRegion.SHOULDER, CheckInStatus.RED)

    assert effects.excluded is True
    assert effects.consult_recommended is True
    assert effects.draft_injury_record is not None
    assert effects.draft_injury_record.region == InjuryRegion.SHOULDER
    assert effects.draft_injury_record.phase == InjuryPhase.ACUTE
    assert effects.draft_injury_record.severity == 3
    assert effects.advisories[0].code == "CHECK_IN_RED_FLAG"
    assert effects.advisories[0].severity == "error"


def test_thoracic_amber_has_no_contraindication_tag_but_still_tracks_streak():
    """THORACIC has no Contraindication equivalent (task 3.3) - amber still counts
    toward the regression-step streak, it just can't contribute a score penalty."""
    program = _program()
    apply_check_in(program, InjuryRegion.THORACIC, CheckInStatus.AMBER)

    effects = apply_check_in(program, InjuryRegion.THORACIC, CheckInStatus.AMBER)

    assert effects.excluded is True
    assert "region_score_penalties" not in program.constraints


def test_regions_track_independent_state():
    program = _program()
    apply_check_in(program, InjuryRegion.KNEE, CheckInStatus.AMBER)
    apply_check_in(program, InjuryRegion.KNEE, CheckInStatus.AMBER)

    effects = apply_check_in(program, InjuryRegion.SHOULDER, CheckInStatus.AMBER)

    assert effects.excluded is False
    assert program.constraints["check_in_state"]["knee"]["excluded"] is True
    assert program.constraints["check_in_state"]["shoulder"]["excluded"] is False


@pytest.mark.asyncio
async def test_ctx_for_merges_check_in_excluded_regions_and_penalties(db_session, test_user, user_environment):
    from app.api.v1.endpoints.programs import _ctx_for

    await db_session.refresh(test_user, attribute_names=["profile"])
    program = WorkoutProgram(
        id=1,
        user_id=test_user.id,
        template_id=1,
        environment_id=user_environment.id,
        name="Test Program",
        focus=None,
        status="draft",
        duration_weeks=8,
        days_per_week=3,
        weight_unit="kg",
        constraints={
            "check_in_state": {"knee": {"amber_streak": 2, "excluded": True}},
            "region_score_penalties": {"lower_back": 1.0},
        },
    )

    ctx = await _ctx_for(db_session, test_user, user_environment, program=program)

    assert "knee" in ctx.injuries
    assert ctx.region_score_penalties == {"lower_back": 1.0}


@pytest.mark.asyncio
async def test_ctx_for_without_program_has_no_check_in_hazards(db_session, test_user, user_environment):
    from app.api.v1.endpoints.programs import _ctx_for

    await db_session.refresh(test_user, attribute_names=["profile"])
    ctx = await _ctx_for(db_session, test_user, user_environment)

    assert ctx.injuries == []
    assert ctx.region_score_penalties == {}
