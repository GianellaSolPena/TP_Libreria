from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import AliasPath, BaseModel, ConfigDict, computed_field, model_validator
from pydantic import Field as PydanticField

INT4_MAX = 2**31 - 1
IdInt4 = Annotated[int, PydanticField(ge=1, le=INT4_MAX)]


class RenglonCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    libro_id: IdInt4
    cantidad: int = PydanticField(ge=1, le=INT4_MAX)


class VentaCreate(BaseModel):
    """No viajan precio, total ni fecha: los resuelve el servidor (RN-06, RN-07)."""

    model_config = ConfigDict(extra="forbid")

    cliente_id: IdInt4
    renglones: list[RenglonCreate] = PydanticField(min_length=1)

    @model_validator(mode="after")
    def _sin_libros_repetidos(self) -> "VentaCreate":
        ids = [r.libro_id for r in self.renglones]
        if len(ids) != len(set(ids)):
            raise ValueError("renglones no puede repetir libro_id")
        return self


class ClienteResumen(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    email: str


class RenglonRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    libro_id: int
    titulo: str = PydanticField(validation_alias=AliasPath("libro", "titulo"))
    cantidad: int
    precio_unitario: Decimal

    @computed_field
    @property
    def subtotal(self) -> Decimal:
        return self.cantidad * self.precio_unitario


class VentaRead(BaseModel):
    """Listado: venta con su cliente."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    fecha: datetime
    total: Decimal
    cliente: ClienteResumen


class VentaDetalleRead(VentaRead):
    """Detalle: suma los renglones."""

    renglones: list[RenglonRead]
