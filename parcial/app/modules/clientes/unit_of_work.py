from sqlalchemy.ext.asyncio import AsyncSession

from app.core.unit_of_work import UnitOfWork
from app.modules.clientes.repository import ClienteRepository, PerfilClienteRepository
from app.modules.ventas.repository import VentaRepository


class ClientesUnitOfWork(UnitOfWork):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self.clientes = ClienteRepository(session)
        self.perfiles = PerfilClienteRepository(session)
        self.ventas = VentaRepository(session)  # para /clientes/{id}/ventas
