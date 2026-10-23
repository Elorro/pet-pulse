"""Router para el foro de publicaciones."""

import re
import uuid
from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.api.deps import (
    get_comment_repository,
    get_current_profile,
    get_post_repository,
    get_storage_service,
)
from app.application.interfaces.storage_service import (
    StorageService,
    StorageServiceError,
)
from app.domain.entities.post import Post
from app.domain.entities.user import User
from app.domain.repositories.comment_repository import CommentRepository
from app.domain.repositories.post_repository import PostRepository

router = APIRouter(prefix="/posts", tags=["posts"])

ALLOWED_MEDIA_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
}
MAX_MEDIA_SIZE_BYTES = 5 * 1024 * 1024


def _normalize_content_type(value: str | None) -> str | None:
    """Return the MIME essence without parameters, preserving the allowlist check."""
    if value is None:
        return None
    return value.split(";", 1)[0].strip().lower()


class PostCreate(BaseModel):
    """Esquema de entrada para crear una publicación."""

    content: str = Field(..., min_length=1, max_length=5000)
    media_path: str | None = None


class MediaUploadCreate(BaseModel):
    """Solicitud de URL firmada para subir una imagen."""

    content_type: Literal["image/jpeg", "image/png", "image/webp", "image/gif"]


class CommentMediaUploadCreate(MediaUploadCreate):
    """Solicitud firmada; file_size_bytes sirve para rechazar archivos grandes antes de subir."""

    file_size_bytes: int = Field(..., gt=0, le=MAX_MEDIA_SIZE_BYTES)


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


class CommentAuthorResponse(BaseModel):
    id: uuid.UUID
    username: str


class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)
    media_path: str | None = Field(
        default=None,
        description=(
            "Ruta devuelta por POST /api/v1/posts/comment-media-uploads; "
            "debe pertenecer al usuario autenticado y estar cargada."
        ),
    )


class CommentResponse(BaseModel):
    id: uuid.UUID
    post_id: uuid.UUID
    content: str | None
    media_url: str | None = Field(
        description="URL pública renderizable del adjunto; null para comentarios solo de texto."
    )
    created_at: datetime
    author: CommentAuthorResponse


def _require_storage(storage: StorageService | None) -> StorageService:
    if storage is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="La carga de imágenes no está configurada",
        )
    return storage


def _to_response(post: Post, like_count: int = 0) -> PostResponse:
    return PostResponse(
        id=post.id,
        author_id=post.author_id,
        content=post.content,
        created_at=post.created_at,
        updated_at=post.updated_at,
        media_url=post.media_url,
        like_count=like_count,
    )


def _to_comment_response(
    comment, author: User, storage: StorageService | None
) -> CommentResponse:
    media_url = None
    if comment.media is not None:
        # comment.media persiste una ruta creada por el servidor, nunca una URL.
        media_url = _require_storage(storage).public_url(comment.media)
    return CommentResponse(
        id=comment.id,
        post_id=comment.post_id,
        content=comment.content,
        media_url=media_url,
        created_at=comment.created_at,
        author=CommentAuthorResponse(id=author.id, username=author.username),
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


@router.post(
    "/comment-media-uploads",
    response_model=MediaUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Solicitar URL de carga para adjunto de comentario",
    description=(
        "Acepta JPEG, PNG, WebP o GIF de hasta 5 MiB. La API vuelve a verificar "
        "tipo y tamaño del objeto al crear el comentario."
    ),
    responses={
        401: {"description": "Falta un token de autenticación válido"},
        422: {"description": "Tipo o tamaño no válido"},
        502: {"description": "No se pudo preparar la carga"},
        503: {"description": "Almacenamiento no configurado"},
    },
)
async def create_comment_media_upload(
    payload: CommentMediaUploadCreate,
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
    return [_to_response(post, like_counts[post.id]) for post in posts]


@router.get("/{post_id}", response_model=PostResponse, summary="Get post")
async def get_post(
    post_id: uuid.UUID,
    post_repo: PostRepository = Depends(get_post_repository),
) -> PostResponse:
    post = await post_repo.get_by_id(post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return _to_response(post, await post_repo.get_like_count(post_id))


@router.get(
    "/{post_id}/comments",
    response_model=list[CommentResponse],
    summary="Listar comentarios de una publicación",
    responses={404: {"description": "La publicación no existe"}},
)
async def list_comments(
    post_id: uuid.UUID,
    post_repo: PostRepository = Depends(get_post_repository),
    comment_repo: CommentRepository = Depends(get_comment_repository),
    storage: StorageService | None = Depends(get_storage_service),
) -> list[CommentResponse]:
    if await post_repo.get_by_id(post_id) is None:
        raise HTTPException(status_code=404, detail="Post not found")
    comments = await comment_repo.get_for_post(post_id)
    return [_to_comment_response(comment, author, storage) for comment, author in comments]


@router.post(
    "/{post_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear comentario",
    description="Crea un comentario en nombre del usuario autenticado con Supabase.",
    responses={
        401: {"description": "Falta un token de autenticación válido"},
        404: {"description": "La publicación no existe"},
        422: {"description": "La ruta, el MIME o el tamaño del adjunto no son válidos"},
        502: {"description": "No se pudo verificar el adjunto"},
        503: {"description": "Almacenamiento no configurado"},
    },
)
async def create_comment(
    post_id: uuid.UUID,
    payload: CommentCreate,
    author: User = Depends(get_current_profile),
    comment_repo: CommentRepository = Depends(get_comment_repository),
    storage: StorageService | None = Depends(get_storage_service),
) -> CommentResponse:
    media_path = None
    if payload.media_path is not None:
        storage = _require_storage(storage)
        if not re.fullmatch(
            rf"{author.id}/[0-9a-f-]{{36}}\.(jpg|png|webp|gif)", payload.media_path
        ):
            raise HTTPException(status_code=422, detail="media_path no válido")
        try:
            stored = await storage.get_object(payload.media_path)
        except StorageServiceError as exc:
            raise HTTPException(status_code=502, detail="No se pudo verificar el adjunto") from exc
        if stored is None:
            raise HTTPException(status_code=422, detail="El adjunto no se ha subido")
        extension = payload.media_path.rsplit(".", 1)[1]
        expected_type = {
            "jpg": "image/jpeg",
            "png": "image/png",
            "webp": "image/webp",
            "gif": "image/gif",
        }[extension]
        if stored.size_bytes > MAX_MEDIA_SIZE_BYTES:
            raise HTTPException(status_code=422, detail="El adjunto supera el máximo de 5 MB")
        if stored.size_bytes <= 0 or _normalize_content_type(stored.content_type) != expected_type:
            raise HTTPException(status_code=422, detail="El tipo del adjunto no coincide")
        media_path = payload.media_path
    comment = await comment_repo.create(post_id, author.id, payload.content, media_path)
    if comment is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return _to_comment_response(comment, author, storage)


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


@router.get("/{post_id}/like", response_model=LikeResponse, summary="Consultar like de publicación")
async def get_post_like(
    post_id: uuid.UUID,
    user: User = Depends(get_current_profile),
    post_repo: PostRepository = Depends(get_post_repository),
) -> LikeResponse:
    result = await post_repo.get_user_like(post_id, user.id)
    if result is None:
        raise HTTPException(status_code=404, detail="Post not found")
    like_count, liked = result
    return LikeResponse(post_id=post_id, like_count=like_count, liked=liked)


@router.delete("/{post_id}/like", response_model=LikeResponse, summary="Quitar like de publicación")
async def unlike_post(
    post_id: uuid.UUID,
    user: User = Depends(get_current_profile),
    post_repo: PostRepository = Depends(get_post_repository),
) -> LikeResponse:
    like_count = await post_repo.unlike(post_id, user.id)
    if like_count is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return LikeResponse(post_id=post_id, like_count=like_count, liked=False)


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
