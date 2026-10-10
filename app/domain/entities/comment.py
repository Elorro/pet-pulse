from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class Comment:
    """Representa un comentario hecho en una publicación del foro.

    Attributes:
        id: Identificador único universal del comentario.
        post_id: Identificador de la publicación a la que pertenece el comentario.
        author_id: Identificador del usuario que escribió el comentario.
        content: Contenido textual del comentario.
        created_at: Fecha y hora de creación del comentario.
        updated_at: Fecha y hora de la última edición del comentario.
    """

    id: UUID
    post_id: UUID
    author_id: UUID
    content: str
    created_at: datetime
    updated_at: datetime
