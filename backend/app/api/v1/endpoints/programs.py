from typing import Any, cast

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_user
from app.core import (
    ProgramNotFoundError,
    ProgramTemplateNotFoundError,
    TrainingEnvironmentNotFoundError,
)
from app.core.database import get_db
from app.crud.exercise import get_exercises_by_ids, list_exercises
from app.crud.injury import list_injury_records
from app.crud.program import get_program, get_template, list_active_templates, save_program
from app.crud.training_environment import get_training_environment
from app.models import ProgramStatus, TrainingEnvironment, User, WorkoutProgram
from app.schemas.program_api import (
    Advisory,
    AlternativeOut,
    DraftRequest,
    FeedbackRequest,
    MatchRequest,
    ProgramPreviewOut,
    TemplateMatchOut,
    WorkoutPreviewOut,
)
from app.schemas.template import TemplateDefinition
from app.services.program.adaptation import FeedbackAction, alternatives_for_slot, apply_feedback
from app.services.program.drafting import build_draft
from app.services.program.engine_config import EngineConfig, get_engine_config
from app.services.program.matching import MatchInput, rank_templates
from app.services.program.preview import derive_week
from app.services.program.selection import SelectionContext, selection_hazards_from_injury_records, template_is_feasible
from app.services.program.style_override import apply_progression_style
from app.services.program.telemetry import record_event

router = APIRouter(prefix="/programs", tags=["programs"])


async def _ctx_for(
    db: AsyncSession,
    user: User,
    environment: TrainingEnvironment,
    *,
    movement_preferences: dict[str, float] | None = None,
    complementary_focus: bool = True,
) -> SelectionContext:
    profile = user.profile
    injury_records = await list_injury_records(db, user.id)
    injuries, injury_provocations = selection_hazards_from_injury_records(injury_records)
    experience = profile.experience_level.value if profile and profile.experience_level else "beginner"
    return SelectionContext(
        list(environment.equipment_tags),
        experience,
        injuries,
        set(),
        movement_preferences=movement_preferences or {},
        complementary_focus=complementary_focus,
        injury_provocations=injury_provocations,
    )


async def _preview_out(
    db: AsyncSession,
    program: WorkoutProgram,
    definition: TemplateDefinition,
    advisories: list[Advisory] | None = None,
) -> ProgramPreviewOut:
    exercise_ids = [ex.exercise_id for w in program.workouts for ex in w.exercises]
    exercises = await get_exercises_by_ids(db, exercise_ids) if exercise_ids else {}
    weeks = {
        w: [WorkoutPreviewOut(**day) for day in derive_week(program, definition, w, exercises)]
        for w in range(1, program.duration_weeks + 1)
    }
    return ProgramPreviewOut(
        program_id=program.id,
        name=program.name,
        status=program.status.value,
        duration_weeks=program.duration_weeks,
        weeks=weeks,
        advisories=advisories or [],
    )


@router.post("/match", response_model=list[TemplateMatchOut])
async def match(
    data: MatchRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    engine_config: EngineConfig = Depends(get_engine_config),
) -> list[TemplateMatchOut]:
    environment = await get_training_environment(db, user.id, data.environment_id)
    if environment is None:
        raise TrainingEnvironmentNotFoundError()
    templates = await list_active_templates(db)
    exercises = await list_exercises(db)
    feasibility = {}
    definitions = {}
    for t in templates:
        d = TemplateDefinition.from_orm_template(t)
        definitions[t.id] = d
        feasibility[t.id] = template_is_feasible(
            cast(list[object], d.split.sessions), exercises, environment.equipment_tags
        )
    profile = user.profile
    inp = MatchInput(
        data.fitness_focus,
        profile.experience_level.value if profile and profile.experience_level else "beginner",
        data.days_per_week,
        data.session_duration_min,
        list(environment.equipment_tags),
        movement_preferences=data.movement_preferences,
        complementary_focus=data.complementary_focus,
        progression_style=data.progression_style.value,
        goal_vector=profile.goal_weights if profile else None,
    )
    ranked = rank_templates(templates, inp, feasibility, definitions=definitions, all_exercises=exercises)
    for m in ranked:
        await record_event(
            db,
            user=user,
            event_type="match_score",
            payload={
                "template_id": m.template_id,
                "slug": m.slug,
                "fit_pct": m.fit_pct,
                "tier": m.tier,
                "factors": m.factors,
                "all_infeasible": m.all_infeasible,
            },
            config_version=engine_config.config_version,
        )
    return [
        TemplateMatchOut(
            **m.__dict__,
            required_inputs=[r.model_dump() for r in definitions[m.template_id].required_inputs],
        )
        for m in ranked
    ]


@router.post("/draft", response_model=ProgramPreviewOut, status_code=status.HTTP_201_CREATED)
async def draft(
    data: DraftRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    engine_config: EngineConfig = Depends(get_engine_config),
) -> ProgramPreviewOut:
    environment = await get_training_environment(db, user.id, data.environment_id)
    if environment is None:
        raise TrainingEnvironmentNotFoundError()
    template = await get_template(db, data.template_id)
    if template is None or not template.is_active:
        raise ProgramTemplateNotFoundError()
    definition = TemplateDefinition.from_orm_template(template)
    ctx = await _ctx_for(
        db,
        user,
        environment,
        movement_preferences=data.movement_preferences,
        complementary_focus=data.complementary_focus,
    )
    exercises = await list_exercises(db)
    telemetry_sink: list[dict[str, Any]] = []
    advisory_sink: list[Advisory] = []
    program = build_draft(
        template,
        definition,
        ctx,
        exercises,
        user_id=user.id,
        environment_id=environment.id,
        days_per_week=data.days_per_week,
        duration_weeks=data.duration_weeks,
        weight_unit=data.weight_unit,
        required_inputs=data.required_inputs,
        progression_style=data.progression_style.value,
        effort_method=data.effort_method.value if data.effort_method else None,
        variety_preference=data.variety_preference.value,
        engine_config_version=engine_config.config_version,
        telemetry_sink=telemetry_sink,
        advisory_sink=advisory_sink,
    )
    await save_program(db, program)
    for entry in telemetry_sink:
        await record_event(
            db,
            user=user,
            event_type="slot_selection",
            payload=entry,
            config_version=engine_config.config_version,
        )
    saved = await get_program(db, user.id, program.id)
    assert saved is not None
    preview_definition = apply_progression_style(definition, data.progression_style.value)
    return await _preview_out(db, saved, preview_definition, advisories=advisory_sink)


async def _load(db: AsyncSession, user: User, program_id: int) -> tuple[WorkoutProgram, TemplateDefinition]:
    program = await get_program(db, user.id, program_id)
    if program is None:
        raise ProgramNotFoundError()
    template = await get_template(db, program.template_id)
    definition = TemplateDefinition.from_orm_template(template)
    style = program.constraints.get("progression_style", "consistent")
    return program, apply_progression_style(definition, style)


@router.get("/{program_id}", response_model=ProgramPreviewOut)
async def get_one(
    program_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> ProgramPreviewOut:
    program, definition = await _load(db, user, program_id)
    return await _preview_out(db, program, definition)


@router.get("/{program_id}/preview", response_model=ProgramPreviewOut)
async def preview(
    program_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> ProgramPreviewOut:
    program, definition = await _load(db, user, program_id)
    return await _preview_out(db, program, definition)


@router.post("/{program_id}/feedback", response_model=ProgramPreviewOut)
async def feedback(
    program_id: int,
    data: FeedbackRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    engine_config: EngineConfig = Depends(get_engine_config),
) -> ProgramPreviewOut:
    program, definition = await _load(db, user, program_id)
    environment = await get_training_environment(db, user.id, program.environment_id)
    if environment is None:
        raise TrainingEnvironmentNotFoundError()
    ctx = await _ctx_for(
        db,
        user,
        environment,
        movement_preferences=program.constraints.get("movement_preferences", {}),
        complementary_focus=program.constraints.get("complementary_focus", True),
    )
    exercises = await list_exercises(db)
    apply_feedback(program, definition, FeedbackAction(**data.model_dump()), ctx, exercises)
    resulting_exercise_id = next(
        (ex.exercise_id for w in program.workouts for ex in w.exercises if ex.id == data.workout_exercise_id),
        None,
    )
    await save_program(db, program)
    await record_event(
        db,
        user=user,
        event_type="feedback_action",
        payload={
            "action": data.model_dump(),
            "workout_exercise_id": data.workout_exercise_id,
            "resulting_exercise_id": resulting_exercise_id,
        },
        config_version=engine_config.config_version,
    )
    saved = await get_program(db, user.id, program.id)
    assert saved is not None
    return await _preview_out(db, saved, definition)


@router.get("/{program_id}/slots/{we_id}/alternatives", response_model=list[AlternativeOut])
async def alternatives(
    program_id: int,
    we_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AlternativeOut]:
    program, definition = await _load(db, user, program_id)
    environment = await get_training_environment(db, user.id, program.environment_id)
    if environment is None:
        raise TrainingEnvironmentNotFoundError()
    ctx = await _ctx_for(
        db,
        user,
        environment,
        movement_preferences=program.constraints.get("movement_preferences", {}),
        complementary_focus=program.constraints.get("complementary_focus", True),
    )
    exercises = await list_exercises(db)
    alts = alternatives_for_slot(program, definition, we_id, ctx, exercises)
    return [AlternativeOut.model_validate(a) for a in alts]


@router.post("/{program_id}/accept", response_model=ProgramPreviewOut)
async def accept(
    program_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> ProgramPreviewOut:
    program, definition = await _load(db, user, program_id)
    program.status = ProgramStatus.ACTIVE
    await save_program(db, program)
    return await _preview_out(db, program, definition)
