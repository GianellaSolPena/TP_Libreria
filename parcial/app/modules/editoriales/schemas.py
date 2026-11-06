from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.validacion import TextoSinNulo


class EditorialCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: TextoSinNulo = Field(min_length=1)
    pais: TextoSinNulo = Field(min_length=1)


class EditorialUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: TextoSinNulo | None = Field(default=None, min_length=1)
    pais: TextoSinNulo | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def _sin_nulos(self) -> "EditorialUpdate":
        nulos = [c for c in self.model_fields_set if getattr(self, c) is None]
        if nulos:
            raise ValueError(f"campos que no admiten null: {', '.join(nulos)}")
        return self


class EditorialRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    pais: str
