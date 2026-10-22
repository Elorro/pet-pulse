"""Pruebas de integración de comentarios de publicaciones."""

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


async def test_list_comments_returns_content_date_and_public_author(client):
    user_id = uuid.uuid4()
    headers = {"Authorization": f"Bearer {token_for(user_id)}"}
    post = await client.post("/api/v1/posts/", json={"content": "post"}, headers=headers)
    post_id = post.json()["id"]
    created = await client.post(
        f"/api/v1/posts/{post_id}/comments", json={"content": "¡Qué lindo!"}, headers=headers
    )

    response = await client.get(f"/api/v1/posts/{post_id}/comments")
    assert response.status_code == 200
    assert response.json() == [created.json()]
    assert response.json()[0]["content"] == "¡Qué lindo!"
    assert response.json()[0]["created_at"]
    assert response.json()[0]["author"] == {
        "id": str(user_id),
        "username": f"user_{user_id.hex[:12]}",
    }
    assert "email" not in response.json()[0]["author"]


async def test_create_comment_requires_auth_and_returns_comment(client):
    author_id = uuid.uuid4()
    post = await client.post(
        "/api/v1/posts/",
        json={"content": "post"},
        headers={"Authorization": f"Bearer {token_for(author_id)}"},
    )
    post_id = post.json()["id"]

    unauthenticated = await client.post(
        f"/api/v1/posts/{post_id}/comments", json={"content": "comentario"}
    )
    assert unauthenticated.status_code == 401

    creator_id = uuid.uuid4()
    response = await client.post(
        f"/api/v1/posts/{post_id}/comments",
        json={"content": "comentario"},
        headers={"Authorization": f"Bearer {token_for(creator_id)}"},
    )
    assert response.status_code == 201
    assert response.json()["post_id"] == post_id
    assert response.json()["content"] == "comentario"
    assert response.json()["author"]["id"] == str(creator_id)


async def test_comment_routes_report_missing_post(client):
    missing_id = str(uuid.uuid4())
    listed = await client.get(f"/api/v1/posts/{missing_id}/comments")
    assert listed.status_code == 404

    created = await client.post(
        f"/api/v1/posts/{missing_id}/comments",
        json={"content": "comentario"},
        headers={"Authorization": f"Bearer {token_for(uuid.uuid4())}"},
    )
    assert created.status_code == 404
    assert created.json() == {"detail": "Post not found"}
