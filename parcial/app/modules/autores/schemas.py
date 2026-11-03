from decimal import Decimal

from pydantic import AliasPath, BaseModel, ConfigDict, Field, model_validator


class AutorCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=1)
    nacionalidad: str = Field(min_length=1)


class AutorUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str | None = Field(default=None, min_length=1)
    nacionalidad: str | None = Field(default=None, min_length=1)

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


class AutorLibroRead(BaseModel):
    """Un libro del autor, con el rol y el orden de la autoría."""

    model_config = ConfigDict(from_attributes=True)

    libro_id: int
    isbn: str = Field(validation_alias=AliasPath("libro", "isbn"))
    titulo: str = Field(validation_alias=AliasPath("libro", "titulo"))
    precio: Decimal = Field(validation_alias=AliasPath("libro", "precio"))
    rol: str
    orden: int
