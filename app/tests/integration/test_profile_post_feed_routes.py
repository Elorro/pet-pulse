"""Pruebas del feed público de publicaciones por username."""

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
    metadata = {
        "username": username,
        "full_name": full_name,
        "photo_url": f"https://cdn.example/{username}.jpg",
    }
    return await client.get(
        "/api/v1/auth/me",
        headers={
            "Authorization": f"Bearer {token_for(user_id, user_metadata=metadata)}"
        },
    )


async def _create_post(client, user_id: uuid.UUID, content: str):
    return await client.post(
        "/api/v1/posts/",
        json={"content": content},
        headers={"Authorization": f"Bearer {token_for(user_id)}"},
    )


async def test_profile_feed_is_public_filtered_paginated_and_has_public_author(client):
    owner_id, other_id = uuid.uuid4(), uuid.uuid4()
    profile = await _create_profile(client, owner_id, "luna", "Luna Pérez")
    assert profile.status_code == 200
    await _create_profile(client, other_id, "sol", "Sol García")
    await _create_post(client, owner_id, "primera")
    await _create_post(client, owner_id, "segunda")
    await _create_post(client, other_id, "ajena")

    page = await client.get("/api/v1/posts/by-username/luna?limit=1&offset=0")
    assert page.status_code == 200
    assert len(page.json()) == 1
    assert page.json()[0]["content"] == "segunda"
    assert page.json()[0]["author"] == {
        "id": str(owner_id),
        "username": "luna",
        "full_name": "Luna Pérez",
        "photo_url": "https://cdn.example/luna.jpg",
    }
    assert "email" not in page.json()[0]["author"]
    next_page = await client.get("/api/v1/posts/by-username/luna?limit=1&offset=1")
    assert next_page.json()[0]["content"] == "primera"

    community = await client.get("/api/v1/posts/")
    assert {post["content"] for post in community.json()} == {"primera", "segunda", "ajena"}


async def test_missing_profile_is_404_and_existing_empty_profile_returns_empty_list(client):
    missing = await client.get("/api/v1/posts/by-username/no-existe")
    assert missing.status_code == 404

    user_id = uuid.uuid4()
    await _create_profile(client, user_id, "sin-posts", "Perfil vacío")
    empty = await client.get("/api/v1/posts/by-username/sin-posts")
    assert empty.status_code == 200
    assert empty.json() == []
