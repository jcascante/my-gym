"""Traffic-light check-in state machine (plan §3.4, proposal §5.3).

Pure function operating on `WorkoutProgram.constraints` JSON - same idiom as
`adaptation.py::apply_feedback` (read the dict, mutate a plain copy, reassign the
whole `constraints` attribute so SQLAlchemy's JSON change-tracking picks it up).

How each proposal §5.3 effect is wired:
- Region exclusion (2 consecutive ambers, or any red) reuses the region/contraindication
  hard-exclude `_apply_safety_substitution`/`_passes_filters` already understand
  (`SelectionContext.injuries`) - the caller is responsible for adding
  `constraints["check_in_state"][region]["excluded"]` regions into `ctx.injuries` the
  same way it already does for `InjuryRecord`-derived tags, and for immediately
  reselecting any already-drafted slot that now fails that filter (this program's
  workouts are the *only* copy of "which exercise fills this slot" - there's no
  separate per-week assignment - so "removed for the mesocycle" has to mutate them now,
  not just bias some future draft).
- Amber's -1.0 selection-score bias is stored in `constraints["region_score_penalties"]`
  and consumed by `SelectionContext.region_score_penalties` (selection.py) - a soft
  nudge, not an exclusion, matching the proposal's distinction between amber and red.
- Amber's load-cut and ledger-guard percentages are computed and stored
  (`constraints["check_in_load_adjustments"]`) but not resolved into an actual
  load/ledger number here - that's `ramp_guard.py`'s job (plan §3.5: "weekly load caps
  ... applied in derive_week"), which is expected to read this key.
- Red also drafts an (unsaved) `InjuryRecordCreate` for the user to confirm via the
  existing `POST /users/me/injuries`, and a consult-message `Advisory`. Never persisted
  here - same "draft, don't mutate without confirmation" principle as tasks 3.1/3.2.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import TypedDict

from app.models.checkin import CheckInStatus
from app.models.injury import InjuryCondition, InjuryPhase, InjuryRegion, InjurySource
from app.models.program import WorkoutProgram
from app.schemas.injury import InjuryRecordCreate
from app.schemas.program_api import Advisory
from app.services.program.selection import contraindication_tag_for_region


class _RegionState(TypedDict):
    amber_streak: int
    excluded: bool


AMBER_SELECTION_BIAS = 1.0
AMBER_LOAD_ADJUSTMENT_PCT = -0.15  # midpoint of proposal's -10-20%
AMBER_LEDGER_GUARD_ADJUSTMENT_PCT = -0.30
AMBER_STREAK_FOR_REGRESSION_STEP = 2


@dataclass(frozen=True)
class CheckInEffects:
    excluded: bool
    consult_recommended: bool
    draft_injury_record: InjuryRecordCreate | None
    advisories: list[Advisory] = field(default_factory=list)


def _region_label(region: InjuryRegion) -> str:
    return region.value.replace("_", " ")


def apply_check_in(program: WorkoutProgram, region: InjuryRegion, status: CheckInStatus) -> CheckInEffects:
    constraints = dict(program.constraints)
    check_in_state: dict[str, _RegionState] = dict(constraints.get("check_in_state", {}))
    region_state: _RegionState = check_in_state.get(region.value) or _RegionState(amber_streak=0, excluded=False)

    advisories: list[Advisory] = []
    draft_injury_record: InjuryRecordCreate | None = None
    consult_recommended = False

    if status == CheckInStatus.GREEN:
        region_state["amber_streak"] = 0

    elif status == CheckInStatus.AMBER:
        region_state["amber_streak"] += 1

        tag = contraindication_tag_for_region(region)
        if tag is not None:
            penalties = dict(constraints.get("region_score_penalties", {}))
            penalties[tag] = AMBER_SELECTION_BIAS
            constraints["region_score_penalties"] = penalties

            load_adjustments = dict(constraints.get("check_in_load_adjustments", {}))
            load_adjustments[tag] = {
                "load_pct": AMBER_LOAD_ADJUSTMENT_PCT,
                "ledger_guard_pct": AMBER_LEDGER_GUARD_ADJUSTMENT_PCT,
            }
            constraints["check_in_load_adjustments"] = load_adjustments

        if region_state["amber_streak"] >= AMBER_STREAK_FOR_REGRESSION_STEP:
            region_state["excluded"] = True
            advisories.append(
                Advisory(
                    code="CHECK_IN_REGRESSION_STEP",
                    severity="warning",
                    subject=region.value,
                    message=(
                        f"Two consecutive amber check-ins for your {_region_label(region)} - stepping future "
                        "sessions down to a gentler variant for this region."
                    ),
                )
            )

    else:  # RED
        region_state["excluded"] = True
        consult_recommended = True
        draft_injury_record = InjuryRecordCreate(
            region=region,
            condition=InjuryCondition.ACUTE_PAIN,
            phase=InjuryPhase.ACUTE,
            provocations=[],
            severity=3,
            reported_at=date.today(),
            source=InjurySource.USER_REPORTED,
        )
        advisories.append(
            Advisory(
                code="CHECK_IN_RED_FLAG",
                severity="error",
                subject=region.value,
                message=(
                    f"Red check-in for your {_region_label(region)} - we've removed exercises that load "
                    "this region for the rest of this program. Please consider consulting a medical "
                    "professional, and confirm the drafted injury record below if it looks right."
                ),
            )
        )

    check_in_state[region.value] = region_state
    constraints["check_in_state"] = check_in_state
    program.constraints = constraints

    return CheckInEffects(
        excluded=region_state["excluded"],
        consult_recommended=consult_recommended,
        draft_injury_record=draft_injury_record,
        advisories=advisories,
    )
