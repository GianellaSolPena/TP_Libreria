from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession


class UnitOfWork:
    """Confirma al salir del bloque sin excepción y revierte si la hubo.

    No crea la sesión (la entrega `get_session`), por eso tampoco la cierra.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.session.rollback()
            return
        try:
            await self.session.commit()
        except BaseException:
            await self.session.rollback()
            raise
