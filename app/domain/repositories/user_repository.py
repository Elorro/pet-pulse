"""Define el puerto de infraestructura para la persistencia de perfiles de usuario.

Esta interfaz abstracta invierte la dependencia del dominio hacia la
capa de infraestructura, permitiendo sustituir la implementación concreta
de base de datos sin alterar la lógica de negocio.
"""

import abc
from uuid import UUID

from app.domain.entities.user import User


class UserRepository(abc.ABC):
    """Interfaz abstracta para el repositorio de usuarios."""

    @abc.abstractmethod
    async def save(self, user: User) -> None:
        """Persiste el perfil proporcionado."""
        raise NotImplementedError

    @abc.abstractmethod
    async def get_by_id(self, user_id: UUID) -> User | None:
        """Recupera un perfil por su UUID de Supabase Auth."""
        raise NotImplementedError

    @abc.abstractmethod
    async def get_by_email(self, email: str) -> User | None:
        """Recupera un perfil por su dirección de correo electrónico."""
        raise NotImplementedError
