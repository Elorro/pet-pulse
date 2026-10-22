"""Pruebas de integración para la carga directa de imágenes de publicaciones."""

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_storage_service
from app.application.interfaces.storage_service import SignedUpload, StorageService, StoredObject
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


class FakeStorageService(StorageService):
    def __init__(self) -> None:
        self.paths: list[str] = []
        self.uploaded: set[str] = set()
        self.objects: dict[str, StoredObject] = {}
        self.fail = False

    async def create_signed_upload(self, path: str) -> SignedUpload:
        if self.fail:
            from app.application.interfaces.storage_service import StorageServiceError

            raise StorageServiceError
        self.paths.append(path)
        return SignedUpload(path=path, upload_url=f"https://upload.test/{path}")

    async def exists(self, path: str) -> bool:
        if self.fail:
            from app.application.interfaces.storage_service import StorageServiceError

            raise StorageServiceError
        return path in self.uploaded

    async def get_object(self, path: str) -> StoredObject | None:
        if self.fail:
            from app.application.interfaces.storage_service import StorageServiceError

            raise StorageServiceError
        return self.objects.get(path)

    def public_url(self, path: str) -> str:
        return f"https://media.test/{path}"


@pytest.fixture
def storage():
    service = FakeStorageService()
    app.dependency_overrides[get_storage_service] = lambda: service
    yield service
    app.dependency_overrides.pop(get_storage_service, None)


async def test_media_upload_requires_auth(client, storage):
    response = await client.post("/api/v1/posts/media-uploads", json={"content_type": "image/jpeg"})
    assert response.status_code == 401


async def test_media_upload_validates_type_and_creates_server_path(client, storage):
    user_id = uuid.uuid4()
    headers = {"Authorization": f"Bearer {token_for(user_id)}"}
    bad = await client.post(
        "/api/v1/posts/media-uploads", json={"content_type": "image/svg+xml"}, headers=headers
    )
    assert bad.status_code == 422

    response = await client.post(
        "/api/v1/posts/media-uploads", json={"content_type": "image/webp"}, headers=headers
    )
    assert response.status_code == 201
    path = response.json()["path"]
    assert path.startswith(f"{user_id}/")
    assert path.endswith(".webp")
    assert storage.paths == [path]


async def test_post_media_validation_and_listing(client, storage):
    user_id = uuid.uuid4()
    headers = {"Authorization": f"Bearer {token_for(user_id)}"}
    foreign = f"{uuid.uuid4()}/{uuid.uuid4()}.jpg"
    malformed = f"{user_id}/../image.jpg"
    for path in (foreign, malformed):
        response = await client.post(
            "/api/v1/posts/", json={"content": "hola", "media_path": path}, headers=headers
        )
        assert response.status_code == 422
        assert response.json()["detail"] == "media_path no válido"

    path = f"{user_id}/{uuid.uuid4()}.png"
    missing = await client.post(
        "/api/v1/posts/", json={"content": "hola", "media_path": path}, headers=headers
    )
    assert missing.status_code == 422
    assert missing.json()["detail"] == "La imagen no se ha subido"

    storage.uploaded.add(path)
    created = await client.post(
        "/api/v1/posts/", json={"content": "hola", "media_path": path}, headers=headers
    )
    assert created.status_code == 201
    assert created.json()["media_url"] == f"https://media.test/{path}"
    listed = await client.get("/api/v1/posts/")
    assert listed.json()[0]["media_url"] == f"https://media.test/{path}"


async def test_text_only_post_has_null_media_and_storage_errors_are_502(client, storage):
    user_id = uuid.uuid4()
    headers = {"Authorization": f"Bearer {token_for(user_id)}"}
    created = await client.post("/api/v1/posts/", json={"content": "solo texto"}, headers=headers)
    assert created.status_code == 201
    assert created.json()["media_url"] is None

    storage.fail = True
    failed_upload = await client.post(
        "/api/v1/posts/media-uploads", json={"content_type": "image/gif"}, headers=headers
    )
    assert failed_upload.status_code == 502

    storage.fail = False
    path = f"{user_id}/{uuid.uuid4()}.jpg"
    storage.uploaded.add(path)
    storage.fail = True
    failed_post = await client.post(
        "/api/v1/posts/", json={"content": "con imagen", "media_path": path}, headers=headers
    )
    assert failed_post.status_code == 502


async def test_text_post_works_without_storage_configured(client):
    app.dependency_overrides[get_storage_service] = lambda: None
    user_id = uuid.uuid4()
    headers = {"Authorization": f"Bearer {token_for(user_id)}"}
    created = await client.post("/api/v1/posts/", json={"content": "solo texto"}, headers=headers)
    assert created.status_code == 201

    upload = await client.post(
        "/api/v1/posts/media-uploads", json={"content_type": "image/png"}, headers=headers
    )
    assert upload.status_code == 503
    with_media = await client.post(
        "/api/v1/posts/",
        json={"content": "con imagen", "media_path": f"{user_id}/{uuid.uuid4()}.png"},
        headers=headers,
    )
    assert with_media.status_code == 503
