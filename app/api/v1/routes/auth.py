"""Router de autenticación.

La app móvil solo habla con esta API. Los endpoints de registro, inicio de
sesión, renovación y cierre delegan en Supabase Auth mediante su SDK; el
backend nunca almacena contraseñas ni emite tokens propios.
"""

import secrets
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from app.api.deps import (
    get_auth_service,
    get_bearer_token,
    get_current_profile,
    get_user_repository,
)
from app.application.interfaces.auth_service import (
    AuthService,
    AuthServiceError,
    AuthSession,
)
from app.domain.entities.user import User
from app.domain.repositories.user_repository import UserRepository

router = APIRouter(prefix="/auth", tags=["auth"])


class SignUpRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    username: str = Field(..., min_length=3, max_length=50)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1)


class SessionResponse(BaseModel):
    """Tokens que la app debe guardar y enviar en `Authorization: Bearer`."""

    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str
    user_id: UUID
    email: str | None


class SignUpResponse(BaseModel):
    user_id: UUID
    email: str | None
    session: SessionResponse | None
    requires_email_confirmation: bool


class ProfileResponse(BaseModel):
    """Perfil público del usuario autenticado."""

    id: UUID
    username: str
    full_name: str | None
    photo_url: str | None
    email: str | None
    created_at: datetime


def _session_response(session: AuthSession) -> SessionResponse:
    return SessionResponse(
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        expires_in=session.expires_in,
        token_type=session.token_type,
        user_id=session.user_id,
        email=session.email,
    )


def _http_error(exc: AuthServiceError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.message)


@router.post(
    "/signup",
    response_model=SignUpResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar usuario",
    description="Crea la cuenta en Supabase Auth. Si el proyecto exige confirmar el email, "
    "`session` será null hasta que el usuario confirme.",
)
async def sign_up(
    payload: SignUpRequest,
    auth: AuthService = Depends(get_auth_service),
    user_repo: UserRepository = Depends(get_user_repository),
) -> SignUpResponse:
    try:
        username = payload.username
        if await user_repo.get_by_username(username) is not None:
            # Leave room for the prefix and keep fallback names within VARCHAR(50).
            for _ in range(5):
                candidate = f"user_{secrets.token_hex(12)}"
                if await user_repo.get_by_username(candidate) is None:
                    username = candidate
                    break
            else:
                raise AuthServiceError(
                    "No se pudo asignar un nombre de usuario disponible", status_code=503
                )
        result = await auth.sign_up(payload.email, payload.password, username)
    except AuthServiceError as exc:
        raise _http_error(exc) from exc
    return SignUpResponse(
        user_id=result.user_id,
        email=result.email,
        session=_session_response(result.session) if result.session else None,
        requires_email_confirmation=result.session is None,
    )


@router.post(
    "/login",
    response_model=SessionResponse,
    summary="Iniciar sesión",
    description="Valida email y contraseña contra Supabase Auth y devuelve la sesión.",
)
async def login(
    payload: LoginRequest,
    auth: AuthService = Depends(get_auth_service),
) -> SessionResponse:
    try:
        session = await auth.sign_in(payload.email, payload.password)
    except AuthServiceError as exc:
        raise _http_error(exc) from exc
    return _session_response(session)


@router.post(
    "/refresh",
    response_model=SessionResponse,
    summary="Renovar sesión",
    description="Intercambia un refresh token por una sesión nueva.",
)
async def refresh(
    payload: RefreshRequest,
    auth: AuthService = Depends(get_auth_service),
) -> SessionResponse:
    try:
        session = await auth.refresh(payload.refresh_token)
    except AuthServiceError as exc:
        raise _http_error(exc) from exc
    return _session_response(session)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cerrar sesión",
    description="Revoca los refresh tokens del usuario en Supabase. "
    "El access token sigue siendo válido hasta su expiración.",
)
async def logout(
    access_token: str = Depends(get_bearer_token),
    auth: AuthService = Depends(get_auth_service),
) -> None:
    try:
        await auth.sign_out(access_token)
    except AuthServiceError as exc:
        raise _http_error(exc) from exc


@router.get(
    "/me",
    response_model=ProfileResponse,
    summary="Perfil del usuario autenticado",
    description="Devuelve el perfil asociado al JWT de Supabase, creándolo en la primera llamada.",
)
async def me(profile: User = Depends(get_current_profile)) -> ProfileResponse:
    return ProfileResponse(
        id=profile.id,
        username=profile.username,
        full_name=profile.full_name,
        photo_url=profile.photo_url,
        email=profile.email,
        created_at=profile.created_at,
    )
