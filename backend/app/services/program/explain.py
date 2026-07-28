"""Explanation API support (plan §3.6): re-derive "why this template / why this
exercise" on demand from current program + selection state, rather than from
telemetry. `EngineEvent` (services/program/telemetry.py) is consent-gated and has no
`program_id` column, so it cannot reliably answer "explain this specific program" -
recomputing fresh is both simpler and always available, matching the plan's own
"assembled from telemetry/stored breakdowns" alternate phrasing.
"""

from dataclasses import dataclass, field

from app.models.exercise import Exercise
from app.models.program import ProgramTemplate, WorkoutProgram
from app.schemas.template import SlotRule, TemplateDefinition
from app.services.program.drafting import _apply_pick_to_ctx, _group_contribution
from app.services.program.matching import MatchInput, TemplateMatch, rank_templates
from app.services.program.selection import HeuristicExerciseScorer, SelectionContext, _extract_features
from app.services.program.taxonomy import MUSCLE_GROUPS


def explain_template(
    template: ProgramTemplate,
    definition: TemplateDefinition,
    exercises: list[Exercise],
    match_input: MatchInput,
) -> TemplateMatch:
    """Re-score `template` in isolation via the same `rank_templates` path used at
    match time. The template is already the one the user picked, so feasibility is
    hardcoded true here - this endpoint explains a match that already happened, it
    doesn't re-decide feasibility."""
    matches = rank_templates(
        [template],
        match_input,
        {template.id: True},
        definitions={template.id: definition},
        all_exercises=exercises,
    )
    return matches[0]


@dataclass(frozen=True)
class LedgerContribution:
    group: str
    effective_sets: float


@dataclass(frozen=True)
class SlotExplanation:
    workout_exercise_id: int
    exercise_id: int
    exercise_name: str
    factors: dict[str, float] = field(default_factory=dict)
    score: float = 0.0
    ledger_contributions: list[LedgerContribution] = field(default_factory=list)
    safety_note: str | None = None


def _safety_note_for(exercise: Exercise, ctx: SelectionContext) -> str | None:
    """Three cheap, state-derived checks - no stored substitution provenance needed,
    since the checks the engine actually makes (hard region exclude, provocation
    overlap, amber score penalty) are all still visible on `ctx` at explain time."""
    contraindication_hits = set(exercise.contraindications) & set(ctx.injuries)
    if contraindication_hits:
        tags = ", ".join(sorted(contraindication_hits))
        return (
            f"This exercise carries contraindication tag(s) ({tags}) that are currently hard-excluded "
            "by your injury records or check-ins; it's likely a locked or manually-swapped slot."
        )
    active_provocations = {p.provocation for p in ctx.injury_provocations}
    provocation_hits = set(exercise.provocation_tags) & active_provocations
    if provocation_hits:
        tags = ", ".join(sorted(provocation_hits))
        return (
            f"This exercise shares provocation tag(s) ({tags}) with an active injury record; "
            "safety substitution may replace it if that mechanism is enabled."
        )
    penalized = set(exercise.contraindications) & set(ctx.region_score_penalties)
    if penalized:
        tags = ", ".join(sorted(penalized))
        return f"This exercise carries contraindication tag(s) ({tags}) with an active amber check-in penalty."
    return None


def explain_slot(
    program: WorkoutProgram,
    workout_exercise_id: int,
    ctx: SelectionContext,
    exercises: list[Exercise],
) -> SlotExplanation | None:
    """Replay every pick before `workout_exercise_id` (in program/workout/slot order)
    into `ctx`, so the target slot's features reflect the same accumulated
    variety/coverage/ledger state the original greedy selection saw - not an empty
    context. Mirrors `drafting.py::build_draft`'s own sequential accumulation."""
    exercise_by_id = {ex.id: ex for ex in exercises}
    target: tuple[Exercise, SlotRule, int] | None = None
    matched_we_id: int | None = None
    for workout in program.workouts:
        for we in workout.exercises:
            if we.id == workout_exercise_id:
                exercise = exercise_by_id.get(we.exercise_id)
                if exercise is not None:
                    target = (exercise, SlotRule(**we.fills_rule), we.sets)
                    matched_we_id = we.id
                break
            exercise = exercise_by_id.get(we.exercise_id)
            if exercise is not None:
                _apply_pick_to_ctx(
                    ctx, exercise, sets=we.sets, is_hard=(we.scheme_key == "main"), workout_key=workout.key
                )
        if target is not None:
            break

    if target is None or matched_we_id is None:
        return None
    exercise, rule, sets = target

    features = _extract_features(exercise, rule, ctx)
    score = HeuristicExerciseScorer(ctx.weights).score(features)

    contributions = [
        LedgerContribution(group=group, effective_sets=contribution)
        for group in MUSCLE_GROUPS
        if (contribution := _group_contribution(exercise, group, sets)) > 0
    ]

    return SlotExplanation(
        workout_exercise_id=matched_we_id,
        exercise_id=exercise.id,
        exercise_name=exercise.name,
        factors=features,
        score=round(score, 4),
        ledger_contributions=contributions,
        safety_note=_safety_note_for(exercise, ctx),
    )
