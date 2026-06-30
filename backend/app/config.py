"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central configuration — reads from .env or environment."""

    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/lifesaver"
    JWT_SECRET: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 1440  # 24 hours
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"
    ANTHROPIC_API_KEY: str = ""
    ALLOW_MOCK_FALLBACK: bool = True

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
