"""Implementación concreta del repositorio de publicaciones usando SQLAlchemy 2.0 asíncrono.

Este adaptador convierte entidades de dominio en modelos ORM y ejecuta
consultas paginadas y parametrizadas para mantener la seguridad y el
desacoplamiento de la lógica de negocio.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.post import Post
from app.domain.repositories.post_repository import PostRepository
from app.infrastructure.db.post_model import PostORM


class SQLAlchemyPostRepository(PostRepository):
    """Repositorio concreto que accede a la tabla `posts` mediante SQLAlchemy asíncrono.

    Recibe una sesión asíncrona y proporciona métodos para persistir y
    consultar publicaciones de forma eficiente.
    """

    def __init__(self, async_session: AsyncSession) -> None:
        self._session = async_session

    async def save(self, post: Post) -> None:
        """Persiste una entidad de dominio `Post` como registro ORM.

        Convierte la entidad en `PostORM` y la agrega a la sesión actual,
        realizando commit al finalizar.

        Args:
            post: Entidad de dominio de la publicación a guardar.
        """
        post_orm = PostORM(
            id=post.id,
            author_id=post.author_id,
            content=post.content,
            created_at=post.created_at,
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
        stmt = (
            select(PostORM)
            .order_by(PostORM.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        post_orms = result.scalars().all()

        return [
            Post(
                id=post_orm.id,
                author_id=post_orm.author_id,
                content=post_orm.content,
                created_at=post_orm.created_at,
                updated_at=post_orm.created_at,  # El MVP no registra edición por separado
            )
            for post_orm in post_orms
        ]
