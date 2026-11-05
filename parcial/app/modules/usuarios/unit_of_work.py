from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.unit_of_work import UnitOfWork
from app.modules.clientes.repository import ClienteRepository
from app.modules.usuarios.repository import (
    AsignacionRolRepository,
    EventoSeguridadRepository,
    IntentoAccesoRepository,
    UsuarioRepository,
)


class UsuariosUnitOfWork(UnitOfWork):
    """UoW de la peticion: no crea ni cierra la sesion (la entrega `get_session`)."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)
        self.usuarios = UsuarioRepository(session)
        self.asignaciones = AsignacionRolRepository(session)
        self.clientes = ClienteRepository(session)
        self.eventos = EventoSeguridadRepository(session)
        # Solo para LEER el limite de intentos dentro de la transaccion de la peticion.
        self.intentos = IntentoAccesoRepository(session)


class IntentosAccesoUnitOfWork:
    """UoW propio de `intento_acceso` (DD-09).

    Que hace distinto: abre su propia sesion y transaccion y confirma siempre,
    independiente del UoW de la peticion.
    Por que: el fallo que se quiere contar (401) es el mismo que revierte la
    transaccion de la peticion; si compartiera la transaccion, el intento fallido
    desapareceria con el rollback y el limite de RN-07 nunca se alcanzaria.
    Costo: deja filas aunque la peticion falle (es lo buscado) y usa una segunda
    conexion del pool durante la escritura.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self.session: AsyncSession | None = None
        self.intentos: IntentoAccesoRepository | None = None

    async def __aenter__(self) -> Self:
        self.session = self._session_factory()
        self.intentos = IntentoAccesoRepository(self.session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        assert self.session is not None
        try:
            if exc_type is not None:
                await self.session.rollback()
            else:
                await self.session.commit()
        except BaseException:
            await self.session.rollback()
            raise
        finally:
            await self.session.close()
