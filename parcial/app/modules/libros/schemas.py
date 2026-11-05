from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Rol = Literal["autor", "coautor", "traductor", "ilustrador"]

INT4_MAX = 2**31 - 1
# Ids, cantidades y órdenes dentro de int4: un valor mayor nunca debe llegar a la base.
IdInt4 = Annotated[int, Field(ge=1, le=INT4_MAX)]
Precio = Annotated[Decimal, Field(gt=0, max_digits=10, decimal_places=2)]


class LibroAutorCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    autor_id: IdInt4
    rol: Rol
    orden: IdInt4


class LibroCreate(BaseModel):
    """El stock no viaja: se crea con `stock_inicial` y su movimiento (RN-01, RN-11)."""

    model_config = ConfigDict(extra="forbid")

    isbn: str = Field(min_length=1)
    titulo: str = Field(min_length=1)
    precio: Precio
    stock_inicial: int = Field(ge=0, le=INT4_MAX)
    editorial_id: IdInt4
    genero_id: IdInt4 | None = None
    autores: list[LibroAutorCreate] = Field(min_length=1)

    @model_validator(mode="after")
    def _autores_sin_repetir(self) -> "LibroCreate":
        ids = [a.autor_id for a in self.autores]
        if len(ids) != len(set(ids)):
            raise ValueError("autores no puede repetir autor_id")
        return self


class LibroUpdate(BaseModel):
    """Sólo título y precio (PDF Ej. 3; QA-05)."""

    model_config = ConfigDict(extra="forbid")

    titulo: str | None = Field(default=None, min_length=1)
    precio: Precio | None = None

    @model_validator(mode="after")
    def _sin_nulos(self) -> "LibroUpdate":
        nulos = [c for c in self.model_fields_set if getattr(self, c) is None]
        if nulos:
            raise ValueError(f"campos que no admiten null: {', '.join(nulos)}")
        return self


class ReponerIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cantidad: int = Field(ge=1, le=INT4_MAX)


class EditorialResumen(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    pais: str


class GeneroResumen(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str


class AutorResumen(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    nacionalidad: str


class AutoriaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    autor: AutorResumen
    rol: str
    orden: int


class LibroRead(BaseModel):
    """Listado: libro con su editorial y género."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    isbn: str
    titulo: str
    precio: Decimal
    stock: int
    editorial: EditorialResumen
    genero: GeneroResumen | None = None


class LibroDetalleRead(LibroRead):
    """Detalle: suma la lista de autorías (autor + rol + orden)."""

    autorias: list[AutoriaRead]


class MovimientoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cantidad: int
    motivo: str
    cuando: datetime
    venta_id: int | None = None
    usuario_id: int


class ReposicionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    libro: LibroRead
    movimiento: MovimientoRead
