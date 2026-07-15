from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.api.v1 import auth_router, exercises_router, programs_router, training_environments_router, users_router
from app.core import AppException, get_logger, settings, setup_logging

setup_logging()
logger = get_logger(__name__)

app = FastAPI(title=settings.PROJECT_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    logger.warning(
        f"App exception: {exc.error_code} - {exc.message}",
        extra={
            "status_code": exc.status_code,
            "error_code": exc.error_code,
        },
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message, "error_code": exc.error_code},
    )


@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
    logger.warning(
        f"Validation error: {exc.errors()}",
        extra={
            "status_code": 422,
            "error_code": "VALIDATION_ERROR",
        },
    )
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Validation error",
            "error_code": "VALIDATION_ERROR",
            "errors": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        f"Unhandled exception: {type(exc).__name__}",
        exc_info=True,
        extra={
            "status_code": 500,
            "error_code": "INTERNAL_SERVER_ERROR",
        },
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An unexpected error occurred. Please contact support if the issue persists.",
            "error_code": "INTERNAL_SERVER_ERROR",
        },
    )


app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(users_router, prefix=settings.API_V1_STR)
app.include_router(training_environments_router, prefix=settings.API_V1_STR)
app.include_router(exercises_router, prefix=settings.API_V1_STR)
app.include_router(programs_router, prefix=settings.API_V1_STR)


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "MyGym API"}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
