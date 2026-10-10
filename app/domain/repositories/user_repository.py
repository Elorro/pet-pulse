"""Define el puerto de infraestructura para la persistencia de usuarios.

Esta interfaz abstracta invierte la dependencia del dominio hacia la
capa de infraestructura, permitiendo sustituir la implementación concreta
de base de datos sin alterar la lógica de negocio.
"""

import abc

from app.domain.entities.user import User


class UserRepository(abc.ABC):
    """Interfaz abstracta para el repositorio de usuarios.

    Las implementaciones concretas deben vivir en la capa de
    infraestructura y proveer persistencia real (SQL, ORM, etc.).
    """

    @abc.abstractmethod
    async def save(self, user: User) -> None:
        """Persiste el usuario proporcionado.

        Args:
            user: Entidad de dominio User a guardar.
        """
        raise NotImplementedError

    @abc.abstractmethod
    async def get_by_email(self, email: str) -> User | None:
        """Recupera un usuario por su dirección de correo electrónico.

        Args:
            email: Email único del usuario a buscar.

        Returns:
            Instancia de User si existe, en caso contrario None.
        """
        raise NotImplementedError
