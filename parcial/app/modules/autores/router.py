from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.dependencies import solo_admin
from app.core.errores import IdPath, traducir_errores
from app.core.paginacion import Pagina, PaginaDep
from app.modules.autores import service
from app.modules.autores.schemas import AutorCreate, AutorRead, AutorUpdate
from app.modules.autores.unit_of_work import AutoresUnitOfWork
from app.modules.libros import service as libros_service
from app.modules.libros.schemas import LibroRead
from app.modules.libros.unit_of_work import LibrosUnitOfWork

# GET sin sesion (matriz de 03) y escrituras solo ADMIN: dos routers con el mismo prefijo.
router_publico = APIRouter(prefix="/autores", tags=["autores"])
router_admin = APIRouter(prefix="/autores", tags=["autores"], dependencies=[Depends(solo_admin)])

# El autor no tiene restricción de unicidad: cualquier rechazo de la base es el 409 genérico.
CONFLICTO = "Los datos del autor violan una restricción"


def get_uow(session: Annotated[AsyncSession, Depends(get_session)]) -> AutoresUnitOfWork:
    return AutoresUnitOfWork(session)


UowDep = Annotated[AutoresUnitOfWork, Depends(get_uow)]


@router_admin.post("", response_model=AutorRead, status_code=status.HTTP_201_CREATED)
async def crear_autor(datos: AutorCreate, uow: UowDep) -> AutorRead:
    with traducir_errores(CONFLICTO):
        return await service.crear(uow, datos)


@router_publico.get("", response_model=Pagina[AutorRead])
async def listar_autores(pagina: PaginaDep, uow: UowDep) -> Pagina[AutorRead]:
    with traducir_errores(CONFLICTO):
        return await service.listar(uow, pagina.page, pagina.size)


@router_publico.get("/{autor_id}", response_model=AutorRead)
async def obtener_autor(autor_id: IdPath, uow: UowDep) -> AutorRead:
    with traducir_errores(CONFLICTO):
        return await service.obtener(uow, autor_id)


@router_admin.patch("/{autor_id}", response_model=AutorRead)
async def actualizar_autor(autor_id: IdPath, datos: AutorUpdate, uow: UowDep) -> AutorRead:
    with traducir_errores(CONFLICTO):
        return await service.actualizar(uow, autor_id, datos)


def get_libros_uow(session: Annotated[AsyncSession, Depends(get_session)]) -> LibrosUnitOfWork:
    return LibrosUnitOfWork(session)


@router_publico.get("/{autor_id}/libros", response_model=Pagina[LibroRead])
async def listar_libros_de_autor(
    autor_id: IdPath,
    pagina: PaginaDep,
    uow: Annotated[LibrosUnitOfWork, Depends(get_libros_uow)],
) -> Pagina[LibroRead]:
    with traducir_errores(CONFLICTO):
        return await libros_service.listar_por(uow, pagina.page, pagina.size, autor_id=autor_id)
