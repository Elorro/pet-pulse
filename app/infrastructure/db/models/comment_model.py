from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base


class CommentModel(Base):
<<<<<<< HEAD
    """Modelo de la tabla existente `comment` en Supabase."""

    __tablename__ = "comment"
=======
    """Modelo de la tabla existente `coment` en Supabase."""

    __tablename__ = "coment"
>>>>>>> origin/main

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    post_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("posts.id", ondelete="CASCADE", onupdate="CASCADE")
    )
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    media: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False
    )
