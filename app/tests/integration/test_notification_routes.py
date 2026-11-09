"""Pruebas de integración para generación y aislamiento de notificaciones."""

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


async def test_like_comment_notifications_and_owner_isolation(client):
    owner, actor, stranger = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    owner_headers = {"Authorization": f"Bearer {token_for(owner)}"}
    actor_headers = {"Authorization": f"Bearer {token_for(actor)}"}
    post = await client.post("/api/v1/posts/", json={"content": "post"}, headers=owner_headers)
    post_id = post.json()["id"]

    await client.post(f"/api/v1/posts/{post_id}/like", headers=actor_headers)
    await client.post(f"/api/v1/posts/{post_id}/like", headers=actor_headers)
    await client.delete(f"/api/v1/posts/{post_id}/like", headers=actor_headers)
    await client.post(
        f"/api/v1/posts/{post_id}/comments",
        json={"content": "hola"},
        headers=actor_headers,
    )
    await client.post(f"/api/v1/posts/{post_id}/like", headers=owner_headers)

    notifications = await client.get("/api/v1/notifications/", headers=owner_headers)
    assert notifications.status_code == 200
    rows = notifications.json()
    assert [row["type"] for row in rows] == ["comment", "like"]
    assert rows[0]["comment_content"] == "hola"
    assert rows[0]["actor"]["id"] == str(actor)
    assert rows[0]["post"]["id"] == post_id
    assert rows[1]["comment_content"] is None

    assert (await client.get("/api/v1/notifications/", headers={
        "Authorization": f"Bearer {token_for(stranger)}"
    })).json() == []
    count = await client.get("/api/v1/notifications/unread-count", headers=owner_headers)
    assert count.json() == {"count": 2}
    assert (await client.patch(
        f"/api/v1/notifications/{rows[0]['id']}/read", headers=owner_headers
    )).status_code == 204
    assert (await client.get(
        "/api/v1/notifications/unread-count", headers=owner_headers
    )).json() == {"count": 1}

    forbidden_owner_update = await client.patch(
        f"/api/v1/notifications/{rows[1]['id']}/read",
        headers={"Authorization": f"Bearer {token_for(stranger)}"},
    )
    assert forbidden_owner_update.status_code == 404
    assert (await client.patch("/api/v1/notifications/read-all", headers=owner_headers)).json() == {
        "updated_count": 1
    }


async def test_notifications_require_auth_and_support_pagination(client):
    assert (await client.get("/api/v1/notifications/")).status_code == 401
    assert (await client.get("/api/v1/notifications/unread-count")).status_code == 401
    assert (await client.patch(f"/api/v1/notifications/{uuid.uuid4()}/read")).status_code == 401
    assert (await client.get(
        "/api/v1/notifications/?limit=0",
        headers={"Authorization": f"Bearer {token_for(uuid.uuid4())}"},
    )).status_code == 422
