from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, StringConstraints

from app.core.security import PasswordBcrypt
from app.modules.usuarios.models import Rol


def _normalizar_email(valor: str) -> str:
    return valor.strip().lower()


# Mismo patron que clientes/schemas.py; se recorta y pasa a minusculas para que
# Ana@Example.com y ana@example.com no sean dos cuentas ni dos contadores.
Email = Annotated[
    str,
    StringConstraints(min_length=3, pattern=r"^[^@\s]+@[^@\s]+$"),
    AfterValidator(_normalizar_email),
]


class RegistroIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: Email
    nombre: str
    password: PasswordBcrypt


class LoginIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: Email
    password: PasswordBcrypt


class CambiarPasswordIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    password_actual: PasswordBcrypt
    password_nueva: PasswordBcrypt


class UsuarioRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    nombre: str
    activo: bool
    debe_cambiar_password: bool


class LoginOut(BaseModel):
    mensaje: str
    debe_cambiar_password: bool
    expira_en_segundos: int


class YoOut(BaseModel):
    usuario: UsuarioRead
    roles_vigentes: list[Rol]
    roles_token: list[str]


class MensajeOut(BaseModel):
    mensaje: str
