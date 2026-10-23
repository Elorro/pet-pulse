"""Adaptador de `AuthService` sobre el SDK oficial de Supabase (`supabase-py`).

Se crea un cliente por operación para no compartir estado de sesión entre
peticiones: el SDK guarda la sesión del último `sign_in` en el cliente.
"""

import logging
from uuid import UUID

from supabase import AsyncClient, AsyncClientOptions, acreate_client
from supabase_auth.errors import AuthApiError, AuthError
from supabase_auth.types import Session

from app.application.interfaces.auth_service import (
    AuthService,
    AuthServiceError,
    AuthSession,
    SignUpResult,
)

logger = logging.getLogger(__name__)


def _to_session(session: Session) -> AuthSession:
    return AuthSession(
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        expires_in=session.expires_in,
        token_type=session.token_type,
        user_id=UUID(session.user.id),
        email=session.user.email,
    )


def _translate(exc: AuthError) -> AuthServiceError:
    status = getattr(exc, "status", 400)
    # Supabase responde 400/422 ante credenciales inválidas; la API las unifica en 401.
    if isinstance(exc, AuthApiError) and exc.code in {"invalid_credentials", "bad_jwt"}:
        status = 401
    return AuthServiceError(exc.message, status_code=int(status or 400))


class SupabaseAuthService(AuthService):
    def __init__(
        self, supabase_url: str, anon_key: str, email_redirect_to: str | None = None
    ) -> None:
        if not supabase_url or not anon_key:
            raise ValueError("SUPABASE_URL y SUPABASE_ANON_KEY son obligatorios")
        self._url = supabase_url
        self._anon_key = anon_key
        self._email_redirect_to = email_redirect_to

    async def _client(self) -> AsyncClient:
        return await acreate_client(
            self._url,
            self._anon_key,
            options=AsyncClientOptions(auto_refresh_token=False, persist_session=False),
        )

    async def sign_up(self, email: str, password: str, username: str) -> SignUpResult:
        client = await self._client()
        try:
            options: dict[str, object] = {"data": {"username": username}}
            if self._email_redirect_to:
                options["email_redirect_to"] = self._email_redirect_to
            response = await client.auth.sign_up(
                {"email": email, "password": password, "options": options}
            )
        except AuthError as exc:
            logger.warning(
                "Supabase Auth rechazó signup (status=%s, code=%s)",
                getattr(exc, "status", None),
                getattr(exc, "code", None),
            )
            raise _translate(exc) from exc
        except Exception:
            logger.exception("Error inesperado al llamar Supabase Auth signup")
            raise
        if response.user is None:
            raise AuthServiceError("El proveedor no devolvió un usuario", status_code=502)
        return SignUpResult(
            user_id=UUID(response.user.id),
            email=response.user.email,
            session=_to_session(response.session) if response.session else None,
        )

    async def sign_in(self, email: str, password: str) -> AuthSession:
        client = await self._client()
        try:
            response = await client.auth.sign_in_with_password(
                {"email": email, "password": password}
            )
        except AuthError as exc:
            logger.warning(
                "Supabase Auth rechazó login (status=%s, code=%s)",
                getattr(exc, "status", None),
                getattr(exc, "code", None),
            )
            raise _translate(exc) from exc
        if response.session is None:
            raise AuthServiceError("Credenciales inválidas", status_code=401)
        return _to_session(response.session)
    async def refresh(self, refresh_token: str) -> AuthSession:
        client = await self._client()
        try:
            response = await client.auth.refresh_session(refresh_token)
        except AuthError as exc:
            raise _translate(exc) from exc
        if response.session is None:
            raise AuthServiceError("Refresh token inválido", status_code=401)
        return _to_session(response.session)

    async def sign_out(self, access_token: str) -> None:
        client = await self._client()
        try:
            # Revoca los refresh tokens del usuario; el JWT sigue siendo válido hasta `exp`.
            await client.auth.admin.sign_out(access_token, "global")
        except AuthError as exc:
            raise _translate(exc) from exc
