from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models.comment_model import CommentModel
from app.infrastructure.db.models.notification_model import NotificationModel
from app.infrastructure.db.models.post_model import PostModel
from app.infrastructure.db.models.user_model import UserModel


class SQLAlchemyNotificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_user(self, user_id: UUID, limit: int, offset: int) -> list[dict]:
        stmt = (
            select(NotificationModel, UserModel, PostModel, CommentModel.text)
            .join(UserModel, UserModel.id == NotificationModel.actor_id)
            .join(PostModel, PostModel.id == NotificationModel.post_id)
            .outerjoin(CommentModel, CommentModel.id == NotificationModel.source_comment_id)
            .where(NotificationModel.recipient_id == user_id)
            .order_by(NotificationModel.created_at.desc(), NotificationModel.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return [
            {"notification": n, "actor": actor, "post": post, "comment_content": content}
            for n, actor, post, content in (await self._session.execute(stmt)).all()
        ]

    async def unread_count(self, user_id: UUID) -> int:
        result = await self._session.execute(
            select(func.count(NotificationModel.id)).where(
                NotificationModel.recipient_id == user_id,
                NotificationModel.read_at.is_(None),
            )
        )
        return int(result.scalar_one())

    async def mark_read(self, user_id: UUID, notification_id: UUID) -> bool:
        result = await self._session.execute(
            update(NotificationModel)
            .where(
                NotificationModel.id == notification_id,
                NotificationModel.recipient_id == user_id,
                NotificationModel.read_at.is_(None),
            )
            .values(read_at=datetime.now(UTC))
        )
        await self._session.commit()
        if result.rowcount:
            return True
        return await self._session.scalar(
            select(NotificationModel.id).where(
                NotificationModel.id == notification_id,
                NotificationModel.recipient_id == user_id,
            )
        ) is not None

    async def mark_all_read(self, user_id: UUID) -> int:
        result = await self._session.execute(
            update(NotificationModel)
            .where(
                NotificationModel.recipient_id == user_id,
                NotificationModel.read_at.is_(None),
            )
            .values(read_at=datetime.now(UTC))
        )
        await self._session.commit()
        return int(result.rowcount or 0)
