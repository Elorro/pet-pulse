"""Verificación de tokens de acceso emitidos por Supabase Auth.

Supabase firma los JWT de sus usuarios con claves asimétricas (ES256/RS256)
publicadas en el endpoint JWKS del proyecto, o, en proyectos antiguos, con un
secreto compartido HS256. Este módulo valida ambos formatos y expone la
identidad del usuario autenticado sin que el backend emita tokens propios.
"""

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any
from uuid import UUID

import jwt
from jwt import PyJWKClient

from app.core.config import get_settings

SUPPORTED_ALGORITHMS = ("ES256", "RS256", "HS256")


class InvalidTokenError(Exception):
    """El token no es válido, ha expirado o no pudo verificarse."""


@dataclass(frozen=True)
class AuthUser:
    """Identidad verificada de un usuario de Supabase Auth.

    Attributes:
        id: UUID del usuario en `auth.users` (claim `sub`).
        email: Email del usuario, si el proveedor lo expone.
        role: Rol de Postgres asociado (normalmente `authenticated`).
        claims: Payload completo del JWT para acceder a `user_metadata`.
    """

    id: UUID
    email: str | None
    role: str
    claims: dict[str, Any] = field(default_factory=dict, repr=False)


class SupabaseTokenVerifier:
    """Valida JWT de Supabase contra el JWKS del proyecto o el secreto legado."""

    def __init__(
        self,
        supabase_url: str,
        jwt_secret: str | None = None,
        audience: str = "authenticated",
    ) -> None:
        if not supabase_url:
            raise ValueError("SUPABASE_URL es obligatorio para verificar tokens")
        self._issuer = f"{supabase_url.rstrip('/')}/auth/v1"
        self._audience = audience
        self._jwt_secret = jwt_secret
        self._jwks_client = PyJWKClient(
            f"{self._issuer}/.well-known/jwks.json",
            cache_keys=True,
        )

    @property
    def issuer(self) -> str:
        return self._issuer

    def verify(self, token: str) -> AuthUser:
        """Verifica firma, expiración, emisor y audiencia del token.

        Args:
            token: JWT de acceso enviado por el cliente en `Authorization: Bearer`.

        Returns:
            `AuthUser` con la identidad contenida en el token.

        Raises:
            InvalidTokenError: si el token no supera alguna validación.
        """
        try:
            header = jwt.get_unverified_header(token)
            algorithm = header.get("alg")
            if algorithm not in SUPPORTED_ALGORITHMS:
                raise InvalidTokenError(f"Algoritmo no soportado: {algorithm}")

            if algorithm == "HS256":
                if not self._jwt_secret:
                    raise InvalidTokenError(
                        "Token HS256 recibido pero SUPABASE_JWT_SECRET no está configurado"
                    )
                key: Any = self._jwt_secret
            else:
                key = self._jwks_client.get_signing_key_from_jwt(token).key

            claims = jwt.decode(
                token,
                key,
                algorithms=[algorithm],
                audience=self._audience,
                issuer=self._issuer,
                options={"require": ["sub", "exp", "iss", "aud"]},
            )
        except InvalidTokenError:
            raise
        except jwt.PyJWTError as exc:
            raise InvalidTokenError(str(exc)) from exc

        try:
            user_id = UUID(str(claims["sub"]))
        except ValueError as exc:
            raise InvalidTokenError("El claim `sub` no es un UUID válido") from exc

        return AuthUser(
            id=user_id,
            email=claims.get("email"),
            role=str(claims.get("role", "authenticated")),
            claims=claims,
        )


@lru_cache
def get_token_verifier() -> SupabaseTokenVerifier:
    """Construye (una sola vez) el verificador a partir de la configuración."""
    settings = get_settings()
    return SupabaseTokenVerifier(
        supabase_url=settings.supabase_url,
        jwt_secret=settings.supabase_jwt_secret,
        audience=settings.supabase_jwt_audience,
    )
