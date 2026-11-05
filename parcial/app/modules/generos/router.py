from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.dependencies import solo_admin
from app.core.errores import IdPath, traducir_errores
from app.core.paginacion import Pagina, PaginaDep
from app.modules.generos import service
from app.modules.generos.schemas import GeneroCreate, GeneroRead, GeneroUpdate
from app.modules.generos.unit_of_work import GenerosUnitOfWork
from app.modules.libros import service as libros_service
from app.modules.libros.schemas import LibroRead
from app.modules.libros.unit_of_work import LibrosUnitOfWork

# GET sin sesion (matriz de 03) y escrituras solo ADMIN: dos routers con el mismo prefijo.
router_publico = APIRouter(prefix="/generos", tags=["generos"])
router_admin = APIRouter(prefix="/generos", tags=["generos"], dependencies=[Depends(solo_admin)])

CONFLICTO = "Ya existe un género con ese nombre"


def get_uow(session: Annotated[AsyncSession, Depends(get_session)]) -> GenerosUnitOfWork:
    return GenerosUnitOfWork(session)


UowDep = Annotated[GenerosUnitOfWork, Depends(get_uow)]


@router_admin.post("", response_model=GeneroRead, status_code=status.HTTP_201_CREATED)
async def crear_genero(datos: GeneroCreate, uow: UowDep) -> GeneroRead:
    with traducir_errores(CONFLICTO):
        return await service.crear(uow, datos)


@router_publico.get("", response_model=Pagina[GeneroRead])
async def listar_generos(pagina: PaginaDep, uow: UowDep) -> Pagina[GeneroRead]:
    with traducir_errores(CONFLICTO):
        return await service.listar(uow, pagina.page, pagina.size)


@router_publico.get("/{genero_id}", response_model=GeneroRead)
async def obtener_genero(genero_id: IdPath, uow: UowDep) -> GeneroRead:
    with traducir_errores(CONFLICTO):
        return await service.obtener(uow, genero_id)


@router_admin.patch("/{genero_id}", response_model=GeneroRead)
async def actualizar_genero(genero_id: IdPath, datos: GeneroUpdate, uow: UowDep) -> GeneroRead:
    with traducir_errores(CONFLICTO):
        return await service.actualizar(uow, genero_id, datos)


def get_libros_uow(session: Annotated[AsyncSession, Depends(get_session)]) -> LibrosUnitOfWork:
    return LibrosUnitOfWork(session)


@router_publico.get("/{genero_id}/libros", response_model=Pagina[LibroRead])
async def listar_libros_de_genero(
    genero_id: IdPath,
    pagina: PaginaDep,
    uow: Annotated[LibrosUnitOfWork, Depends(get_libros_uow)],
) -> Pagina[LibroRead]:
    with traducir_errores(CONFLICTO):
        return await libros_service.listar_por(uow, pagina.page, pagina.size, genero_id=genero_id)
