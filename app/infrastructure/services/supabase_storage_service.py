"""Adaptador de almacenamiento de objetos sobre Supabase Storage."""

import logging

from storage3.exceptions import StorageApiError, StorageException

from app.application.interfaces.storage_service import (
    SignedUpload,
    StorageService,
    StorageServiceError,
    StoredObject,
)
from supabase import acreate_client

logger = logging.getLogger(__name__)


class SupabaseStorageService(StorageService):
    def __init__(self, supabase_url: str, service_role_key: str, bucket: str) -> None:
        if not supabase_url or not service_role_key or not bucket:
            raise ValueError(
                "SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY y SUPABASE_MEDIA_BUCKET son obligatorios"
            )
        self._url = supabase_url
        self._service_role_key = service_role_key
        self._bucket = bucket

    async def _client(self):
        return await acreate_client(self._url, self._service_role_key)

    async def create_signed_upload(self, path: str) -> SignedUpload:
        try:
            client = await self._client()
            result = await client.storage.from_(self._bucket).create_signed_upload_url(path)
            return SignedUpload(path=path, upload_url=result["signed_url"])
        except (StorageException, StorageApiError) as exc:
            logger.warning("Supabase Storage rechazó la firma de carga (%s)", type(exc).__name__)
            raise StorageServiceError("No se pudo firmar la carga") from exc

    async def exists(self, path: str) -> bool:
        try:
            client = await self._client()
            return await client.storage.from_(self._bucket).exists(path)
        except (StorageException, StorageApiError) as exc:
            logger.warning(
                "Supabase Storage rechazó la consulta del objeto (%s)", type(exc).__name__
            )
            raise StorageServiceError("No se pudo consultar el objeto") from exc

    async def get_object(self, path: str) -> StoredObject | None:
        try:
            client = await self._client()
            info = await client.storage.from_(self._bucket).info(path)
            metadata = info.get("metadata")
            if not isinstance(metadata, dict):
                metadata = {}
            size = info.get("size", metadata.get("size"))
            content_type = (
                info.get("mimetype")
                or metadata.get("mimetype")
                or metadata.get("contentType")
                or metadata.get("content_type")
            )
            if size is None:
                return None
            return StoredObject(size_bytes=int(size), content_type=content_type)
        except (StorageException, StorageApiError) as exc:
            if getattr(exc, "status", None) == 404 or getattr(exc, "status_code", None) == 404:
                return None
            logger.warning("Supabase Storage rechazó la metadata (%s)", type(exc).__name__)
            raise StorageServiceError("No se pudo consultar la metadata") from exc

    def public_url(self, path: str) -> str:
        return f"{self._url.rstrip('/')}/storage/v1/object/public/{self._bucket}/{path}"
