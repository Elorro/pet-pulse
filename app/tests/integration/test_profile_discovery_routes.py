"""Pruebas de búsqueda y resolución pública de perfiles autenticadas."""

import uuid

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.auth import get_token_verifier
from app.infrastructure.db.base import Base
from app.infrastructure.db.session import engine
from app.main import app
from app.tests.integration.test_auth_routes import FakeVerifier, token_for


@pytest_asyncio.fixture
async def client():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    app.dependency_overrides[get_token_verifier] = lambda: FakeVerifier()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def _create_profile(client, user_id: uuid.UUID, username: str, full_name: str):
    metadata = {"username": username, "full_name": full_name}
    return await client.get(
        "/api/v1/auth/me",
        headers={
            "Authorization": f"Bearer {token_for(user_id, user_metadata=metadata)}"
        },
    )


async def test_search_is_authenticated_private_fields_hidden_and_paginated(client):
    await _create_profile(client, uuid.uuid4(), "luna", "Luna Pérez")
    await _create_profile(client, uuid.uuid4(), "luna2", "Otra Persona")
    await _create_profile(client, uuid.uuid4(), "sol", "Luna García")
    headers = {"Authorization": f"Bearer {token_for(uuid.uuid4())}"}

    first = await client.get("/api/v1/profiles/search?q=lUnA&limit=1&offset=0", headers=headers)
    second = await client.get("/api/v1/profiles/search?q=lUna&limit=1&offset=1", headers=headers)
    assert first.status_code == second.status_code == 200
    assert first.json()[0]["username"] == "luna"
    assert second.json()[0]["username"] == "luna2"
    assert set(first.json()[0]) == {"id", "username", "full_name", "photo_url"}
    assert "email" not in first.text
    assert (await client.get("/api/v1/profiles/search?q=luna")).status_code == 401


async def test_username_lookup_returns_profile_without_posts(client):
    user_id = uuid.uuid4()
    await _create_profile(client, user_id, "perfil-vacio", "Perfil sin publicaciones")
    headers = {"Authorization": f"Bearer {token_for(uuid.uuid4())}"}

    response = await client.get("/api/v1/profiles/username/perfil-vacio", headers=headers)
    assert response.status_code == 200
    assert response.json() == {
        "id": str(user_id),
        "username": "perfil-vacio",
        "full_name": "Perfil sin publicaciones",
        "photo_url": None,
    }
    missing = await client.get("/api/v1/profiles/username/no-existe", headers=headers)
    assert missing.status_code == 404
