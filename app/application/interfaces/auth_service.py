"""Puerto de aplicación para el proveedor de identidad.

La app móvil solo habla con esta API; el registro, inicio de sesión,
renovación y cierre de sesión se delegan a un proveedor externo
(Supabase Auth) a través de esta interfaz.
"""

import abc
from dataclasses import dataclass
from uuid import UUID


class AuthServiceError(Exception):
    """El proveedor de identidad rechazó la operación."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


@dataclass(frozen=True)
class AuthSession:
    """Sesión emitida por el proveedor de identidad."""

    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str
    user_id: UUID
    email: str | None


@dataclass(frozen=True)
class SignUpResult:
    """Resultado de un registro.

    `session` es `None` cuando el proveedor exige confirmar el email antes
    de iniciar sesión.
    """

    user_id: UUID
    email: str | None
    session: AuthSession | None


class AuthService(abc.ABC):
    @abc.abstractmethod
    async def sign_up(self, email: str, password: str, username: str) -> SignUpResult:
        raise NotImplementedError

    @abc.abstractmethod
    async def sign_in(self, email: str, password: str) -> AuthSession:
        raise NotImplementedError

    @abc.abstractmethod
    async def refresh(self, refresh_token: str) -> AuthSession:
        raise NotImplementedError

    @abc.abstractmethod
    async def sign_out(self, access_token: str) -> None:
        raise NotImplementedError
