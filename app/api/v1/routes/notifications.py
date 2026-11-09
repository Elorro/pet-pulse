import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.api.deps import get_current_profile, get_notification_repository
from app.domain.entities.user import User
from app.infrastructure.repositories.sqlalchemy_notification_repository import (
    SQLAlchemyNotificationRepository,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotificationActor(BaseModel):
    id: uuid.UUID
    username: str
    full_name: str | None
    photo_url: str | None


class NotificationPost(BaseModel):
    id: uuid.UUID
    content: str
    media_url: str | None


class NotificationResponse(BaseModel):
    id: uuid.UUID
    type: str
    created_at: datetime
    read_at: datetime | None
    actor: NotificationActor
    post: NotificationPost
    comment_content: str | None


class UnreadCountResponse(BaseModel):
    count: int


class MarkAllReadResponse(BaseModel):
    updated_count: int


@router.get("/", response_model=list[NotificationResponse], summary="Listar notificaciones")
async def list_notifications(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_profile),
    repository: SQLAlchemyNotificationRepository = Depends(get_notification_repository),
) -> list[NotificationResponse]:
    rows = await repository.list_for_user(user.id, limit, offset)
    return [
        NotificationResponse(
            id=row["notification"].id,
            type=row["notification"].type,
            created_at=row["notification"].created_at,
            read_at=row["notification"].read_at,
            actor=NotificationActor(
                id=row["actor"].id,
                username=row["actor"].username,
                full_name=row["actor"].full_name,
                photo_url=row["actor"].photo_url,
            ),
            post=NotificationPost(
                id=row["post"].id,
                content=row["post"].content,
                media_url=row["post"].media_url,
            ),
            comment_content=row["comment_content"],
        )
        for row in rows
    ]


@router.get("/unread-count", response_model=UnreadCountResponse, summary="Contar no leídas")
async def unread_count(
    user: User = Depends(get_current_profile),
    repository: SQLAlchemyNotificationRepository = Depends(get_notification_repository),
) -> UnreadCountResponse:
    return UnreadCountResponse(count=await repository.unread_count(user.id))


@router.patch("/{notification_id}/read", status_code=204, summary="Marcar como leída")
async def mark_notification_read(
    notification_id: uuid.UUID,
    user: User = Depends(get_current_profile),
    repository: SQLAlchemyNotificationRepository = Depends(get_notification_repository),
) -> None:
    if not await repository.mark_read(user.id, notification_id):
        raise HTTPException(status_code=404, detail="Notification not found")


@router.patch("/read-all", response_model=MarkAllReadResponse, summary="Marcar todas como leídas")
async def mark_all_read(
    user: User = Depends(get_current_profile),
    repository: SQLAlchemyNotificationRepository = Depends(get_notification_repository),
) -> MarkAllReadResponse:
    return MarkAllReadResponse(updated_count=await repository.mark_all_read(user.id))
