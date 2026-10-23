from functools import lru_cache
from urllib.parse import urlparse

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    environment: str = "development"
    database_url_async: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"

    # Supabase Auth. El backend no emite tokens: solo verifica los de Supabase.
    supabase_url: str = ""
    # Destino al que Supabase redirige tras verificar el email. En desarrollo
    # puede omitirse para conservar el Site URL local del proyecto Supabase.
    auth_email_redirect_to: str | None = None
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

    @field_validator("auth_email_redirect_to")
    @classmethod
    def validate_auth_email_redirect_to(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        value = value.strip()
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("AUTH_EMAIL_REDIRECT_TO debe ser una URL absoluta http(s)")
        return value.rstrip("/")

    @model_validator(mode="after")
    def validate_production_auth_redirect(self) -> "Settings":
        if self.environment.lower() == "production":
            if not self.auth_email_redirect_to:
                raise ValueError("AUTH_EMAIL_REDIRECT_TO es obligatorio en producción")
            parsed = urlparse(self.auth_email_redirect_to)
            hostname = (parsed.hostname or "").lower()
            if parsed.scheme != "https" or hostname == "localhost" or hostname.endswith(
                ".localhost"
            ) or hostname in {"127.0.0.1", "::1"}:
                raise ValueError(
                    "AUTH_EMAIL_REDIRECT_TO en producción debe usar HTTPS y no localhost"
                )
        return self

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
