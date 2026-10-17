"""Implementación concreta del repositorio de usuarios usando SQLAlchemy 2.0 asíncrono."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.user import User
from app.domain.repositories.user_repository import UserRepository
from app.infrastructure.db.datetime_utils import as_utc
from app.infrastructure.db.models.user_model import UserModel


def _to_entity(user_orm: UserModel) -> User:
    return User(
        id=user_orm.id,
        username=user_orm.username,
        email=user_orm.email,
        created_at=as_utc(user_orm.created_at),
        updated_at=as_utc(user_orm.created_at),  # El MVP no registra edición por separado
    )


class SQLAlchemyUserRepository(UserRepository):
    """Repositorio concreto que accede a la tabla `users` mediante SQLAlchemy asíncrono."""

    def __init__(self, async_session: AsyncSession) -> None:
        self._session = async_session

    async def save(self, user: User) -> None:
        user_orm = UserModel(
            id=user.id,
            username=user.username,
            email=user.email,
            created_at=user.created_at,
        )
        self._session.add(user_orm)
        await self._session.commit()

    async def get_by_id(self, user_id: UUID) -> User | None:
        user_orm = await self._session.get(UserModel, user_id)
        return _to_entity(user_orm) if user_orm else None

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(UserModel).where(UserModel.email == email)
        result = await self._session.execute(stmt)
        user_orm = result.scalar_one_or_none()
        return _to_entity(user_orm) if user_orm else None

    async def get_by_username(self, username: str) -> User | None:
        stmt = select(UserModel).where(UserModel.username == username)
        result = await self._session.execute(stmt)
        user_orm = result.scalar_one_or_none()
        return _to_entity(user_orm) if user_orm else None

    async def rollback(self) -> None:
        await self._session.rollback()
