"""Implementación concreta del repositorio de publicaciones usando SQLAlchemy 2.0 asíncrono.

Este adaptador convierte entidades de dominio en modelos ORM y ejecuta
consultas paginadas y parametrizadas para mantener la seguridad y el
desacoplamiento de la lógica de negocio.
"""

from uuid import UUID

from sqlalchemy import Integer, delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.post import Post
from app.domain.repositories.post_repository import PostRepository
from app.infrastructure.db.datetime_utils import as_utc
from app.infrastructure.db.models.post_like_model import PostLikeModel
from app.infrastructure.db.models.post_model import PostModel


class SQLAlchemyPostRepository(PostRepository):
    """Repositorio concreto que accede a la tabla `posts` mediante SQLAlchemy asíncrono.

    Recibe una sesión asíncrona y proporciona métodos para persistir y
    consultar publicaciones de forma eficiente.
    """

    def __init__(self, async_session: AsyncSession) -> None:
        self._session = async_session

    async def save(self, post: Post) -> None:
        """Persiste una entidad de dominio `Post` como registro ORM.

        Convierte la entidad en `PostModel` y la agrega a la sesión actual,
        realizando commit al finalizar.

        Args:
            post: Entidad de dominio de la publicación a guardar.
        """
        post_orm = PostModel(
            id=post.id,
            author_id=post.author_id,
            content=post.content,
            created_at=post.created_at,
            media_url=post.media_url,
        )
        self._session.add(post_orm)
        await self._session.commit()

    async def get_all_paginated(self, limit: int, offset: int) -> list[Post]:
        """Recupera publicaciones de forma paginada desde la base de datos.

        Utiliza `.limit(limit).offset(offset)` sobre una consulta parametrizada,
        devolviendo únicamente las columnas necesarias para mapear a entidades
        del dominio.

        Args:
            limit: Número máximo de publicaciones a devolver.
            offset: Cantidad de publicaciones a omitir.

        Returns:
            Lista de entidades `Post` correspondientes a la página solicitada.
        """
        stmt = select(PostModel).order_by(PostModel.created_at.desc()).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        post_orms = result.scalars().all()

        return [
            Post(
                id=post_orm.id,
                author_id=post_orm.author_id,
                content=post_orm.content,
                created_at=as_utc(post_orm.created_at),
                updated_at=as_utc(post_orm.created_at),  # El MVP no registra edición por separado
                media_url=post_orm.media_url,
            )
            for post_orm in post_orms
        ]

    async def get_by_id(self, post_id: UUID) -> Post | None:
        result = await self._session.execute(select(PostModel).where(PostModel.id == post_id))
        post_orm = result.scalar_one_or_none()
        if post_orm is None:
            return None
        return Post(
            id=post_orm.id,
            author_id=post_orm.author_id,
            content=post_orm.content,
            created_at=as_utc(post_orm.created_at),
            updated_at=as_utc(post_orm.created_at),
            media_url=post_orm.media_url,
        )

    async def get_like_count(self, post_id: UUID) -> int:
        result = await self._session.execute(
            select(func.count()).select_from(PostLikeModel).where(PostLikeModel.post_id == post_id)
        )
        return int(result.scalar_one())

    async def get_like_counts(self, post_ids: list[UUID]) -> dict[UUID, int]:
        if not post_ids:
            return {}
        result = await self._session.execute(
            select(PostLikeModel.post_id, func.count(PostLikeModel.id))
            .where(PostLikeModel.post_id.in_(post_ids))
            .group_by(PostLikeModel.post_id)
        )
        counts = {post_id: int(count) for post_id, count in result.all()}
        return {post_id: counts.get(post_id, 0) for post_id in post_ids}

    async def like(self, post_id: UUID, user_id: UUID) -> int | None:
        post_exists = await self._session.execute(
            select(PostModel.id).where(PostModel.id == post_id)
        )
        if post_exists.scalar_one_or_none() is None:
            return None

        existing = await self._session.execute(
            select(PostLikeModel.id).where(
                PostLikeModel.post_id == post_id, PostLikeModel.user_id == user_id
            )
        )
        if existing.scalar_one_or_none() is None:
            self._session.add(PostLikeModel(post_id=post_id, user_id=user_id))
            try:
                await self._session.commit()
            except IntegrityError:
                # Una solicitud concurrente pudo insertar el mismo like primero.
                await self._session.rollback()
        return await self.get_like_count(post_id)

    async def get_user_like(self, post_id: UUID, user_id: UUID) -> tuple[int, bool] | None:
        post_exists = await self._session.execute(
            select(PostModel.id).where(PostModel.id == post_id)
        )
        if post_exists.scalar_one_or_none() is None:
            return None

        result = await self._session.execute(
            select(
                func.count(PostLikeModel.id),
                func.coalesce(
                    func.max(
                        (PostLikeModel.user_id == user_id).cast(Integer)
                    ),
                    0,
                ),
            ).where(PostLikeModel.post_id == post_id)
        )
        like_count, liked = result.one()
        return int(like_count), bool(liked)

    async def unlike(self, post_id: UUID, user_id: UUID) -> int | None:
        post_exists = await self._session.execute(
            select(PostModel.id).where(PostModel.id == post_id)
        )
        if post_exists.scalar_one_or_none() is None:
            return None

        await self._session.execute(
            delete(PostLikeModel).where(
                PostLikeModel.post_id == post_id,
                PostLikeModel.user_id == user_id,
            )
        )
        await self._session.commit()
        return await self.get_like_count(post_id)
