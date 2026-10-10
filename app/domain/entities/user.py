from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class User:
    """Representa a un usuario registrado en la red social de mascotas.

    Attributes:
        id: Identificador único universal del usuario.
        username: Nombre de usuario público.
        email: Correo electrónico del usuario.
        hashed_password: Contraseña cifrada con bcrypt.
        created_at: Fecha y hora de creación del registro.
        updated_at: Fecha y hora de la última actualización del registro.
    """

    id: UUID
    username: str
    email: str
    hashed_password: str
    created_at: datetime
    updated_at: datetime
