from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.comment import Comment
from app.domain.entities.user import User
from app.domain.repositories.comment_repository import CommentRepository
from app.infrastructure.db.datetime_utils import as_utc
from app.infrastructure.db.models.comment_model import CommentModel
from app.infrastructure.db.models.post_model import PostModel
from app.infrastructure.db.models.user_model import UserModel


class SQLAlchemyCommentRepository(CommentRepository):
    def __init__(self, async_session: AsyncSession) -> None:
        self._session = async_session

    async def get_for_post(self, post_id: UUID) -> list[tuple[Comment, User]]:
        stmt = (
            select(CommentModel, UserModel)
            .join(UserModel, CommentModel.user_id == UserModel.id)
            .where(CommentModel.post_id == post_id)
            .order_by(CommentModel.created_at, CommentModel.id)
        )
        rows = (await self._session.execute(stmt)).all()
        return [
            (
                Comment(
                    id=comment.id,
                    post_id=comment.post_id,
                    author_id=comment.user_id,
                    content=comment.text,
                    created_at=as_utc(comment.created_at),
                    updated_at=as_utc(comment.created_at),
                    media=comment.media,
                ),
                User(
                    id=user.id,
                    username=user.username,
                    email=None,
                    created_at=as_utc(user.created_at),
                    updated_at=as_utc(user.created_at),
                ),
            )
            for comment, user in rows
        ]

    async def create(
        self, post_id: UUID, user_id: UUID, content: str, media: str | None = None
    ) -> Comment | None:
        post_exists = await self._session.execute(
            select(PostModel.id).where(PostModel.id == post_id)
        )
        if post_exists.scalar_one_or_none() is None:
            return None

        comment = CommentModel(
            id=uuid4(), created_at=datetime.now(UTC), post_id=post_id, text=content,
            media=media, user_id=user_id
        )
        self._session.add(comment)
        await self._session.commit()
        return Comment(
            id=comment.id,
            post_id=post_id,
            author_id=user_id,
            content=content,
            created_at=as_utc(comment.created_at),
            updated_at=as_utc(comment.created_at),
            media=media,
        )
