"""Router de identidad.

El registro e inicio de sesión ocurren en Supabase Auth desde la app móvil.
Este router solo expone el perfil asociado al token verificado.
"""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import get_current_profile
from app.domain.entities.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


class ProfileResponse(BaseModel):
    """Perfil público del usuario autenticado."""

    id: UUID
    username: str
    email: str | None
    created_at: datetime


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
        email=profile.email,
        created_at=profile.created_at,
    )
