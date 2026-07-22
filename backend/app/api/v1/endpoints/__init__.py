from .auth import router as auth_router
from .exercises import router as exercises_router
from .injuries import router as injuries_router
from .logging import router as logging_router
from .programs import router as programs_router
from .templates import router as templates_router
from .training_environments import router as training_environments_router
from .users import router as users_router

__all__ = [
    "auth_router",
    "users_router",
    "training_environments_router",
    "exercises_router",
    "templates_router",
    "programs_router",
    "injuries_router",
    "logging_router",
]
