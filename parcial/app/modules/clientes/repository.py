from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.repository import BaseRepository
from app.modules.clientes.models import Cliente, PerfilCliente


class ClienteRepository(BaseRepository[Cliente]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Cliente)

    async def get_con_perfil(self, cliente_id: int) -> Cliente | None:
        stmt = (
            select(Cliente)
            .where(Cliente.id == cliente_id)
            .options(joinedload(Cliente.perfil))  # to-one -> joinedload
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).unique().scalar_one_or_none()

    async def get_por_usuario(self, usuario_id: int) -> Cliente | None:
        stmt = select(Cliente).where(Cliente.usuario_id == usuario_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def listar_con_perfil(self, offset: int, limit: int) -> list[Cliente]:
        stmt = (
            select(Cliente)
            .options(joinedload(Cliente.perfil))
            .order_by(Cliente.id)
            .offset(offset)
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars().all())


class PerfilClienteRepository(BaseRepository[PerfilCliente]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, PerfilCliente)
