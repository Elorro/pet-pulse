from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    environment: str = "development"
    database_url_async: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"

    # Supabase Auth. El backend no emite tokens: solo verifica los de Supabase.
    supabase_url: str = ""
    supabase_anon_key: str = Field(
        default="",
        validation_alias=AliasChoices("SUPABASE_ANON_KEY", "SUPABASE_KEY"),
        description="Clave pública (anon/publishable) para el SDK.",
    )
    supabase_service_role_key: str = Field(
        default="",
        validation_alias=AliasChoices("SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_SECRET_KEY"),
    )
    supabase_media_bucket: str = "post-media"
    supabase_jwt_secret: str | None = None  # Solo para proyectos legados con HS256.
    supabase_jwt_audience: str = "authenticated"

    # Orígenes CORS separados por comas (p. ej. el dominio de Vercel del frontend).
    cors_origins: str = "http://localhost,http://localhost:3000,http://localhost:8080"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
