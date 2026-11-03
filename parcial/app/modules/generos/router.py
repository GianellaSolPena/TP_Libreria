from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.errores import IdPath, traducir_errores
from app.core.paginacion import Pagina, PaginaDep
from app.modules.libros import service as libros_service
from app.modules.libros.schemas import LibroRead
from app.modules.generos import service
from app.modules.generos.schemas import GeneroCreate, GeneroRead, GeneroUpdate
from app.modules.generos.unit_of_work import GenerosUnitOfWork

router = APIRouter(prefix="/generos", tags=["generos"])

CONFLICTO = "Ya existe un género con ese nombre"


def get_uow(session: Annotated[AsyncSession, Depends(get_session)]) -> GenerosUnitOfWork:
    return GenerosUnitOfWork(session)


UowDep = Annotated[GenerosUnitOfWork, Depends(get_uow)]


@router.post("", response_model=GeneroRead, status_code=status.HTTP_201_CREATED)
async def crear_genero(datos: GeneroCreate, uow: UowDep) -> GeneroRead:
    with traducir_errores(CONFLICTO):
        return await service.crear(uow, datos)


@router.get("", response_model=Pagina[GeneroRead])
async def listar_generos(pagina: PaginaDep, uow: UowDep) -> Pagina[GeneroRead]:
    with traducir_errores(CONFLICTO):
        return await service.listar(uow, pagina.page, pagina.size)


@router.get("/{genero_id}", response_model=GeneroRead)
async def obtener_genero(genero_id: IdPath, uow: UowDep) -> GeneroRead:
    with traducir_errores(CONFLICTO):
        return await service.obtener(uow, genero_id)


@router.patch("/{genero_id}", response_model=GeneroRead)
async def actualizar_genero(genero_id: IdPath, datos: GeneroUpdate, uow: UowDep) -> GeneroRead:
    with traducir_errores(CONFLICTO):
        return await service.actualizar(uow, genero_id, datos)


# TRANSITORIO (C-07): lista con libros.service y `get_session`; pasa al envoltorio y a la baja lógica en C-07.
@router.get("/{genero_id}/libros", response_model=list[LibroRead])
async def listar_libros_de_genero(
    genero_id: IdPath,
    uow: UowDep,
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> list[LibroRead]:
    with traducir_errores(CONFLICTO):
        await service.obtener(uow, genero_id)  # 404 si no existe
    return await libros_service.listar(session, limit, offset, genero_id=genero_id)
