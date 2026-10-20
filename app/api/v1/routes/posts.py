"""Router para el foro de publicaciones."""

import re
import uuid
from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.api.deps import get_current_profile, get_post_repository, get_storage_service
from app.application.interfaces.storage_service import StorageService, StorageServiceError
from app.domain.entities.post import Post
from app.domain.entities.user import User
from app.domain.repositories.post_repository import PostRepository

router = APIRouter(prefix="/posts", tags=["posts"])

ALLOWED_MEDIA_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
}


class PostCreate(BaseModel):
    """Esquema de entrada para crear una publicación."""

    content: str = Field(..., min_length=1, max_length=5000)
    media_path: str | None = None


class MediaUploadCreate(BaseModel):
    """Solicitud de URL firmada para subir una imagen."""

    content_type: Literal["image/jpeg", "image/png", "image/webp", "image/gif"]


class MediaUploadResponse(BaseModel):
    """Ruta de almacenamiento y URL temporal para la carga directa."""

    path: str
    upload_url: str


class PostResponse(BaseModel):
    """Esquema de salida para una publicación del foro."""

    id: uuid.UUID
    author_id: uuid.UUID
    content: str
    created_at: datetime
    updated_at: datetime
    media_url: str | None
    like_count: int = 0


class LikeResponse(BaseModel):
    post_id: uuid.UUID
    like_count: int
    liked: bool = True


def _require_storage(storage: StorageService | None) -> StorageService:
    if storage is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="La carga de imágenes no está configurada",
        )
    return storage


def _to_response(post: Post) -> PostResponse:
    return PostResponse(
        id=post.id,
        author_id=post.author_id,
        content=post.content,
        created_at=post.created_at,
        updated_at=post.updated_at,
        media_url=post.media_url,
    )


@router.post(
    "/media-uploads",
    response_model=MediaUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Solicitar URL de carga de imagen",
)
async def create_media_upload(
    payload: MediaUploadCreate,
    author: User = Depends(get_current_profile),
    storage: StorageService | None = Depends(get_storage_service),
) -> MediaUploadResponse:
    storage = _require_storage(storage)
    ext = ALLOWED_MEDIA_TYPES[payload.content_type]
    path = f"{author.id}/{uuid4()}.{ext}"
    try:
        signed = await storage.create_signed_upload(path)
    except StorageServiceError as exc:
        raise HTTPException(status_code=502, detail="No se pudo preparar la carga") from exc
    return MediaUploadResponse(path=signed.path, upload_url=signed.upload_url)


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
    like_counts = await post_repo.get_like_counts([post.id for post in posts])
    return [
        PostResponse(**_to_response(post).model_dump(), like_count=like_counts[post.id])
        for post in posts
    ]


@router.get("/{post_id}", response_model=PostResponse, summary="Get post")
async def get_post(
    post_id: uuid.UUID,
    post_repo: PostRepository = Depends(get_post_repository),
) -> PostResponse:
    post = await post_repo.get_by_id(post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return PostResponse(
        **_to_response(post).model_dump(),
        like_count=await post_repo.get_like_count(post_id),
    )


@router.post("/{post_id}/like", response_model=LikeResponse, summary="Like post")
async def like_post(
    post_id: uuid.UUID,
    user: User = Depends(get_current_profile),
    post_repo: PostRepository = Depends(get_post_repository),
) -> LikeResponse:
    like_count = await post_repo.like(post_id, user.id)
    if like_count is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return LikeResponse(post_id=post_id, like_count=like_count)


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
    storage: StorageService | None = Depends(get_storage_service),
) -> PostResponse:
    media_url = None
    if payload.media_path is not None:
        storage = _require_storage(storage)
        if not re.fullmatch(
            rf"{author.id}/[0-9a-f-]{{36}}\.(jpg|png|webp|gif)", payload.media_path
        ):
            raise HTTPException(status_code=422, detail="media_path no válido")
        try:
            if not await storage.exists(payload.media_path):
                raise HTTPException(status_code=422, detail="La imagen no se ha subido")
            media_url = storage.public_url(payload.media_path)
        except StorageServiceError as exc:
            raise HTTPException(status_code=502, detail="No se pudo verificar la imagen") from exc
    now = datetime.now(UTC)
    post = Post(
        id=uuid.uuid4(),
        author_id=author.id,
        content=payload.content,
        created_at=now,
        updated_at=now,
        media_url=media_url,
    )
    await post_repo.save(post)
    return _to_response(post)
