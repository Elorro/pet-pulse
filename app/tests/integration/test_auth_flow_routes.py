"""Pruebas de los endpoints /auth/signup, /login, /refresh y /logout.

Se sustituye el `AuthService` real (SDK de Supabase) por un doble en memoria.
"""

import uuid
from datetime import UTC, datetime

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_auth_service, get_user_repository
from app.application.interfaces.auth_service import (
    AuthService,
    AuthServiceError,
    AuthSession,
    SignUpResult,
)
from app.domain.entities.user import User
from app.main import app


class FakeAuthService(AuthService):
    def __init__(self, confirm_email: bool = False) -> None:
        self.users: dict[str, tuple[uuid.UUID, str]] = {}
        self.refresh_tokens: dict[str, uuid.UUID] = {}
        self.revoked: list[str] = []
        self.confirm_email = confirm_email
        self.signup_usernames: dict[str, str] = {}

    def _session(self, user_id: uuid.UUID, email: str) -> AuthSession:
        refresh = f"refresh-{uuid.uuid4().hex}"
        self.refresh_tokens[refresh] = user_id
        return AuthSession(
            access_token=f"access-{user_id.hex}", refresh_token=refresh,
            expires_in=3600, token_type="bearer", user_id=user_id, email=email,
        )

    async def sign_up(self, email, password, username):
        if email in self.users:
            raise AuthServiceError("User already registered", status_code=422)
        user_id = uuid.uuid4()
        self.users[email] = (user_id, password)
        self.signup_usernames[email] = username
        session = None if self.confirm_email else self._session(user_id, email)
        return SignUpResult(user_id=user_id, email=email, session=session)

    async def sign_in(self, email, password):
        stored = self.users.get(email)
        if stored is None or stored[1] != password:
            raise AuthServiceError("Invalid login credentials", status_code=401)
        return self._session(stored[0], email)

    async def refresh(self, refresh_token):
        user_id = self.refresh_tokens.pop(refresh_token, None)
        if user_id is None:
            raise AuthServiceError("Invalid Refresh Token", status_code=401)
        email = next(e for e, (uid, _) in self.users.items() if uid == user_id)
        return self._session(user_id, email)

    async def sign_out(self, access_token):
        self.revoked.append(access_token)


class FakeUserRepository:
    def __init__(self):
        self.users: dict[uuid.UUID, User] = {}

    async def get_by_username(self, username):
        return next((u for u in self.users.values() if u.username == username), None)

    async def get_by_id(self, user_id):
        return self.users.get(user_id)

    async def get_by_email(self, email):
        return next((u for u in self.users.values() if u.email == email), None)

    async def save(self, user):
        self.users[user.id] = user

    async def rollback(self):
        pass


@pytest_asyncio.fixture
async def fake_auth():
    return FakeAuthService()


@pytest_asyncio.fixture
async def fake_users():
    return FakeUserRepository()


@pytest_asyncio.fixture
async def client(fake_auth, fake_users):
    app.dependency_overrides[get_auth_service] = lambda: fake_auth
    app.dependency_overrides[get_user_repository] = lambda: fake_users
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


SIGNUP = {"email": "ana@example.com", "password": "secreto123", "username": "ana"}


async def test_signup_returns_session(client):
    response = await client.post("/api/v1/auth/signup", json=SIGNUP)
    assert response.status_code == 201
    body = response.json()
    assert body["requires_email_confirmation"] is False
    assert body["session"]["token_type"] == "bearer"
    assert body["session"]["user_id"] == body["user_id"]


async def test_signup_keeps_available_username_in_metadata(fake_auth, client):
    response = await client.post("/api/v1/auth/signup", json=SIGNUP)
    assert response.status_code == 201
    assert fake_auth.signup_usernames[SIGNUP["email"]] == "ana"


async def test_signup_uses_fallback_when_username_is_taken(fake_auth, fake_users, client):
    existing_id = uuid.uuid4()
    now = datetime.now(UTC)
    fake_users.users[existing_id] = User(
        id=existing_id, username="ana", email="taken@example.com",
        created_at=now, updated_at=now,
    )
    response = await client.post("/api/v1/auth/signup", json=SIGNUP)
    assert response.status_code == 201
    assigned = fake_auth.signup_usernames[SIGNUP["email"]]
    assert assigned.startswith("user_")
    assert len(assigned) <= 50


async def test_signup_with_email_confirmation_has_no_session(fake_auth, client):
    fake_auth.confirm_email = True
    response = await client.post("/api/v1/auth/signup", json=SIGNUP)
    assert response.status_code == 201
    assert response.json()["session"] is None
    assert response.json()["requires_email_confirmation"] is True


async def test_signup_duplicate_is_422(client):
    await client.post("/api/v1/auth/signup", json=SIGNUP)
    response = await client.post("/api/v1/auth/signup", json=SIGNUP)
    assert response.status_code == 422
    assert response.json()["detail"] == "User already registered"


async def test_signup_duplicate_email_is_422_even_with_taken_username(
    fake_auth, fake_users, client
):
    await client.post("/api/v1/auth/signup", json=SIGNUP)
    existing_id = uuid.uuid4()
    now = datetime.now(UTC)
    fake_users.users[existing_id] = User(
        id=existing_id, username="ana", email=SIGNUP["email"],
        created_at=now, updated_at=now,
    )
    response = await client.post("/api/v1/auth/signup", json=SIGNUP)
    assert response.status_code == 422
    assert response.json()["detail"] == "User already registered"


async def test_signup_validates_payload(client):
    response = await client.post(
        "/api/v1/auth/signup", json={"email": "no", "password": "short", "username": "a"}
    )
    assert response.status_code == 422


async def test_login_then_refresh_then_logout(fake_auth, client):
    await client.post("/api/v1/auth/signup", json=SIGNUP)

    login = await client.post(
        "/api/v1/auth/login", json={"email": SIGNUP["email"], "password": SIGNUP["password"]}
    )
    assert login.status_code == 200
    session = login.json()

    refreshed = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": session["refresh_token"]}
    )
    assert refreshed.status_code == 200
    assert refreshed.json()["refresh_token"] != session["refresh_token"]

    reused = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": session["refresh_token"]}
    )
    assert reused.status_code == 401

    logout = await client.post(
        "/api/v1/auth/logout", headers={"Authorization": f"Bearer {session['access_token']}"}
    )
    assert logout.status_code == 204
    assert fake_auth.revoked == [session["access_token"]]


async def test_login_wrong_password_is_401(client):
    await client.post("/api/v1/auth/signup", json=SIGNUP)
    response = await client.post(
        "/api/v1/auth/login", json={"email": SIGNUP["email"], "password": "incorrecta"}
    )
    assert response.status_code == 401


async def test_logout_without_token_is_401(client):
    response = await client.post("/api/v1/auth/logout")
    assert response.status_code == 401
