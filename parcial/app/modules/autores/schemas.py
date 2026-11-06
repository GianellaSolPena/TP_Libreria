from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.validacion import TextoSinNulo


class AutorCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: TextoSinNulo = Field(min_length=1)
    nacionalidad: TextoSinNulo = Field(min_length=1)


class AutorUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: TextoSinNulo | None = Field(default=None, min_length=1)
    nacionalidad: TextoSinNulo | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def _sin_nulos(self) -> "AutorUpdate":
        nulos = [c for c in self.model_fields_set if getattr(self, c) is None]
        if nulos:
            raise ValueError(f"campos que no admiten null: {', '.join(nulos)}")
        return self


class AutorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    nacionalidad: str
