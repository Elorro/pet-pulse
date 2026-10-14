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

    second = await client.get("/api/v1/auth/me", headers=headers)
    assert second.json() == first.json()


async def test_me_falls_back_to_generated_username(client):
    user_id = uuid.uuid4()
    response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token_for(user_id)}"}
    )
    assert response.status_code == 200
    assert response.json()["username"] == f"user_{user_id.hex[:12]}"


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


async def test_create_post_rejects_empty_content(client):
    headers = {"Authorization": f"Bearer {token_for(uuid.uuid4())}"}
    response = await client.post("/api/v1/posts/", json={"content": ""}, headers=headers)
    assert response.status_code == 422
