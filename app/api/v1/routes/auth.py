"""Router y esquemas para autenticación de usuarios.

Define el endpoint POST /register para crear una cuenta de usuario,
aplicando validación estricta de Pydantic, hash de contraseña mediante bcrypt
y exclusión de credenciales en las respuestas.
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, EmailStr, Field

from app.api.deps import get_user_repository
from app.core.security import hash_password
from app.domain.entities.user import User
from app.domain.repositories.user_repository import UserRepository


router = APIRouter(prefix="/auth", tags=["auth"])


class UserCreate(BaseModel):
    """Esquema de entrada para registrar un nuevo usuario.

    Valida los campos obligatorios con restricciones de longitud y formato.
    """

    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class UserResponse(BaseModel):
    """Esquema de salida con datos seguros del usuario registrado.

    Excluye `hashed_password` para no exponer credenciales en la API.
    """

    id: uuid.UUID
    username: str
    email: EmailStr
    created_at: datetime


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar usuario",
    description="Crea una cuenta de usuario con contraseña hasheada con bcrypt.",
)
async def register(
    payload: UserCreate,
    user_repo: UserRepository = Depends(get_user_repository),
) -> UserResponse:
    """Registra un nuevo usuario en el sistema.

    Args:
        payload: Datos validados para la creación del usuario.
        user_repo: Repositorio de usuarios inyectado.

    Returns:
        Objeto `UserResponse` con los datos públicos del usuario creado.
    """
    user = User(
        id=uuid.uuid4(),
        username=payload.username,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        created_at=datetime.utcnow(),
    )
    await user_repo.save(user)
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        created_at=user.created_at,
    )
