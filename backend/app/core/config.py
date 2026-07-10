from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    PROJECT_NAME: str = "MyGym"
    API_V1_STR: str = "/api/v1"

    DATABASE_URL: str
    SQLALCHEMY_ECHO: bool = False

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Only send auth cookies over HTTPS; set to true in production.
    COOKIE_SECURE: bool = False

    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:5173"]


settings = Settings()  # type: ignore[call-arg]  # required fields are loaded from the environment/.env at runtime
