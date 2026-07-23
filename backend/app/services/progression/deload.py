"""Readiness-based reactive deload trigger (Phase 4 plan, Task 4.3).

Reactively signals that the upcoming week should be a deload when logged
pre-workout readiness has been low often enough recently. This is independent of:
- the template's scheduled every-N-weeks deload
  (`app.services.program.progression.deload.apply_deload`), and
- the EWMA autoregulation controller (`app.services.progression.autoregulation`),
  which reacts to logged RPE rather than readiness.

Mirrors `autoregulation.compute_adjustment`'s shape: this module only computes
*whether* to trigger and *why* - `(bool, str)` - it does not touch `SetScheme`. The
caller (`derive_week` in `preview.py`) applies the resulting load reduction, the same
division of responsibility `_apply_autoregulation` already uses for the EWMA factor.

`readiness_logs` need not be pre-filtered or pre-sorted: the caller (typically a single
`UserWorkoutLog` query scoped to a user) may pass the user's full log history, and this
function does the date-window filtering and counting itself. `reference_date` is an
explicit parameter (not `date.today()` internally) so the trigger stays a pure function
of its inputs - same readiness history + same reference date must always produce the
same result (plan's determinism requirement), independent of wall-clock time.
"""

from datetime import date, datetime

from app.core.constants import (
    DELOAD_LOOKBACK_DAYS,
    DELOAD_MIN_LOW_READINESS_SESSIONS,
    DELOAD_READINESS_THRESHOLD,
)
from app.models import UserWorkoutLog

INSUFFICIENT_SIGNAL_REASON = "insufficient low-readiness signal"


def _session_date(log: UserWorkoutLog) -> date:
    session_date = log.session_date
    return session_date.date() if isinstance(session_date, datetime) else session_date


def compute_deload_trigger(
    readiness_logs: list[UserWorkoutLog],
    reference_date: date,
) -> tuple[bool, str]:
    """Determine whether readiness history warrants firing a deload.

    Returns `(triggered, reason)`. `triggered` is `True` when at least
    `DELOAD_MIN_LOW_READINESS_SESSIONS` logged sessions in the
    `DELOAD_LOOKBACK_DAYS`-day window ending on (and including) `reference_date` have
    `readiness <= DELOAD_READINESS_THRESHOLD`; `False` (with reason
    `INSUFFICIENT_SIGNAL_REASON`) otherwise, including when `readiness_logs` is empty.
    Logs with `readiness is None`, outside the lookback window, or dated after
    `reference_date` are ignored.
    """
    window_start = reference_date.toordinal() - DELOAD_LOOKBACK_DAYS
    low_readiness_dates = [
        _session_date(log)
        for log in readiness_logs
        if log.readiness is not None
        and log.readiness <= DELOAD_READINESS_THRESHOLD
        and window_start <= _session_date(log).toordinal() <= reference_date.toordinal()
    ]

    if len(low_readiness_dates) < DELOAD_MIN_LOW_READINESS_SESSIONS:
        return False, INSUFFICIENT_SIGNAL_REASON

    low_readiness_dates.sort()
    dates_str = ", ".join(d.isoformat() for d in low_readiness_dates)
    reason = (
        f"low_readiness_sessions={len(low_readiness_dates)} in last {DELOAD_LOOKBACK_DAYS}d "
        f"(threshold<={DELOAD_READINESS_THRESHOLD}, dates=[{dates_str}])"
    )
    return True, reason
