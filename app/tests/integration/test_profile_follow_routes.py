"""Pruebas de la API de seguimiento unilateral entre perfiles."""

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


async def _profile(client, user_id: uuid.UUID, username: str):
    return await client.get(
        "/api/v1/auth/me",
        headers={
            "Authorization": f"Bearer {token_for(user_id, user_metadata={'username': username})}"
        },
    )


def _headers(user_id: uuid.UUID) -> dict[str, str]:
    return {"Authorization": f"Bearer {token_for(user_id)}"}


async def test_follow_is_idempotent_and_lists_only_authenticated_users_relationships(client):
    follower_id, target_id, third_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    await _profile(client, follower_id, "seguidor")
    await _profile(client, target_id, "seguido")
    await _profile(client, third_id, "tercero")

    first = await client.put(
        f"/api/v1/profiles/{target_id}/follow", headers=_headers(follower_id)
    )
    repeated = await client.put(
        f"/api/v1/profiles/{target_id}/follow", headers=_headers(follower_id)
    )
    await client.put(f"/api/v1/profiles/{third_id}/follow", headers=_headers(follower_id))
    assert first.status_code == repeated.status_code == 200
    assert first.json() == {"profile_id": str(target_id), "following": True, "created": True}
    assert repeated.json() == {
        "profile_id": str(target_id),
        "following": True,
        "created": False,
    }

    own_following = await client.get(
        "/api/v1/profiles/following?limit=1&offset=0", headers=_headers(follower_id)
    )
    next_following = await client.get(
        "/api/v1/profiles/following?limit=1&offset=1", headers=_headers(follower_id)
    )
    assert len(own_following.json()) == len(next_following.json()) == 1
    assert {
        own_following.json()[0]["username"],
        next_following.json()[0]["username"],
    } == {"seguido", "tercero"}
    unrelated_following = await client.get(
        "/api/v1/profiles/following", headers=_headers(third_id)
    )
    assert unrelated_following.json() == []
    target_followers = await client.get(
        "/api/v1/profiles/followers", headers=_headers(target_id)
    )
    assert [profile["username"] for profile in target_followers.json()] == ["seguidor"]
    assert "email" not in target_followers.json()[0]

    status_response = await client.get(
        f"/api/v1/profiles/{target_id}/follow-status", headers=_headers(follower_id)
    )
    assert status_response.json() == {
        "profile_id": str(target_id),
        "following": True,
        "followed_by": False,
    }


async def test_unfollow_is_idempotent_self_follow_and_missing_profile_are_rejected(client):
    user_id, target_id, unknown_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    await _profile(client, user_id, "alfa")
    await _profile(client, target_id, "beta")

    self_follow = await client.put(
        f"/api/v1/profiles/{user_id}/follow", headers=_headers(user_id)
    )
    assert self_follow.status_code == 400

    missing = await client.put(
        f"/api/v1/profiles/{unknown_id}/follow", headers=_headers(user_id)
    )
    assert missing.status_code == 404

    for _ in range(2):
        response = await client.delete(
            f"/api/v1/profiles/{target_id}/follow", headers=_headers(user_id)
        )
        assert response.status_code == 204

    unauthenticated = await client.get("/api/v1/profiles/following")
    assert unauthenticated.status_code == 401


async def test_follow_creates_one_notification_and_self_follow_creates_none(client):
    follower_id, target_id = uuid.uuid4(), uuid.uuid4()
    await _profile(client, follower_id, "seguidor")
    await _profile(client, target_id, "seguido")
    headers = _headers(follower_id)

    created = await client.put(f"/api/v1/profiles/{target_id}/follow", headers=headers)
    repeated = await client.put(f"/api/v1/profiles/{target_id}/follow", headers=headers)
    assert created.json()["created"] is True
    assert repeated.json()["created"] is False

    inbox = await client.get("/api/v1/notifications/", headers=_headers(target_id))
    assert len(inbox.json()) == 1
    row = inbox.json()[0]
    assert row["type"] == "follow"
    assert row["actor"]["id"] == str(follower_id)
    assert row["post"] is None
    assert row["comment_content"] is None

    self_follow = await client.put(f"/api/v1/profiles/{follower_id}/follow", headers=headers)
    assert self_follow.status_code == 400
    follower_inbox = await client.get(
        "/api/v1/notifications/", headers=_headers(follower_id)
    )
    assert len(follower_inbox.json()) == 0

    read = await client.patch(
        f"/api/v1/notifications/{row['id']}/read", headers=_headers(target_id)
    )
    assert read.status_code == 204
    unread = await client.get(
        "/api/v1/notifications/unread-count", headers=_headers(target_id)
    )
    assert unread.json() == {
        "count": 0
    }

