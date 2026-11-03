from datetime import UTC, datetime
from typing import Any, Generic, TypeVar

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """Acceso a datos genérico. Hace `flush`, nunca confirma (lo hace el UoW)."""

    def __init__(self, session: AsyncSession, model: type[T]) -> None:
        self.session = session
        self.model = model

    def _condiciones(self) -> list[ColumnElement[bool]]:
        """Filtros que aplican TODAS las lecturas (get_by_id, get_all, count)."""
        return []

    async def get_by_id(self, id: int) -> T | None:
        stmt = select(self.model).where(self.model.id == id, *self._condiciones())  # type: ignore[attr-defined]
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_all(self, *, offset: int = 0, limit: int | None = None) -> list[T]:
        stmt = (
            select(self.model)
            .where(*self._condiciones())
            .order_by(self.model.id)  # type: ignore[attr-defined]
            .offset(offset)
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def count(self) -> int:
        stmt = select(func.count()).select_from(self.model).where(*self._condiciones())
        return (await self.session.execute(stmt)).scalar_one()

    async def add(self, entidad: T) -> T:
        self.session.add(entidad)
        await self.session.flush()
        return entidad

    async def update(self, entidad: T, cambios: dict[str, Any]) -> T:
        for campo, valor in cambios.items():
            setattr(entidad, campo, valor)
        await self.session.flush()
        return entidad

    async def delete(self, entidad: T) -> None:
        await self.session.delete(entidad)
        await self.session.flush()


class SoftDeleteRepository(BaseRepository[T]):
    """Repositorio con baja lógica.

    Interfaz asumida de C-03: el modelo tiene `borrado_en: datetime | None`
    (timestamptz, NULL = vigente). Lo estrena Libro en C-07.
    """

    def _condiciones(self) -> list[ColumnElement[bool]]:
        return [*super()._condiciones(), self.model.borrado_en.is_(None)]  # type: ignore[attr-defined]

    async def get_by_id_including_deleted(self, id: int) -> T | None:
        stmt = select(self.model).where(self.model.id == id)  # type: ignore[attr-defined]
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def soft_delete(self, entidad: T) -> T:
        entidad.borrado_en = datetime.now(UTC)  # type: ignore[attr-defined]
        await self.session.flush()
        return entidad
