from sqlmodel import Field, Relationship, SQLModel


class Cliente(SQLModel, table=True):
    __tablename__ = "cliente"

    id: int | None = Field(default=None, primary_key=True)
    nombre: str
    email: str = Field(unique=True)

    perfil: "PerfilCliente | None" = Relationship(
        back_populates="cliente", uselist=False
    )


class PerfilCliente(SQLModel, table=True):
    __tablename__ = "perfil_cliente"

    id: int | None = Field(default=None, primary_key=True)
    cliente_id: int = Field(foreign_key="cliente.id", unique=True, index=True)
    telefono: str | None = None
    direccion: str | None = None

    cliente: Cliente | None = Relationship(back_populates="perfil")
