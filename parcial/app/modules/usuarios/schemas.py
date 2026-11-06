from datetime import UTC, datetime
from typing import Annotated, Literal

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
)

from app.core.security import PasswordBcrypt
from app.core.validacion import TextoSinNulo, rechazar_nulo
from app.modules.usuarios.models import Rol


def _normalizar_email(valor: str) -> str:
    return valor.strip().lower()


# Mismo patron que clientes/schemas.py; se recorta y pasa a minusculas para que
# Ana@Example.com y ana@example.com no sean dos cuentas ni dos contadores.
Email = Annotated[
    str,
    AfterValidator(rechazar_nulo),
    StringConstraints(min_length=3, max_length=254, pattern=r"^[^@\s]+@[^@\s]+$"),
    AfterValidator(_normalizar_email),
]


class RegistroIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: Email
    nombre: TextoSinNulo = Field(min_length=1, max_length=120)
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


# Un CLIENTE nace por /auth/registro con su ficha (RN-02): el alta de personal solo admite estos dos.
RolPersonal = Literal[Rol.VENDEDOR, Rol.ADMIN]


def _exigir_futuro(valor: datetime | None) -> datetime | None:
    if valor is not None and valor <= datetime.now(UTC):
        raise ValueError("vence_en debe ser una fecha futura")
    return valor


class PersonalIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: Email
    nombre: TextoSinNulo = Field(min_length=1, max_length=120)
    password: PasswordBcrypt
    rol: RolPersonal


class AsignarRolIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rol: Rol
    # AwareDatetime rechaza la fecha sin zona (422); timestamptz la normaliza a UTC.
    vence_en: Annotated[AwareDatetime | None, AfterValidator(_exigir_futuro)] = None


class AsignacionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    usuario_id: int
    rol: Rol
    desde: datetime
    vence_en: datetime | None
    revocada_en: datetime | None
    otorgada_por: int | None
    vigente: bool


class EventoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cuando: datetime
    actor: str
    accion: str
