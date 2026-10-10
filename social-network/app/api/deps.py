"""Módulo de inyección de dependencias para la capa de API de FastAPI.

Proporciona dependencias reutilizables para obtener la sesión de base de datos
y las implementaciones concretas de los repositorios, siguiendo el principio
de inversión de dependencias y garantizando una gestión limpia de recursos.
"""

from typing import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.repositories.post_repository import PostRepository
from app.domain.repositories.user_repository import UserRepository
from app.infrastructure.db.session import async_session_factory
from app.infrastructure.repositories.sqlalchemy_post_repository import SQLAlchemyPostRepository
from app.infrastructure.repositories.sqlalchemy_user_repository import SQLAlchemyUserRepository


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Inyecta una sesión asíncrona de SQLAlchemy.

    Crea una sesión a partir de la fábrica asíncrona, la entrega al endpoint
    mediante `yield` y garantiza su cierre en el bloque `finally`.

    Yields:
        AsyncSession: Sesión de base de datos lista para usar.
    """
    session = async_session_factory()
    try:
        yield session
    finally:
        await session.close()


async def get_user_repository(
    session: AsyncSession = Depends(get_async_session),
) -> UserRepository:
    """Inyecta el repositorio de usuarios configurado con la sesión activa.

    Args:
        session: Sesión asíncrona proporcionada por `get_async_session`.

    Returns:
        Instancia de `SQLAlchemyUserRepository` que implementa `UserRepository`.
    """
    return SQLAlchemyUserRepository(async_session=session)


async def get_post_repository(
    session: AsyncSession = Depends(get_async_session),
) -> PostRepository:
    """Inyecta el repositorio de publicaciones configurado con la sesión activa.

    Args:
        session: Sesión asíncrona proporcionada por `get_async_session`.

    Returns:
        Instancia de `SQLAlchemyPostRepository` que implementa `PostRepository`.
    """
    return SQLAlchemyPostRepository(async_session=session)
