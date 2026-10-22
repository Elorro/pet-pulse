import abc
from uuid import UUID

from app.domain.entities.comment import Comment
from app.domain.entities.user import User


class CommentRepository(abc.ABC):
    @abc.abstractmethod
    async def get_for_post(self, post_id: UUID) -> list[tuple[Comment, User]]:
        raise NotImplementedError

    @abc.abstractmethod
    async def create(
        self, post_id: UUID, user_id: UUID, content: str, media: str | None = None
    ) -> Comment | None:
        """Persist a comment; return None when the post does not exist."""
        raise NotImplementedError
