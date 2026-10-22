"""Pruebas de integración de comentarios de publicaciones."""

import uuid

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_storage_service
from app.application.interfaces.storage_service import SignedUpload, StorageService, StoredObject
from app.core.auth import get_token_verifier
from app.infrastructure.db.base import Base
from app.infrastructure.db.session import engine
from app.main import app
from app.tests.integration.test_auth_routes import FakeVerifier, token_for


class FakeStorage(StorageService):
    def __init__(self):
        self.objects: dict[str, StoredObject] = {}

    async def create_signed_upload(self, path: str) -> SignedUpload:
        return SignedUpload(path, f"https://upload.test/{path}")

    async def exists(self, path: str) -> bool:
        return path in self.objects

    async def get_object(self, path: str) -> StoredObject | None:
        return self.objects.get(path)

    def public_url(self, path: str) -> str:
        return f"https://media.test/{path}"


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


async def test_comment_media_upload_validates_type_and_size_and_returns_owned_path(client):
    storage = FakeStorage()
    app.dependency_overrides[get_storage_service] = lambda: storage
    user_id = uuid.uuid4()
    headers = {"Authorization": f"Bearer {token_for(user_id)}"}
    unauthorized = await client.post(
        "/api/v1/posts/comment-media-uploads",
        json={"content_type": "image/gif", "file_size_bytes": 12},
    )
    assert unauthorized.status_code == 401
    for payload in (
        {"content_type": "image/svg+xml", "file_size_bytes": 12},
        {"content_type": "image/jpeg", "file_size_bytes": 5 * 1024 * 1024 + 1},
        {"content_type": "image/png", "file_size_bytes": 0},
    ):
        invalid = await client.post(
            "/api/v1/posts/comment-media-uploads", json=payload, headers=headers
        )
        assert invalid.status_code == 422

    uploaded = await client.post(
        "/api/v1/posts/comment-media-uploads",
        json={"content_type": "image/gif", "file_size_bytes": 1024},
        headers=headers,
    )
    assert uploaded.status_code == 201
    path = uploaded.json()["path"]
    assert path.startswith(f"{user_id}/") and path.endswith(".gif")


async def test_comment_media_association_checks_owner_metadata_and_returns_url(client):
    storage = FakeStorage()
    app.dependency_overrides[get_storage_service] = lambda: storage
    author_id = uuid.uuid4()
    headers = {"Authorization": f"Bearer {token_for(author_id)}"}
    post = await client.post(
        "/api/v1/posts/", json={"content": "post"}, headers=headers
    )
    post_id = post.json()["id"]
    own_path = f"{author_id}/{uuid.uuid4()}.png"
    foreign_path = f"{uuid.uuid4()}/{uuid.uuid4()}.png"
    arbitrary_path = f"{author_id}/../../bad.png"
    for path in (foreign_path, arbitrary_path):
        response = await client.post(
            f"/api/v1/posts/{post_id}/comments",
            json={"content": "con medio", "media_path": path},
            headers=headers,
        )
        assert response.status_code == 422

    missing = await client.post(
        f"/api/v1/posts/{post_id}/comments",
        json={"content": "con medio", "media_path": own_path},
        headers=headers,
    )
    assert missing.status_code == 422
    storage.objects[own_path] = StoredObject(5 * 1024 * 1024 + 1, "image/png")
    too_large = await client.post(
        f"/api/v1/posts/{post_id}/comments",
        json={"content": "con medio", "media_path": own_path},
        headers=headers,
    )
    assert too_large.status_code == 422
    storage.objects[own_path] = StoredObject(42, "image/jpeg")
    wrong_type = await client.post(
        f"/api/v1/posts/{post_id}/comments",
        json={"content": "con medio", "media_path": own_path},
        headers=headers,
    )
    assert wrong_type.status_code == 422

    storage.objects[own_path] = StoredObject(42, "image/png")
    created = await client.post(
        f"/api/v1/posts/{post_id}/comments",
        json={"content": "con medio", "media_path": own_path},
        headers=headers,
    )
    assert created.status_code == 201
    assert created.json()["media_url"] == f"https://media.test/{own_path}"
    assert "media" not in created.json()

    text_only = await client.post(
        f"/api/v1/posts/{post_id}/comments",
        json={"content": "solo texto"},
        headers=headers,
    )
    assert text_only.status_code == 201
    assert text_only.json()["media_url"] is None
    listed = await client.get(f"/api/v1/posts/{post_id}/comments")
    assert listed.json()[0]["media_url"] == f"https://media.test/{own_path}"
