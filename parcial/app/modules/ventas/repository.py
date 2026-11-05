from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.core.repository import BaseRepository
from app.modules.clientes.models import Cliente
from app.modules.ventas.models import RenglonVenta, Venta


class VentaRepository(BaseRepository[Venta]):
    """Las ventas no se modifican ni se borran: sólo alta y lecturas."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Venta)

    async def get_detalle(self, venta_id: int) -> Venta | None:
        """Venta con cliente, renglones y libro de cada renglón.

        La precarga por relación no pasa por el filtro de baja de `SoftDeleteRepository`:
        una venta vieja sigue mostrando el título de un libro dado de baja.
        """
        stmt = (
            select(Venta)
            .where(Venta.id == venta_id)
            .options(
                joinedload(Venta.cliente),
                selectinload(Venta.renglones).joinedload(RenglonVenta.libro),
            )
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).unique().scalar_one_or_none()

    async def listar(self, offset: int, limit: int, cliente_id: int | None = None) -> list[Venta]:
        stmt = select(Venta).options(joinedload(Venta.cliente))
        if cliente_id is not None:
            stmt = stmt.where(Venta.cliente_id == cliente_id)
        stmt = stmt.order_by(Venta.id).offset(offset).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def contar(self, cliente_id: int | None = None) -> int:
        stmt = select(func.count()).select_from(Venta)
        if cliente_id is not None:
            stmt = stmt.where(Venta.cliente_id == cliente_id)
        return (await self.session.execute(stmt)).scalar_one()

    async def get_dueno(self, venta_id: int) -> tuple[int, int | None] | None:
        """(venta.id, cliente.usuario_id), o None si la venta no existe; sin cargar el detalle."""
        stmt = (
            select(Venta.id, Cliente.usuario_id)
            .join(Cliente, Cliente.id == Venta.cliente_id)
            .where(Venta.id == venta_id)
        )
        fila = (await self.session.execute(stmt)).one_or_none()
        return None if fila is None else (fila[0], fila[1])
