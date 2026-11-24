from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base


class FollowModel(Base):
    """Relación unilateral de seguimiento entre dos perfiles."""

    __tablename__ = "follows"
    __table_args__ = (Index("follows_following_id_idx", "following_id"),)
    follower_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    following_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
