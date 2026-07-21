"""Ramp-rate guard (plan §3.5, proposal §5.2/§5.4): caps week-over-week load/set-count
growth by population, wrapping `apply_deload(model.resolve(...))` in `derive_week` -
same shape as `deload.py`.

Unlike drafting.py's Phase 2/3 post-draft passes, this is NOT gated behind an
`EngineFlags` bool: `derive_week`/`apply_deload` have never been flag-gated (deload has
always run unconditionally, controlled only by whether `every` is set), and the plan
describes ramp_guard as extending that exact same always-on wrapper. In practice this
cap rarely binds for a normal progression (a typical linear-load week-over-week
increase is well under 20%) - it's a ceiling against pathological jumps, not a routine
brake.

Populations, first match wins:
- "post_amber": this slot's exercise carries a contraindication tag with an active
  amber adjustment (task 3.4's `check_in_load_adjustments`) - the tightest cap
  (+2.5%/week load, +10%/week sets).
- "beginner": the program's stored `experience_level` is "beginner" - a looser cap
  (+20%/week, both load and sets).
- everything else ("unrestricted"): no cap - the progression model's own formula
  governs, same as before this task.

"Returning after 2 weeks" (proposal: restart at 70%) is deliberately not implemented -
it needs to know when the user last actually trained, which needs workout-session
logging (`UserWorkoutLog`, Phase 4.1) that doesn't exist in this codebase yet (the same
infrastructure gap flagged for task 3.4's check-in). Revisit once that lands.
"""

from app.services.program.progression.base import SetScheme

RAMP_CAPS: dict[str, dict[str, float]] = {
    "post_amber": {"load_pct": 0.025, "sets_pct": 0.10},
    "beginner": {"load_pct": 0.20, "sets_pct": 0.20},
}


def population_for(
    exercise_contraindications: list[str],
    check_in_load_adjustments: dict[str, object],
    experience: str,
) -> str:
    if set(exercise_contraindications) & set(check_in_load_adjustments):
        return "post_amber"
    if experience == "beginner":
        return "beginner"
    return "unrestricted"


def apply_ramp_guard(scheme: SetScheme, prior_scheme: SetScheme | None, population: str) -> SetScheme:
    caps = RAMP_CAPS.get(population)
    if caps is None or prior_scheme is None:
        return scheme

    capped_load = scheme.load
    if scheme.load is not None and prior_scheme.load is not None and prior_scheme.load > 0:
        max_load = round(prior_scheme.load * (1 + caps["load_pct"]), 2)
        capped_load = min(scheme.load, max_load)

    max_sets = max(int(prior_scheme.sets * (1 + caps["sets_pct"])), prior_scheme.sets)
    capped_sets = min(scheme.sets, max_sets)

    if capped_load == scheme.load and capped_sets == scheme.sets:
        return scheme
    return SetScheme(
        sets=capped_sets,
        reps=scheme.reps,
        load=capped_load,
        rest_seconds=scheme.rest_seconds,
        note=scheme.note or "ramp_capped",
    )
