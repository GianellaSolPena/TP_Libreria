from typing import TYPE_CHECKING, Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.modules.usuarios.models import Usuario
    from app.modules.ventas.models import Venta


class Cliente(SQLModel, table=True):
    __tablename__ = "cliente"
    __table_args__ = (
        UniqueConstraint("email", name="uq_cliente_email"),
        UniqueConstraint("usuario_id", name="uq_cliente_usuario_id"),
    )

    id: int | None = Field(default=None, primary_key=True)
    nombre: str
    email: str
    usuario_id: int | None = Field(default=None, foreign_key="usuario.id")

    perfil: Optional["PerfilCliente"] = Relationship(
        back_populates="cliente", sa_relationship_kwargs={"lazy": "raise_on_sql"}
    )
    ventas: list["Venta"] = Relationship(
        back_populates="cliente", sa_relationship_kwargs={"lazy": "raise_on_sql"}
    )
    usuario: Optional["Usuario"] = Relationship(
        back_populates="cliente", sa_relationship_kwargs={"lazy": "raise_on_sql"}
    )


class PerfilCliente(SQLModel, table=True):
    __tablename__ = "perfil_cliente"
    __table_args__ = (UniqueConstraint("cliente_id", name="uq_perfil_cliente_cliente_id"),)

    id: int | None = Field(default=None, primary_key=True)
    cliente_id: int = Field(foreign_key="cliente.id", index=True)
    telefono: str | None = None
    direccion: str | None = None

    cliente: Optional["Cliente"] = Relationship(
        back_populates="perfil", sa_relationship_kwargs={"lazy": "raise_on_sql"}
    )
