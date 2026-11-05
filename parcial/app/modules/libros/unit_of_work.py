from sqlalchemy.ext.asyncio import AsyncSession

from app.core.unit_of_work import UnitOfWork
from app.modules.autores.repository import AutorRepository
from app.modules.editoriales.repository import EditorialRepository
from app.modules.generos.repository import GeneroRepository
from app.modules.libros.repository import (
    LibroAutorRepository,
    LibroRepository,
    MovimientoStockRepository,
)


class LibrosUnitOfWork(UnitOfWork):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self.libros = LibroRepository(session)
        self.autorias = LibroAutorRepository(session)
        self.movimientos = MovimientoStockRepository(session)
        # Sólo get_by_id: el 404 del padre en /{editoriales,generos,autores}/{id}/libros.
        self.editoriales = EditorialRepository(session)
        self.generos = GeneroRepository(session)
        self.autores = AutorRepository(session)
