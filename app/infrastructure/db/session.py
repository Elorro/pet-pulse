import os

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings

settings = get_settings()


def _async_database_url(database_url: str) -> str:
    """Normalize PostgreSQL URLs for SQLAlchemy's asyncpg driver."""
    url = make_url(database_url)
    if url.drivername in {
        "postgres",
        "postgresql",
        "postgresql+psycopg",
        "postgresql+psycopg2",
    }:
        url = url.set(drivername="postgresql+asyncpg")

    query = dict(url.query)
    sslmode = query.pop("sslmode", None)
    if sslmode and "ssl" not in query:
        query["ssl"] = sslmode

    # Supabase requires TLS for hosted PostgreSQL connections.
    host = url.host or ""
    if "supabase" in host and "ssl" not in query:
        query["ssl"] = "require"

    return url.set(query=query).render_as_string(hide_password=False)


# En Vercel cada instancia es efímera: sin pool propio, el pooler de Supabase gestiona
# las conexiones y no quedan conexiones abiertas en instancias suspendidas.
engine = create_async_engine(
    _async_database_url(settings.database_url_async),
    echo=settings.environment == "development",
    poolclass=NullPool if os.environ.get("VERCEL") else None,
)
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
