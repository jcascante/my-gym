"""Runner: executes match -> draft for a single synthetic profile under old vs new
formula (plan Section 1.8, design decision #2).

"Old" = `config=None` (today's production default: `HeuristicTemplateScorer` +
`_range_fit` for matching, greedy per-slot selection for drafting).
"New" = an `EngineConfig` with `flags.use_constraint_scorer=True` (drives
`ConstraintTemplateScorer`) and `flags.use_beam_search=True` with
`assembly.beam_width=4` (per the proposal's own example).

This mirrors the service-level call pattern `api/v1/endpoints/programs.py` uses for
`/programs/match` and `/programs/draft`: build a `MatchInput`, rank templates, pick the
top-ranked (possibly all-infeasible best-effort) template, then draft it.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, cast

from app.core.constants import ENVIRONMENT_TYPE_EQUIPMENT_PRESETS
from app.models import Exercise, ProgramTemplate
from app.schemas.template import TemplateDefinition
from app.services.program.drafting import build_draft
from app.services.program.engine_config import AssemblyConfig, EngineConfig, EngineFlags
from app.services.program.matching import MatchInput, TemplateMatch, rank_templates
from app.services.program.selection import SelectionContext, template_is_feasible
from tests.harness.profiles import SyntheticProfile

# "New formula" EngineConfig (ground truth section of the task brief): both new-behavior
# flags on, beam_width=4 per the improvement proposal's own example.
NEW_CONFIG = EngineConfig(
    config_version="harness-new",
    flags=EngineFlags(use_constraint_scorer=True, use_beam_search=True),
    assembly=AssemblyConfig(beam_width=4),
)

# width=1 beam search must reproduce greedy selection exactly (Task 5); used by the
# width=1-equivalence sweep. Deliberately leaves use_constraint_scorer off so template
# ranking is unaffected -- only the assembly (drafting) strategy differs from `config=None`.
WIDTH_ONE_CONFIG = EngineConfig(
    config_version="harness-width1",
    flags=EngineFlags(use_beam_search=True),
    assembly=AssemblyConfig(beam_width=1),
)

# Per-slot exercise identity, in program order: enough to prove byte-for-byte
# reproducibility without serializing the full ORM object graph.
DraftFingerprint = tuple[tuple[str, int, int], ...]


@dataclass(frozen=True)
class FormulaResult:
    top_template_slug: str | None
    all_infeasible: bool
    elapsed_seconds: float
    draft_fingerprint: DraftFingerprint


@dataclass(frozen=True)
class ProfileResult:
    profile: SyntheticProfile
    old: FormulaResult
    new: FormulaResult


def equipment_for(profile: SyntheticProfile) -> list[str]:
    return ENVIRONMENT_TYPE_EQUIPMENT_PRESETS[profile.environment_type]


def build_match_input(profile: SyntheticProfile, equipment: list[str]) -> MatchInput:
    return MatchInput(
        fitness_focus=profile.fitness_focus,
        experience_level=profile.experience_level,
        days_per_week=profile.days_per_week,
        session_duration_min=profile.session_duration_min,
        environment_equipment=equipment,
    )


def build_selection_context(profile: SyntheticProfile, equipment: list[str]) -> SelectionContext:
    return SelectionContext(
        equipment=list(equipment),
        experience=profile.experience_level,
        injuries=list(profile.injuries),
        used_movement_slugs=set(),
    )


def required_inputs_for(definition: TemplateDefinition) -> dict[str, float]:
    """A fixed dummy value for every required input the template declares -- the actual
    magnitude doesn't affect template ranking or exercise selection, only `base_load`."""
    return {ri.key: 80.0 for ri in definition.required_inputs}


def draft_fingerprint(program: Any) -> DraftFingerprint:
    return tuple((w.key, ex.order, ex.exercise_id) for w in program.workouts for ex in w.exercises)


def build_definitions(templates: list[ProgramTemplate]) -> dict[int, TemplateDefinition]:
    return {t.id: TemplateDefinition.from_orm_template(t) for t in templates}


def build_feasibility(
    templates: list[ProgramTemplate],
    exercises: list[Exercise],
    definitions: dict[int, TemplateDefinition],
    equipment: list[str],
) -> dict[int, bool]:
    return {
        t.id: template_is_feasible(cast(list[object], definitions[t.id].split.sessions), exercises, equipment)
        for t in templates
    }


def rank(
    profile: SyntheticProfile,
    templates: list[ProgramTemplate],
    exercises: list[Exercise],
    definitions: dict[int, TemplateDefinition],
    feasibility: dict[int, bool],
    config: EngineConfig | None,
) -> list[TemplateMatch]:
    equipment = equipment_for(profile)
    inp = build_match_input(profile, equipment)
    return rank_templates(
        cast(list[Any], templates),
        inp,
        feasibility,
        definitions=definitions,
        all_exercises=cast(list[Any], exercises),
        config=config,
    )


def draft_for(
    profile: SyntheticProfile,
    template: ProgramTemplate,
    definition: TemplateDefinition,
    exercises: list[Exercise],
    config: EngineConfig | None,
) -> Any:
    equipment = equipment_for(profile)
    ctx = build_selection_context(profile, equipment)
    return build_draft(
        template,
        definition,
        ctx,
        exercises,
        user_id=1,
        environment_id=1,
        days_per_week=profile.days_per_week,
        duration_weeks=8,
        weight_unit="kg",
        required_inputs=required_inputs_for(definition),
        config=config,
    )


def run_formula(
    profile: SyntheticProfile,
    templates: list[ProgramTemplate],
    exercises: list[Exercise],
    definitions: dict[int, TemplateDefinition],
    feasibility: dict[int, bool],
    config: EngineConfig | None,
) -> FormulaResult:
    """Rank + draft a single profile under one formula (`config`), timing just the two
    engine calls (not fixture/DB setup, which the caller is responsible for doing once)."""
    start = time.perf_counter()
    ranked = rank(profile, templates, exercises, definitions, feasibility, config)
    top = ranked[0]
    template = next(t for t in templates if t.id == top.template_id)
    definition = definitions[top.template_id]
    program = draft_for(profile, template, definition, exercises, config)
    elapsed = time.perf_counter() - start
    return FormulaResult(
        top_template_slug=top.slug,
        all_infeasible=top.all_infeasible,
        elapsed_seconds=elapsed,
        draft_fingerprint=draft_fingerprint(program),
    )


def run_profile(
    profile: SyntheticProfile,
    templates: list[ProgramTemplate],
    exercises: list[Exercise],
    definitions: dict[int, TemplateDefinition] | None = None,
) -> ProfileResult:
    """Run a single synthetic profile through both the old and new formula."""
    defs = definitions if definitions is not None else build_definitions(templates)
    equipment = equipment_for(profile)
    feasibility = build_feasibility(templates, exercises, defs, equipment)
    old = run_formula(profile, templates, exercises, defs, feasibility, config=None)
    new = run_formula(profile, templates, exercises, defs, feasibility, config=NEW_CONFIG)
    return ProfileResult(profile=profile, old=old, new=new)
