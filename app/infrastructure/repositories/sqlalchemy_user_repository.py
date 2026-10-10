"""Implementación concreta del repositorio de usuarios usando SQLAlchemy 2.0 asíncrono.

Este adaptador convierte entidades de dominio en modelos ORM y ejecuta
consultas parametrizadas para aislar la lógica de negocio de la persistencia.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.user import User
from app.domain.repositories.user_repository import UserRepository
from app.infrastructure.db.models.user_model import UserModel


class SQLAlchemyUserRepository(UserRepository):
    """Repositorio concreto que accede a la tabla `users` mediante SQLAlchemy asíncrono.

    Recibe una sesión asíncrona de SQLAlchemy y gestiona la persistencia
    y consulta de usuarios sin exponer detalles de la base de datos.
    """

    def __init__(self, async_session: AsyncSession) -> None:
        self._session = async_session

    async def save(self, user: User) -> None:
        """Persiste una entidad de dominio `User` como registro ORM.

        Convierte la entidad en `UserModel` y la agrega a la sesión actual,
        realizando commit al finalizar.

        Args:
            user: Entidad de dominio del usuario a guardar.
        """
        user_orm = UserModel(
            id=user.id,
            username=user.username,
            email=user.email,
            hashed_password=user.hashed_password,
            created_at=user.created_at,
        )
        self._session.add(user_orm)
        await self._session.commit()

    async def get_by_email(self, email: str) -> User | None:
        """Busca un usuario por email en la base de datos.

        Ejecuta una consulta parametrizada con SQLAlchemy para evitar
        inyecciones SQL y devuelve la entidad de dominio correspondiente.

        Args:
            email: Email único del usuario a buscar.

        Returns:
            Instancia de `User` si existe, `None` en caso contrario.
        """
        stmt = select(UserModel).where(UserModel.email == email)
        result = await self._session.execute(stmt)
        user_orm = result.scalar_one_or_none()

        if not user_orm:
            return None

        return User(
            id=user_orm.id,
            username=user_orm.username,
            email=user_orm.email,
            hashed_password=user_orm.hashed_password,
            created_at=user_orm.created_at,
            updated_at=user_orm.created_at,  # El MVP no registra edición por separado
        )
