"""Endpoints autenticados para seguir perfiles."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.api.deps import get_current_profile, get_follow_repository, get_user_repository
from app.domain.entities.user import User
from app.domain.repositories.user_repository import UserRepository
from app.infrastructure.db.models.user_model import UserModel
from app.infrastructure.repositories.sqlalchemy_follow_repository import (
    SQLAlchemyFollowRepository,
)

router = APIRouter(prefix="/profiles", tags=["profiles"])


class FollowProfile(BaseModel):
    id: uuid.UUID
    username: str
    full_name: str | None
    photo_url: str | None


class FollowMutationResponse(BaseModel):
    profile_id: uuid.UUID
    following: bool
    created: bool


class FollowStatusResponse(BaseModel):
    profile_id: uuid.UUID
    following: bool
    followed_by: bool


def _profile(user: UserModel) -> FollowProfile:
    return FollowProfile(
        id=user.id,
        username=user.username,
        full_name=user.full_name,
        photo_url=user.photo_url,
    )


@router.put(
    "/{profile_id}/follow",
    response_model=FollowMutationResponse,
    summary="Seguir un perfil",
    responses={
        400: {"description": "No es posible seguir el propio perfil"},
        401: {"description": "Falta un token de autenticación válido"},
        404: {"description": "No existe el perfil"},
    },
)
async def follow_profile(
    profile_id: uuid.UUID,
    user: User = Depends(get_current_profile),
    user_repository: UserRepository = Depends(get_user_repository),
    follow_repository: SQLAlchemyFollowRepository = Depends(get_follow_repository),
) -> FollowMutationResponse:
    if profile_id == user.id:
        raise HTTPException(status_code=400, detail="No puedes seguir tu propio perfil")
    if await user_repository.get_by_id(profile_id) is None:
        raise HTTPException(status_code=404, detail="No existe el perfil")
    created = await follow_repository.follow(user.id, profile_id)
    return FollowMutationResponse(profile_id=profile_id, following=True, created=created)


@router.delete(
    "/{profile_id}/follow",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Dejar de seguir un perfil",
    responses={
        400: {"description": "No es posible dejar de seguir el propio perfil"},
        401: {"description": "Falta un token de autenticación válido"},
        404: {"description": "No existe el perfil"},
    },
)
async def unfollow_profile(
    profile_id: uuid.UUID,
    user: User = Depends(get_current_profile),
    user_repository: UserRepository = Depends(get_user_repository),
    follow_repository: SQLAlchemyFollowRepository = Depends(get_follow_repository),
) -> None:
    if profile_id == user.id:
        raise HTTPException(status_code=400, detail="No puedes dejar de seguir tu propio perfil")
    if await user_repository.get_by_id(profile_id) is None:
        raise HTTPException(status_code=404, detail="No existe el perfil")
    await follow_repository.unfollow(user.id, profile_id)


@router.get(
    "/following",
    response_model=list[FollowProfile],
    summary="Listar perfiles que sigue el usuario autenticado",
    responses={401: {"description": "Falta un token de autenticación válido"}},
)
async def list_following(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_profile),
    repository: SQLAlchemyFollowRepository = Depends(get_follow_repository),
) -> list[FollowProfile]:
    return [_profile(row) for row in await repository.list_following(user.id, limit, offset)]


@router.get(
    "/followers",
    response_model=list[FollowProfile],
    summary="Listar perfiles que siguen al usuario autenticado",
    responses={401: {"description": "Falta un token de autenticación válido"}},
)
async def list_followers(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_profile),
    repository: SQLAlchemyFollowRepository = Depends(get_follow_repository),
) -> list[FollowProfile]:
    return [_profile(row) for row in await repository.list_followers(user.id, limit, offset)]


@router.get(
    "/{profile_id}/follow-status",
    response_model=FollowStatusResponse,
    summary="Consultar estado de seguimiento",
    responses={
        401: {"description": "Falta un token de autenticación válido"},
        404: {"description": "No existe el perfil"},
    },
)
async def follow_status(
    profile_id: uuid.UUID,
    user: User = Depends(get_current_profile),
    user_repository: UserRepository = Depends(get_user_repository),
    follow_repository: SQLAlchemyFollowRepository = Depends(get_follow_repository),
) -> FollowStatusResponse:
    if await user_repository.get_by_id(profile_id) is None:
        raise HTTPException(status_code=404, detail="No existe el perfil")
    following = await follow_repository.is_following(user.id, profile_id)
    followed_by = await follow_repository.is_following(profile_id, user.id)
    return FollowStatusResponse(
        profile_id=profile_id, following=following, followed_by=followed_by
    )
