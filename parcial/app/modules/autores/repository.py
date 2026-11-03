from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.repository import BaseRepository
from app.modules.autores.models import Autor
from app.modules.libros.models import LibroAutor


class AutorRepository(BaseRepository[Autor]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Autor)

    async def listar_autorias(self, autor_id: int, offset: int, limit: int) -> list[LibroAutor]:
        stmt = (
            select(LibroAutor)
            .where(LibroAutor.autor_id == autor_id)
            .options(joinedload(LibroAutor.libro))  # to-one -> joinedload
            .order_by(LibroAutor.libro_id)
            .offset(offset)
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars().all())
