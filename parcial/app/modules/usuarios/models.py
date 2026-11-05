from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import CheckConstraint, DateTime, Index, UniqueConstraint, text
from sqlmodel import Field, Relationship, SQLModel
from sqlmodel.sql.sqltypes import AutoString

if TYPE_CHECKING:
    from app.modules.clientes.models import Cliente
    from app.modules.libros.models import MovimientoStock


# Actor de los eventos que no los origina una persona (p. ej. la carga inicial de seed.py, C-09).
ACTOR_SISTEMA = "SISTEMA"


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


class Rol(str, Enum):
    ADMIN = "ADMIN"
    VENDEDOR = "VENDEDOR"
    CLIENTE = "CLIENTE"


class Usuario(SQLModel, table=True):
    __tablename__ = "usuario"
    __table_args__ = (UniqueConstraint("email", name="uq_usuario_email"),)

    id: int | None = Field(default=None, primary_key=True)
    email: str
    nombre: str
    password_hash: str
    activo: bool = True
    debe_cambiar_password: bool = False

    asignaciones: list["AsignacionRol"] = Relationship(
        back_populates="usuario",
        sa_relationship_kwargs={"foreign_keys": "[AsignacionRol.usuario_id]"},
    )
    cliente: Optional["Cliente"] = Relationship(
        back_populates="usuario", sa_relationship_kwargs={"uselist": False}
    )
    movimientos: list["MovimientoStock"] = Relationship(back_populates="usuario")


class AsignacionRol(SQLModel, table=True):
    __tablename__ = "asignacion_rol"
    __table_args__ = (
        CheckConstraint(
            "rol IN ('ADMIN', 'VENDEDOR', 'CLIENTE')",
            name="ck_asignacion_rol_rol_valido",
        ),
        Index(
            "ux_asignacion_rol_usuario_rol_abierta",
            "usuario_id",
            "rol",
            unique=True,
            postgresql_where=text("revocada_en IS NULL"),
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    usuario_id: int = Field(foreign_key="usuario.id", index=True)
    rol: Rol = Field(sa_type=AutoString)
    desde: datetime = Field(default_factory=_ahora, sa_type=DateTime(timezone=True))
    vence_en: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    revocada_en: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))
    otorgada_por: int | None = Field(default=None, foreign_key="usuario.id", index=True)

    usuario: "Usuario" = Relationship(
        back_populates="asignaciones",
        sa_relationship_kwargs={"foreign_keys": "[AsignacionRol.usuario_id]"},
    )


class IntentoAcceso(SQLModel, table=True):
    __tablename__ = "intento_acceso"
    __table_args__ = (
        Index("ix_intento_acceso_email_ip_cuando", "email", "ip", "cuando"),
    )

    id: int | None = Field(default=None, primary_key=True)
    cuando: datetime = Field(default_factory=_ahora, sa_type=DateTime(timezone=True))
    email: str
    ip: str
    exito: bool


class EventoSeguridad(SQLModel, table=True):
    __tablename__ = "evento_seguridad"

    id: int | None = Field(default=None, primary_key=True)
    cuando: datetime = Field(default_factory=_ahora, sa_type=DateTime(timezone=True))
    actor: str
    accion: str
