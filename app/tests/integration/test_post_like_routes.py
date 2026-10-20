"""Pruebas de integración para consultar y quitar likes."""

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
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as test_client:
        yield test_client
    app.dependency_overrides.clear()


async def test_get_like_requires_auth_and_reports_user_state(client):
    author_id, liker_id, other_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    post = await client.post(
        "/api/v1/posts/",
        json={"content": "hola"},
        headers={"Authorization": f"Bearer {token_for(author_id)}"},
    )
    post_id = post.json()["id"]

    assert (await client.get(f"/api/v1/posts/{post_id}/like")).status_code == 401
    for user_id in (liker_id, other_id):
        await client.post(
            f"/api/v1/posts/{post_id}/like",
            headers={"Authorization": f"Bearer {token_for(user_id)}"},
        )

    response = await client.get(
        f"/api/v1/posts/{post_id}/like",
        headers={"Authorization": f"Bearer {token_for(liker_id)}"},
    )
    assert response.status_code == 200
    assert response.json() == {"post_id": post_id, "like_count": 2, "liked": True}

    unliked_user = await client.get(
        f"/api/v1/posts/{post_id}/like",
        headers={"Authorization": f"Bearer {token_for(author_id)}"},
    )
    assert unliked_user.json() == {"post_id": post_id, "like_count": 2, "liked": False}


async def test_delete_like_is_idempotent_and_only_removes_requesting_user(client):
    author_id, liker_id, other_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    headers = {"Authorization": f"Bearer {token_for(author_id)}"}
    post = await client.post("/api/v1/posts/", json={"content": "hola"}, headers=headers)
    post_id = post.json()["id"]

    for user_id in (liker_id, other_id):
        await client.post(
            f"/api/v1/posts/{post_id}/like",
            headers={"Authorization": f"Bearer {token_for(user_id)}"},
        )

    liker_headers = {"Authorization": f"Bearer {token_for(liker_id)}"}
    removed = await client.delete(f"/api/v1/posts/{post_id}/like", headers=liker_headers)
    repeated = await client.delete(f"/api/v1/posts/{post_id}/like", headers=liker_headers)
    assert removed.status_code == repeated.status_code == 200
    assert removed.json() == repeated.json() == {
        "post_id": post_id,
        "like_count": 1,
        "liked": False,
    }

    still_liked = await client.get(
        f"/api/v1/posts/{post_id}/like",
        headers={"Authorization": f"Bearer {token_for(other_id)}"},
    )
    assert still_liked.json() == {"post_id": post_id, "like_count": 1, "liked": True}

    absent = str(uuid.uuid4())
    missing = await client.delete(f"/api/v1/posts/{absent}/like", headers=liker_headers)
    assert missing.status_code == 404
