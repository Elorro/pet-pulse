"""Pruebas unitarias del adaptador de Supabase Storage sin red."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from storage3.exceptions import StorageApiError

from app.application.interfaces.storage_service import StorageServiceError
from app.infrastructure.services import supabase_storage_service as module
from app.infrastructure.services.supabase_storage_service import SupabaseStorageService


@pytest.mark.parametrize(
    ("url", "key", "bucket"),
    [
        ("", "secret", "bucket"),
        ("https://example.test", "", "bucket"),
        ("https://example.test", "secret", ""),
    ],
)
def test_constructor_requires_all_values(url, key, bucket):
    with pytest.raises(ValueError):
        SupabaseStorageService(url, key, bucket)


def test_public_url_strips_trailing_slash():
    service = SupabaseStorageService("https://example.test/", "secret", "post-media")
    assert service.public_url("abc/image.jpg") == (
        "https://example.test/storage/v1/object/public/post-media/abc/image.jpg"
    )


@pytest.mark.asyncio
async def test_storage_sdk_error_is_translated(monkeypatch):
    bucket = MagicMock()
    bucket.create_signed_upload_url = AsyncMock(side_effect=StorageApiError("failed", "400", 400))
    client = MagicMock()
    client.storage.from_.return_value = bucket
    monkeypatch.setattr(module, "acreate_client", AsyncMock(return_value=client))
    service = SupabaseStorageService("https://example.test", "secret", "post-media")
    with pytest.raises(StorageServiceError):
        await service.create_signed_upload("user/image.jpg")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "metadata",
    [
        {"mimetype": "image/jpeg", "size": 123},
        {"contentType": "image/png", "size": 234},
    ],
)
async def test_get_object_reads_mime_and_size_from_storage_metadata(monkeypatch, metadata):
    bucket = MagicMock()
    bucket.info = AsyncMock(return_value={"metadata": metadata})
    client = MagicMock()
    client.storage.from_.return_value = bucket
    monkeypatch.setattr(module, "acreate_client", AsyncMock(return_value=client))
    service = SupabaseStorageService("https://example.test", "secret", "post-media")

    obj = await service.get_object("user/image.jpg")

    assert obj is not None
    assert obj.size_bytes == metadata["size"]
    assert obj.content_type in {"image/jpeg", "image/png"}
