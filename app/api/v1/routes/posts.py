"""Router para el foro de publicaciones.

Define el endpoint GET / que devuelve una lista paginada de publicaciones,
inyectando el repositorio concreto y parametrizando la consulta para evitar
inyecciones SQL.
"""

from datetime import datetime
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.api.deps import get_post_repository
from app.domain.entities.post import Post
from app.domain.repositories.post_repository import PostRepository


router = APIRouter(prefix="/posts", tags=["posts"])


class PostResponse(BaseModel):
    """Esquema de salida para una publicación del foro."""

    id: UUID
    author_id: UUID
    content: str
    created_at: datetime
    updated_at: datetime


@router.get(
    "/",
    response_model=List[PostResponse],
    summary="Listar publicaciones",
    description="Obtiene publicaciones del foro de forma paginada.",
)
async def list_posts(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    post_repo: PostRepository = Depends(get_post_repository),
) -> List[PostResponse]:
    """Obtiene una lista paginada de publicaciones del foro.

    Args:
        limit: Número máximo de publicaciones a devolver (1-100).
        offset: Cantidad de publicaciones a omitir.
        post_repo: Repositorio de publicaciones inyectado.

    Returns:
        Lista de `PostResponse` correspondientes a la página solicitada.
    """
    posts: List[Post] = await post_repo.get_all_paginated(limit=limit, offset=offset)
    return [
        PostResponse(
            id=post.id,
            author_id=post.author_id,
            content=post.content,
            created_at=post.created_at,
            updated_at=post.updated_at,
        )
        for post in posts
    ]
