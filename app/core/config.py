from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    environment: str = "development"
    database_url_async: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"

    # Supabase Auth. El backend no emite tokens: solo verifica los de Supabase.
    supabase_url: str = ""
    supabase_jwt_secret: str | None = None  # Solo para proyectos legados con HS256.
    supabase_jwt_audience: str = "authenticated"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
