"""Define el puerto de infraestructura para la persistencia de publicaciones.

Esta interfaz abstracta desacopla la lógica de dominio de la implementación
concreta de base de datos, siguiendo el principio de inversión de dependencias.
"""

import abc
from uuid import UUID

from app.domain.entities.post import Post


class PostRepository(abc.ABC):
    """Interfaz abstracta para el repositorio de publicaciones.

    Las implementaciones concretas deben residir en infraestructura y
    proporcionar mecanismos reales de persistencia.
    """

    @abc.abstractmethod
    async def save(self, post: Post) -> None:
        """Persiste la publicación proporcionada.

        Args:
            post: Entidad de dominio Post a guardar.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def get_all_paginated(self, limit: int, offset: int) -> list[Post]:
        """Recupera publicaciones de forma paginada.

        Args:
            limit: Número máximo de publicaciones a devolver.
            offset: Cantidad de publicaciones a saltar.

        Returns:
            Lista de entidades Post correspondientes a la página solicitada.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def get_by_id(self, post_id: UUID) -> Post | None:
        """Recupera una publicación por su identificador."""
        raise NotImplementedError

    @abc.abstractmethod
    async def like(self, post_id: UUID, user_id: UUID) -> int | None:
        """Registra el like (si aún no existe) y devuelve el total; None si no existe el post."""
        raise NotImplementedError

    @abc.abstractmethod
    async def get_user_like(self, post_id: UUID, user_id: UUID) -> tuple[int, bool] | None:
        """Devuelve el total y si el usuario dio like; None si no existe el post."""
        raise NotImplementedError

    @abc.abstractmethod
    async def unlike(self, post_id: UUID, user_id: UUID) -> int | None:
        """Elimina únicamente el like del usuario y devuelve el total; None si no existe el post."""
        raise NotImplementedError

    @abc.abstractmethod
    async def get_like_count(self, post_id: UUID) -> int:
        """Devuelve el total de likes de una publicación."""
        raise NotImplementedError

    @abc.abstractmethod
    async def get_like_counts(self, post_ids: list[UUID]) -> dict[UUID, int]:
        """Devuelve los totales de likes de varias publicaciones en una consulta."""
        raise NotImplementedError
