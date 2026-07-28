from .endpoints import (
    auth_router,
    exercises_router,
    injuries_router,
    programs_router,
    templates_router,
    training_environments_router,
    users_router,
)

__all__ = [
    "auth_router",
    "users_router",
    "training_environments_router",
    "exercises_router",
    "templates_router",
    "programs_router",
    "injuries_router",
]
