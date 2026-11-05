from typing import Any

from sqlalchemy import ColumnElement, exists, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.orm.attributes import set_committed_value
from sqlalchemy.orm.util import identity_key

from app.core.repository import BaseRepository, SoftDeleteRepository
from app.modules.libros.models import Libro, LibroAutor, MovimientoStock

# Motivos de los movimientos de stock (Q-07, QA-02). El vínculo con la venta va en `venta_id`.
MOTIVO_STOCK_INICIAL = "Stock inicial"
MOTIVO_REPOSICION = "Reposición"
MOTIVO_VENTA = "Venta"


class LibroRepository(SoftDeleteRepository[Libro]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Libro)

    async def get_detalle(self, libro_id: int) -> Libro | None:
        """Libro vigente con editorial, género y autorías (to-one joinedload, colección selectinload)."""
        stmt = (
            select(Libro)
            .where(Libro.id == libro_id, *self._condiciones())
            .options(
                joinedload(Libro.editorial),
                joinedload(Libro.genero),
                selectinload(Libro.autorias).joinedload(LibroAutor.autor),
            )
            .execution_options(populate_existing=True)
        )
        return (await self.session.execute(stmt)).unique().scalar_one_or_none()

    async def get_vigentes_por_ids(self, ids: list[int]) -> dict[int, Libro]:
        stmt = select(Libro).where(Libro.id.in_(ids), *self._condiciones())
        return {libro.id: libro for libro in (await self.session.execute(stmt)).scalars()}

    def _filtros(
        self,
        titulo: str | None,
        genero_id: int | None,
        editorial_id: int | None,
        autor_id: int | None,
    ) -> list[ColumnElement[bool]]:
        """Los mismos filtros para listar y contar (así `total` coincide con `items`)."""
        filtros = self._condiciones()
        if titulo:
            filtros.append(Libro.titulo.ilike(f"%{titulo}%"))  # parámetro ligado
        if genero_id is not None:
            filtros.append(Libro.genero_id == genero_id)
        if editorial_id is not None:
            filtros.append(Libro.editorial_id == editorial_id)
        if autor_id is not None:
            filtros.append(
                exists().where(LibroAutor.libro_id == Libro.id, LibroAutor.autor_id == autor_id)
            )
        return filtros

    async def listar_vigentes(
        self,
        *,
        offset: int,
        limit: int,
        titulo: str | None = None,
        genero_id: int | None = None,
        editorial_id: int | None = None,
        autor_id: int | None = None,
    ) -> list[Libro]:
        stmt = (
            select(Libro)
            .where(*self._filtros(titulo, genero_id, editorial_id, autor_id))
            .options(joinedload(Libro.editorial), joinedload(Libro.genero))
            .order_by(Libro.id)
            .offset(offset)
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def contar_vigentes(
        self,
        *,
        titulo: str | None = None,
        genero_id: int | None = None,
        editorial_id: int | None = None,
        autor_id: int | None = None,
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(Libro)
            .where(*self._filtros(titulo, genero_id, editorial_id, autor_id))
        )
        return (await self.session.execute(stmt)).scalar_one()

    async def aplicar_movimiento(
        self,
        libro_id: int,
        cantidad: int,
        motivo: str,
        usuario_id: int,
        venta_id: int | None = None,
    ) -> MovimientoStock | None:
        """ÚNICO código que escribe `libro.stock` (D3): UPDATE atómico + su movimiento.

        La base calcula `stock + cantidad` sobre el último valor confirmado y no devuelve
        fila si el libro está dado de baja o el stock quedaría negativo; no hay lectura
        previa que pueda quedar vieja. Devuelve el movimiento agregado, o `None` si no se
        aplicó nada (el servicio decide el mensaje).
        """
        stmt = (
            update(Libro)
            .where(
                Libro.id == libro_id,
                Libro.borrado_en.is_(None),
                Libro.stock + cantidad >= 0,
            )
            .values(stock=Libro.stock + cantidad)
            .returning(Libro.stock)
            .execution_options(synchronize_session=False)
        )
        nuevo_stock = (await self.session.execute(stmt)).scalar_one_or_none()
        if nuevo_stock is None:
            return None
        movimiento = MovimientoStock(
            libro_id=libro_id,
            venta_id=venta_id,
            usuario_id=usuario_id,
            cantidad=cantidad,
            motivo=motivo,
        )
        self.session.add(movimiento)
        await self.session.flush()
        # Si el libro ya está en la sesión, se actualiza su `stock` sin ensuciarlo.
        en_sesion = self.session.identity_map.get(identity_key(Libro, libro_id))
        if en_sesion is not None:
            set_committed_value(en_sesion, "stock", nuevo_stock)
        return movimiento


class LibroAutorRepository(BaseRepository[LibroAutor]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, LibroAutor)


class MovimientoStockRepository(BaseRepository[MovimientoStock]):
    """Sólo agregado (RN-11): la base lo garantiza con el disparador 0004; aquí no hay update/delete."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, MovimientoStock)

    async def update(self, entidad: MovimientoStock, cambios: dict[str, Any]) -> MovimientoStock:
        raise NotImplementedError("Los movimientos de stock no se modifican")

    async def delete(self, entidad: MovimientoStock) -> None:
        raise NotImplementedError("Los movimientos de stock no se borran")

    async def listar_de_libro(self, libro_id: int, offset: int, limit: int) -> list[MovimientoStock]:
        stmt = (
            select(MovimientoStock)
            .where(MovimientoStock.libro_id == libro_id)
            .order_by(MovimientoStock.cuando, MovimientoStock.id)
            .offset(offset)
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def contar_de_libro(self, libro_id: int) -> int:
        stmt = (
            select(func.count())
            .select_from(MovimientoStock)
            .where(MovimientoStock.libro_id == libro_id)
        )
        return (await self.session.execute(stmt)).scalar_one()
