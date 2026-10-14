"""Orquestador principal de la API PetPulse.

Inicializa FastAPI con configuración global, aplica políticas de CORS,
agrega cabeceras de seguridad básicas y registra los routers versionados
de autenticación y publicaciones.
"""

from collections.abc import Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import RedirectResponse, Response

import app.infrastructure.db.models
from app.api.v1.routes import auth, posts
from app.core.config import get_settings
from app.infrastructure.db.base import Base
from app.infrastructure.db.session import engine

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Crea las tablas de la base de datos al iniciar la aplicación.

    Este bloque se ejecuta antes de que la API empiece a recibir
    peticiones, garantizando que los modelos ORM estén registrados
    y que las tablas existan en el esquema configurado.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app: FastAPI = FastAPI(
    title="PetPulse API",
    description="API REST para la red social de mascotas PetPulse.",
    version="0.1.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS controlado para aplicaciones móviles y frontend local.
# En producción deben ajustarse los orígenes permitidos mediante variables
# de entorno o la configuración centralizada.
# ---------------------------------------------------------------------------
cors_origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(
    request: Request,
    call_next: Callable[[Request], Response],
) -> Response:
    """Aplica cabeceras de seguridad y redirige HTTP a HTTPS en producción.

    Esta función añade protecciones básicas contra ataques de tipo
    clickjacking, MIME sniffing y carga de recursos externos no deseados.
    En entornos productivos fuerza el uso de HTTPS para cumplir con los
    controles de seguridad de la API.

    Args:
        request: Solicitud HTTP entrante.
        call_next: Siguiente middleware o endpoint en la cadena.

    Returns:
        Respuesta HTTP con cabeceras seguras o redirección a HTTPS.
    """
    response = await call_next(request)

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = "default-src 'self'"

    environment = getattr(settings, "environment", "development")
    if environment == "production" and request.url.scheme == "http":
        redirect_url = str(request.url).replace("http://", "https://", 1)
        return RedirectResponse(url=redirect_url, status_code=301)

    return response


# ---------------------------------------------------------------------------
# Registro de routers versionados.
# Los routers internos ya declaran preﬁjos de recurso (/auth y /posts),
# por lo que aquí solo se añade el preﬁjo de versión /api/v1.
# ---------------------------------------------------------------------------
app.include_router(auth.router, prefix="/api/v1", tags=["Autenticación"])
app.include_router(posts.router, prefix="/api/v1", tags=["Publicaciones"])
