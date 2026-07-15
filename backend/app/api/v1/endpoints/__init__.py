from .auth import router as auth_router
from .programs import router as programs_router
from .training_environments import router as training_environments_router
from .users import router as users_router

__all__ = ["auth_router", "users_router", "training_environments_router", "programs_router"]
