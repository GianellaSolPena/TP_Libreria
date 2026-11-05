from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.dependencies import UsuarioActualDep, solo_admin
from app.core.errores import IdPath, traducir_errores
from app.core.paginacion import Pagina, PaginaDep
from app.modules.libros import service
from app.modules.libros.schemas import (
    INT4_MAX,
    LibroCreate,
    LibroDetalleRead,
    LibroRead,
    LibroUpdate,
    MovimientoRead,
    ReponerIn,
    ReposicionRead,
)
from app.modules.libros.unit_of_work import LibrosUnitOfWork

# GET sin sesión (matriz de 03) y escrituras sólo ADMIN: dos routers con el mismo prefijo.
router_publico = APIRouter(prefix="/libros", tags=["libros"])
router_admin = APIRouter(prefix="/libros", tags=["libros"], dependencies=[Depends(solo_admin)])

CONFLICTO = "Ya existe un libro vigente con ese ISBN"
CONFLICTO_FK = "La editorial, el género o algún autor indicado no existe"


def get_uow(session: Annotated[AsyncSession, Depends(get_session)]) -> LibrosUnitOfWork:
    return LibrosUnitOfWork(session)


UowDep = Annotated[LibrosUnitOfWork, Depends(get_uow)]


@router_admin.post("", response_model=LibroDetalleRead, status_code=status.HTTP_201_CREATED)
async def crear_libro(
    datos: LibroCreate, uow: UowDep, sesion: UsuarioActualDep
) -> LibroDetalleRead:
    with traducir_errores(CONFLICTO, CONFLICTO_FK):
        return await service.crear(uow, datos, sesion.usuario)


@router_publico.get("", response_model=Pagina[LibroRead])
async def listar_libros(
    pagina: PaginaDep,
    uow: UowDep,
    titulo: str | None = Query(None),
    genero_id: int | None = Query(None, ge=1, le=INT4_MAX),
) -> Pagina[LibroRead]:
    with traducir_errores(CONFLICTO, CONFLICTO_FK):
        return await service.listar(uow, pagina.page, pagina.size, titulo, genero_id)


@router_publico.get("/{libro_id}", response_model=LibroDetalleRead)
async def obtener_libro(libro_id: IdPath, uow: UowDep) -> LibroDetalleRead:
    with traducir_errores(CONFLICTO, CONFLICTO_FK):
        return await service.obtener(uow, libro_id)


@router_admin.patch("/{libro_id}", response_model=LibroDetalleRead)
async def actualizar_libro(libro_id: IdPath, datos: LibroUpdate, uow: UowDep) -> LibroDetalleRead:
    with traducir_errores(CONFLICTO, CONFLICTO_FK):
        return await service.actualizar(uow, libro_id, datos)


@router_admin.delete("/{libro_id}", status_code=status.HTTP_204_NO_CONTENT)
async def dar_de_baja_libro(libro_id: IdPath, uow: UowDep) -> Response:
    with traducir_errores(CONFLICTO, CONFLICTO_FK):
        await service.dar_de_baja(uow, libro_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router_admin.post("/{libro_id}/reponer", response_model=ReposicionRead)
async def reponer_libro(
    libro_id: IdPath, datos: ReponerIn, uow: UowDep, sesion: UsuarioActualDep
) -> ReposicionRead:
    with traducir_errores(CONFLICTO, CONFLICTO_FK):
        return await service.reponer(uow, libro_id, datos.cantidad, sesion.usuario)


@router_admin.get("/{libro_id}/movimientos", response_model=Pagina[MovimientoRead])
async def listar_movimientos_de_libro(
    libro_id: IdPath, pagina: PaginaDep, uow: UowDep
) -> Pagina[MovimientoRead]:
    with traducir_errores(CONFLICTO, CONFLICTO_FK):
        return await service.listar_movimientos(uow, libro_id, pagina.page, pagina.size)
