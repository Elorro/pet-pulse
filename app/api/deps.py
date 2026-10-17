"""Módulo de inyección de dependencias para la capa de API de FastAPI.

Proporciona la sesión de base de datos, los repositorios concretos y la
identidad del usuario autenticado mediante Supabase Auth.
"""

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from functools import lru_cache

from fastapi import Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.interfaces.auth_service import AuthService
from app.core.auth import AuthUser, InvalidTokenError, SupabaseTokenVerifier, get_token_verifier
from app.core.config import get_settings
from app.domain.entities.user import User
from app.domain.repositories.post_repository import PostRepository
from app.domain.repositories.user_repository import UserRepository
from app.infrastructure.db.session import async_session_factory
from app.infrastructure.repositories.sqlalchemy_post_repository import SQLAlchemyPostRepository
from app.infrastructure.repositories.sqlalchemy_user_repository import SQLAlchemyUserRepository
from app.infrastructure.services.supabase_auth_service import SupabaseAuthService

bearer_scheme = HTTPBearer(auto_error=False)


@lru_cache
def get_auth_service() -> AuthService:
    """Proveedor de identidad (Supabase) usado por los endpoints de /auth."""
    settings = get_settings()
    return SupabaseAuthService(settings.supabase_url, settings.supabase_anon_key)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Inyecta una sesión asíncrona de SQLAlchemy y garantiza su cierre."""
    session = async_session_factory()
    try:
        yield session
    finally:
        await session.close()


async def get_user_repository(
    session: AsyncSession = Depends(get_async_session),
) -> UserRepository:
    return SQLAlchemyUserRepository(async_session=session)


async def get_post_repository(
    session: AsyncSession = Depends(get_async_session),
) -> PostRepository:
    return SQLAlchemyPostRepository(async_session=session)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    verifier: SupabaseTokenVerifier = Depends(get_token_verifier),
) -> AuthUser:
    """Verifica el JWT de Supabase enviado en `Authorization: Bearer`.

    Responde 401 si falta el token o no supera la verificación. La
    verificación se ejecuta en un threadpool porque la descarga del JWKS
    es síncrona.
    """
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token de acceso inválido o ausente",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise unauthorized
    try:
        return await run_in_threadpool(verifier.verify, credentials.credentials)
    except InvalidTokenError as exc:
        raise unauthorized from exc


async def get_bearer_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    """Devuelve el token crudo del header `Authorization` o responde 401."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de acceso ausente",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials


def _default_username(auth_user: AuthUser) -> str:
    metadata = auth_user.claims.get("user_metadata") or {}
    username = metadata.get("username")
    if isinstance(username, str) and username.strip():
        return username.strip()[:50]
    return f"user_{auth_user.id.hex[:12]}"


async def _ensure_email_available(user_repo: UserRepository, auth_user: AuthUser) -> None:
    """Responde 409 si otro perfil local ya usa el correo del usuario autenticado."""
    if not auth_user.email:
        return
    owner = await user_repo.get_by_email(auth_user.email)
    if owner is not None and owner.id != auth_user.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El correo ya está asociado a otro perfil",
        )


async def get_current_profile(
    auth_user: AuthUser = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repository),
) -> User:
    """Devuelve el perfil local del usuario autenticado, creándolo si no existe.

    Supabase gestiona el registro; la fila en `users` se crea de forma
    perezosa la primera vez que un usuario autenticado llama a la API.
    """
    existing = await user_repo.get_by_id(auth_user.id)
    if existing is not None:
        return existing

    await _ensure_email_available(user_repo, auth_user)

    now = datetime.now(UTC)
    user = User(
        id=auth_user.id,
        username=_default_username(auth_user),
        email=auth_user.email,
        created_at=now,
        updated_at=now,
    )
    try:
        await user_repo.save(user)
    except IntegrityError:
        # Another request may have claimed the same username or email after the lookup.
        await user_repo.rollback()
        existing = await user_repo.get_by_id(auth_user.id)
        if existing is not None:
            return existing
        await _ensure_email_available(user_repo, auth_user)
        user.username = f"user_{auth_user.id.hex}"
        try:
            await user_repo.save(user)
        except IntegrityError as exc:
            await user_repo.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No se pudo crear el perfil por un conflicto de unicidad",
            ) from exc
    return user
