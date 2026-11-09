from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base


class NotificationModel(Base):
    """ORM para la tabla notifications creada en Supabase."""

    __tablename__ = "notifications"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    actor_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    recipient_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    post_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(Text, nullable=False)
    source_like_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("like.id", ondelete="CASCADE"), nullable=True, unique=True
    )
    source_comment_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("comment.id", ondelete="CASCADE"), nullable=True, unique=True
    )
