"""Router para el foro de publicaciones."""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field

from app.api.deps import get_current_profile, get_post_repository
from app.domain.entities.post import Post
from app.domain.entities.user import User
from app.domain.repositories.post_repository import PostRepository

router = APIRouter(prefix="/posts", tags=["posts"])


class PostCreate(BaseModel):
    """Esquema de entrada para crear una publicación."""

    content: str = Field(..., min_length=1, max_length=5000)


class PostResponse(BaseModel):
    """Esquema de salida para una publicación del foro."""

    id: uuid.UUID
    author_id: uuid.UUID
    content: str
    created_at: datetime
    updated_at: datetime


def _to_response(post: Post) -> PostResponse:
    return PostResponse(
        id=post.id,
        author_id=post.author_id,
        content=post.content,
        created_at=post.created_at,
        updated_at=post.updated_at,
    )


@router.get(
    "/",
    response_model=list[PostResponse],
    summary="Listar publicaciones",
    description="Obtiene publicaciones del foro de forma paginada.",
)
async def list_posts(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    post_repo: PostRepository = Depends(get_post_repository),
) -> list[PostResponse]:
    posts = await post_repo.get_all_paginated(limit=limit, offset=offset)
    return [_to_response(post) for post in posts]


@router.post(
    "/",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear publicación",
    description="Crea una publicación en nombre del usuario autenticado con Supabase.",
)
async def create_post(
    payload: PostCreate,
    author: User = Depends(get_current_profile),
    post_repo: PostRepository = Depends(get_post_repository),
) -> PostResponse:
    now = datetime.now(UTC)
    post = Post(
        id=uuid.uuid4(),
        author_id=author.id,
        content=payload.content,
        created_at=now,
        updated_at=now,
    )
    await post_repo.save(post)
    return _to_response(post)
