from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.errores import IdPath, traducir_errores
from app.core.paginacion import Pagina, PaginaDep
from app.modules.autores import service
from app.modules.autores.schemas import AutorCreate, AutorLibroRead, AutorRead, AutorUpdate
from app.modules.autores.unit_of_work import AutoresUnitOfWork

router = APIRouter(prefix="/autores", tags=["autores"])

# El autor no tiene restricción de unicidad: cualquier rechazo de la base es el 409 genérico.
CONFLICTO = "Los datos del autor violan una restricción"


def get_uow(session: Annotated[AsyncSession, Depends(get_session)]) -> AutoresUnitOfWork:
    return AutoresUnitOfWork(session)


UowDep = Annotated[AutoresUnitOfWork, Depends(get_uow)]


@router.post("", response_model=AutorRead, status_code=status.HTTP_201_CREATED)
async def crear_autor(datos: AutorCreate, uow: UowDep) -> AutorRead:
    with traducir_errores(CONFLICTO):
        return await service.crear(uow, datos)


@router.get("", response_model=Pagina[AutorRead])
async def listar_autores(pagina: PaginaDep, uow: UowDep) -> Pagina[AutorRead]:
    with traducir_errores(CONFLICTO):
        return await service.listar(uow, pagina.page, pagina.size)


@router.get("/{autor_id}", response_model=AutorRead)
async def obtener_autor(autor_id: IdPath, uow: UowDep) -> AutorRead:
    with traducir_errores(CONFLICTO):
        return await service.obtener(uow, autor_id)


@router.patch("/{autor_id}", response_model=AutorRead)
async def actualizar_autor(autor_id: IdPath, datos: AutorUpdate, uow: UowDep) -> AutorRead:
    with traducir_errores(CONFLICTO):
        return await service.actualizar(uow, autor_id, datos)


# limit/offset y lista plana hasta C-07 (pasa al envoltorio con la baja lógica de libros).
@router.get("/{autor_id}/libros", response_model=list[AutorLibroRead])
async def listar_libros_de_autor(
    autor_id: IdPath,
    uow: UowDep,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> list[AutorLibroRead]:
    with traducir_errores(CONFLICTO):
        return await service.listar_libros(uow, autor_id, limit, offset)
