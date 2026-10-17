"""Puerto para almacenamiento de imágenes.

El navegador sube directamente porque los cuerpos de funciones de Vercel
están limitados a unos 4,5 MB y así el archivo no se transmite dos veces.
Este puerto permite migrar después a PUTs firmados de R2 o S3 escribiendo
un adaptador nuevo.
"""

import abc
from dataclasses import dataclass


class StorageServiceError(Exception):
    """Error al solicitar o consultar un objeto del almacenamiento."""


@dataclass(frozen=True)
class SignedUpload:
    """URL firmada para subir un objeto a una ruta fija."""

    path: str
    upload_url: str


class StorageService(abc.ABC):
    @abc.abstractmethod
    async def create_signed_upload(self, path: str) -> SignedUpload:
        raise NotImplementedError

    @abc.abstractmethod
    async def exists(self, path: str) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    def public_url(self, path: str) -> str:
        raise NotImplementedError
