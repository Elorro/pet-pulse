from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class User:
    """Perfil público de un usuario autenticado mediante Supabase Auth.

    Las credenciales viven en Supabase (`auth.users`); aquí solo se guarda
    el perfil de la aplicación, cuyo `id` coincide con el UUID de Supabase.

    Attributes:
        id: UUID del usuario en Supabase Auth.
        username: Nombre de usuario público.
        email: Correo electrónico, si el proveedor de identidad lo expone.
        created_at: Fecha y hora de creación del perfil.
        updated_at: Fecha y hora de la última actualización del perfil.
    """

    id: UUID
    username: str
    email: str | None
    created_at: datetime
    updated_at: datetime
    full_name: str | None = None
    photo_url: str | None = None
