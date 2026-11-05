from datetime import UTC, datetime, timedelta

from sqlalchemy import func, literal_column, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.repository import BaseRepository
from app.modules.usuarios.models import (
    AsignacionRol,
    EventoSeguridad,
    IntentoAcceso,
    Rol,
    Usuario,
)


class UsuarioRepository(BaseRepository[Usuario]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Usuario)

    async def get_by_email(self, email: str) -> Usuario | None:
        stmt = select(Usuario).where(Usuario.email == email)
        return (await self.session.execute(stmt)).scalar_one_or_none()


class AsignacionRolRepository(BaseRepository[AsignacionRol]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, AsignacionRol)

    async def roles_vigentes(self, usuario_id: int) -> list[Rol]:
        ahora = datetime.now(UTC)
        stmt = (
            select(AsignacionRol.rol)
            .where(
                AsignacionRol.usuario_id == usuario_id,
                AsignacionRol.revocada_en.is_(None),
                or_(
                    AsignacionRol.vence_en.is_(None),
                    AsignacionRol.vence_en > ahora,
                ),
            )
            .order_by(AsignacionRol.rol)
        )
        valores = (await self.session.execute(stmt)).scalars().all()
        return [Rol(valor) for valor in valores]


class IntentoAccesoRepository(BaseRepository[IntentoAcceso]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, IntentoAcceso)

    async def fallos_recientes(self, email: str, ip: str, ahora: datetime) -> list[datetime]:
        """Los ultimos 5 fallos del correo/IP posteriores al ultimo login correcto.

        Una sola consulta (D6): usa el indice (email, ip, cuando).
        """
        ultimo_exito = (
            select(func.max(IntentoAcceso.cuando))
            .where(
                IntentoAcceso.email == email,
                IntentoAcceso.ip == ip,
                IntentoAcceso.exito.is_(True),
            )
            .scalar_subquery()
        )
        stmt = (
            select(IntentoAcceso.cuando)
            .where(
                IntentoAcceso.email == email,
                IntentoAcceso.ip == ip,
                IntentoAcceso.exito.is_(False),
                IntentoAcceso.cuando > ahora - timedelta(seconds=60),
                IntentoAcceso.cuando
                > func.coalesce(ultimo_exito, literal_column("'-infinity'::timestamptz")),
            )
            .order_by(IntentoAcceso.cuando.desc())
            .limit(5)
        )
        return list((await self.session.execute(stmt)).scalars().all())


class EventoSeguridadRepository(BaseRepository[EventoSeguridad]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, EventoSeguridad)
