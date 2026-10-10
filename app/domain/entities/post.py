from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class Post:
    """Representa una publicación del foro en el MVP de la red social.

    Attributes:
        id: Identificador único universal de la publicación.
        author_id: Identificador del usuario que creó la publicación.
        content: Contenido textual de la publicación.
        created_at: Fecha y hora de creación de la publicación.
        updated_at: Fecha y hora de la última edición de la publicación.
    """

    id: UUID
    author_id: UUID
    content: str
    created_at: datetime
    updated_at: datetime
