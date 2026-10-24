"""Pruebas de integración de los endpoints protegidos con Supabase Auth.

Se sustituye el verificador real por uno que confía en una clave de prueba,
y se usa SQLite en disco para no depender de Postgres.
"""

import time
import uuid

import jwt
import pytest_asyncio
from cryptography.hazmat.primitives.asymmetric import ec
from httpx import ASGITransport, AsyncClient

from app.core.auth import AuthUser, InvalidTokenError, get_token_verifier
from app.infrastructure.db.base import Base
from app.infrastructure.db.session import engine
from app.infrastructure.repositories.sqlalchemy_user_repository import (
    SQLAlchemyUserRepository,
)
from app.main import app

TEST_KEY = ec.generate_private_key(ec.SECP256R1())
ISSUER = "https://test-project.supabase.co/auth/v1"


class FakeVerifier:
    """Verifica tokens firmados con la clave de prueba sin consultar JWKS."""

    def verify(self, token: str) -> AuthUser:
        try:
            claims = jwt.decode(
                token, TEST_KEY.public_key(), algorithms=["ES256"],
                audience="authenticated", issuer=ISSUER,
            )
        except jwt.PyJWTError as exc:
            raise InvalidTokenError(str(exc)) from exc
        return AuthUser(
            id=uuid.UUID(claims["sub"]), email=claims.get("email"),
            role=claims.get("role", "authenticated"), claims=claims,
        )


def token_for(user_id: uuid.UUID, username: str | None = None, **extra) -> str:
    now = int(time.time())
    claims = {
        "sub": str(user_id), "email": f"{user_id.hex[:6]}@example.com",
        "role": "authenticated", "aud": "authenticated", "iss": ISSUER,
        "iat": now, "exp": now + 3600,
    }
    if username:
        claims["user_metadata"] = {"username": username}
    claims.update(extra)
    return jwt.encode(claims, TEST_KEY, algorithm="ES256")


@pytest_asyncio.fixture
async def client():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    app.dependency_overrides[get_token_verifier] = lambda: FakeVerifier()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def test_me_without_token_is_401(client):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


async def test_me_with_bad_token_is_401(client):
    response = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer nope"})
    assert response.status_code == 401


async def test_me_creates_profile_on_first_call(client):
    user_id = uuid.uuid4()
    headers = {"Authorization": f"Bearer {token_for(user_id, username='pepe')}"}

    first = await client.get("/api/v1/auth/me", headers=headers)
    assert first.status_code == 200
    assert first.json()["id"] == str(user_id)
    assert first.json()["username"] == "pepe"
    assert first.json()["full_name"] is None
    assert first.json()["photo_url"] is None

    second = await client.get("/api/v1/auth/me", headers=headers)
    assert second.json() == first.json()


async def test_me_returns_profile_name_and_photo_from_authenticated_user(client):
    user_id = uuid.uuid4()
    access_token = token_for(
        user_id,
        user_metadata={
            "username": "ana",
            "full_name": "Ana Pérez",
            "photo_url": "https://cdn.example.com/ana.jpg",
        },
    )
    headers = {"Authorization": f"Bearer {access_token}"}

    response = await client.get("/api/v1/auth/me", headers=headers)

    assert response.status_code == 200
    assert response.json()["id"] == str(user_id)
    assert response.json()["username"] == "ana"
    assert response.json()["full_name"] == "Ana Pérez"
    assert response.json()["photo_url"] == "https://cdn.example.com/ana.jpg"


async def test_me_does_not_accept_an_arbitrary_user_id(client):
    response = await client.get(
        f"/api/v1/auth/me/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token_for(uuid.uuid4())}"},
    )
    assert response.status_code == 404


async def test_me_falls_back_to_generated_username(client):
    user_id = uuid.uuid4()
    response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token_for(user_id)}"}
    )
    assert response.status_code == 200
    assert response.json()["username"] == f"user_{user_id.hex[:12]}"


async def test_me_recovers_when_username_is_claimed_before_insert(client):
    first_id, second_id = uuid.uuid4(), uuid.uuid4()
    first = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token_for(first_id, username='same-name')}"},
    )
    second = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token_for(second_id, username='same-name')}"},
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["username"] == f"user_{second_id.hex}"


async def test_me_is_409_when_email_belongs_to_another_profile(client):
    first_id, second_id = uuid.uuid4(), uuid.uuid4()
    first = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token_for(first_id, email='dup@example.com')}"},
    )
    second = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token_for(second_id, email='dup@example.com')}"},
    )
    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["detail"] == "El correo ya está asociado a otro perfil"


async def test_me_is_409_when_email_is_claimed_before_insert(client, monkeypatch):
    first_id, second_id = uuid.uuid4(), uuid.uuid4()
    await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token_for(first_id, email='dup@example.com')}"},
    )

    # Simula la carrera: la comprobación previa no ve el correo, el INSERT sí choca.
    original = SQLAlchemyUserRepository.get_by_email
    calls = 0

    async def racy_get_by_email(self, email):
        nonlocal calls
        calls += 1
        return None if calls == 1 else await original(self, email)

    monkeypatch.setattr(SQLAlchemyUserRepository, "get_by_email", racy_get_by_email)
    second = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token_for(second_id, email='dup@example.com')}"},
    )
    assert second.status_code == 409
    assert second.json()["detail"] == "El correo ya está asociado a otro perfil"


async def test_create_post_requires_auth(client):
    response = await client.post("/api/v1/posts/", json={"content": "hola"})
    assert response.status_code == 401


async def test_create_post_then_list(client):
    user_id = uuid.uuid4()
    headers = {"Authorization": f"Bearer {token_for(user_id, username='ana')}"}

    created = await client.post(
        "/api/v1/posts/", json={"content": "Mi perro Toby"}, headers=headers
    )
    assert created.status_code == 201
    assert created.json()["author_id"] == str(user_id)

    listed = await client.get("/api/v1/posts/")
    assert listed.status_code == 200
    assert [p["content"] for p in listed.json()] == ["Mi perro Toby"]


async def test_like_post_updates_counts(client):
    headers = {"Authorization": f"Bearer {token_for(uuid.uuid4(), username='ana')}"}
    created = await client.post(
        "/api/v1/posts/", json={"content": "Mi perro Toby"}, headers=headers
    )
    post_id = created.json()["id"]

    fetched = await client.get(f"/api/v1/posts/{post_id}")
    assert fetched.status_code == 200
    assert fetched.json()["like_count"] == 0

    for _ in range(2):
        liked = await client.post(f"/api/v1/posts/{post_id}/like", headers=headers)
        assert liked.status_code == 200
        assert liked.json()["like_count"] == 1

    assert (await client.get(f"/api/v1/posts/{post_id}")).json()["like_count"] == 1
    assert (await client.get("/api/v1/posts/")).json()[0]["like_count"] == 1


async def test_get_missing_post_is_404(client):
    response = await client.get(f"/api/v1/posts/{uuid.uuid4()}")
    assert response.status_code == 404


async def test_create_post_rejects_empty_content(client):
    headers = {"Authorization": f"Bearer {token_for(uuid.uuid4())}"}
    response = await client.post("/api/v1/posts/", json={"content": ""}, headers=headers)
    assert response.status_code == 422
