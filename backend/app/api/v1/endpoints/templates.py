from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_user
from app.core.database import get_db
from app.crud.program import list_active_templates
from app.models import User
from app.schemas.template import TemplateOut

router = APIRouter(prefix="/templates", tags=["templates"])


@router.get("", response_model=dict[str, list[TemplateOut]])
async def list_templates(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, list[TemplateOut]]:
    """List all available program templates.

    Requires authentication. Returns only active templates.
    """
    templates = await list_active_templates(db)
    return {
        "templates": [
            TemplateOut(
                slug=t.slug,
                name=t.name,
                description=t.description,
                goals=t.goals,
                experience_levels=t.experience_levels,
                days_per_week_min=t.days_per_week_min,
                days_per_week_max=t.days_per_week_max,
                session_duration_min=t.session_duration_min,
                session_duration_max=t.session_duration_max,
                split=t.split,
                progression_ref=t.progression_ref,
                required_inputs=t.required_inputs,
            )
            for t in templates
        ]
    }
