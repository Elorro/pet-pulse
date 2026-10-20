"""Creación de clientes Supabase aislados por solicitud."""

from supabase import Client, create_client
from supabase.client import ClientOptions

from app.core.config import get_settings


def create_supabase_client() -> Client:
    """Crea un cliente sin sesión persistida compartida entre solicitudes."""
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_key:
        raise RuntimeError("Faltan SUPABASE_URL y SUPABASE_KEY en el entorno.")

    return create_client(
        settings.supabase_url,
        settings.supabase_key,
        options=ClientOptions(persist_session=False, auto_refresh_token=False),
    )
