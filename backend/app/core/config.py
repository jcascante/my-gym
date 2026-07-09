from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "MyGym"
    API_V1_STR: str = "/api/v1"

    DATABASE_URL: str
    SQLALCHEMY_ECHO: bool = False

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
