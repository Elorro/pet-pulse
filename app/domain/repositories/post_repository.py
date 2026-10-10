"""Define el puerto de infraestructura para la persistencia de publicaciones.

Esta interfaz abstracta desacopla la lógica de dominio de la implementación
concreta de base de datos, siguiendo el principio de inversión de dependencias.
"""

import abc

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
