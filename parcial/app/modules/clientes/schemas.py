from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from app.core.validacion import Email, TextoSinNulo


class ClienteCreate(BaseModel):
    """`usuario_id` no viaja: el vínculo con un usuario sólo lo crea el registro (C-05)."""

    model_config = ConfigDict(extra="forbid")

    nombre: TextoSinNulo = Field(min_length=1)
    email: Email


class ClienteUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: TextoSinNulo | None = Field(default=None, min_length=1)
    email: Email | None = None

    @model_validator(mode="after")
    def _sin_nulos(self) -> "ClienteUpdate":
        nulos = [c for c in self.model_fields_set if getattr(self, c) is None]
        if nulos:
            raise ValueError(f"campos que no admiten null: {', '.join(nulos)}")
        return self


class PerfilCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    telefono: TextoSinNulo | None = None
    direccion: TextoSinNulo | None = None


class PerfilRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cliente_id: int
    telefono: str | None = None
    direccion: str | None = None


class ClienteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    email: str
    perfil: PerfilRead | None = None
