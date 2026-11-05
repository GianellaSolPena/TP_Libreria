from sqlalchemy.ext.asyncio import AsyncSession

from app.core.unit_of_work import UnitOfWork
from app.modules.clientes.repository import ClienteRepository
from app.modules.libros.repository import LibroRepository, MovimientoStockRepository
from app.modules.ventas.repository import VentaRepository


class VentasUnitOfWork(UnitOfWork):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self.ventas = VentaRepository(session)
        self.clientes = ClienteRepository(session)
        self.libros = LibroRepository(session)
        self.movimientos = MovimientoStockRepository(session)
