"""Acceso a la relación de seguimiento mediante SQLAlchemy asíncrono."""

from uuid import UUID, uuid4

from sqlalchemy import delete, desc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models.follow_model import FollowModel
from app.infrastructure.db.models.notification_model import NotificationModel
from app.infrastructure.db.models.user_model import UserModel


class SQLAlchemyFollowRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def follow(self, follower_id: UUID, following_id: UUID) -> bool:
        """Inserta un seguimiento y devuelve False si ya existía."""
        existing = await self._session.get(FollowModel, (follower_id, following_id))
        if existing is not None:
            return False
        self._session.add(FollowModel(follower_id=follower_id, following_id=following_id))
        self._session.add(
            NotificationModel(
                id=uuid4(),
                actor_id=follower_id,
                recipient_id=following_id,
                post_id=None,
                type="follow",
            )
        )
        try:
            await self._session.commit()
        except IntegrityError:
            await self._session.rollback()
            existing = await self._session.get(FollowModel, (follower_id, following_id))
            if existing is not None:
                return False
            raise
        return True

    async def unfollow(self, follower_id: UUID, following_id: UUID) -> None:
        await self._session.execute(
            delete(FollowModel).where(
                FollowModel.follower_id == follower_id,
                FollowModel.following_id == following_id,
            )
        )
        await self._session.commit()

    async def list_following(self, user_id: UUID, limit: int, offset: int) -> list[UserModel]:
        statement = (
            select(UserModel)
            .join(FollowModel, FollowModel.following_id == UserModel.id)
            .where(FollowModel.follower_id == user_id)
            .order_by(desc(FollowModel.created_at), UserModel.id)
            .limit(limit)
            .offset(offset)
        )
        return list((await self._session.scalars(statement)).all())

    async def list_followers(self, user_id: UUID, limit: int, offset: int) -> list[UserModel]:
        statement = (
            select(UserModel)
            .join(FollowModel, FollowModel.follower_id == UserModel.id)
            .where(FollowModel.following_id == user_id)
            .order_by(desc(FollowModel.created_at), UserModel.id)
            .limit(limit)
            .offset(offset)
        )
        return list((await self._session.scalars(statement)).all())

    async def is_following(self, follower_id: UUID, following_id: UUID) -> bool:
        statement = select(FollowModel.follower_id).where(
            FollowModel.follower_id == follower_id,
            FollowModel.following_id == following_id,
        )
        return (await self._session.scalar(statement)) is not None
