from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.dependencies import solo_admin
from app.core.errores import IdPath, traducir_errores
from app.core.paginacion import Pagina, PaginaDep
from app.modules.editoriales import service
from app.modules.editoriales.schemas import EditorialCreate, EditorialRead, EditorialUpdate
from app.modules.editoriales.unit_of_work import EditorialesUnitOfWork
from app.modules.libros import service as libros_service
from app.modules.libros.schemas import LibroRead
from app.modules.libros.unit_of_work import LibrosUnitOfWork

# GET sin sesion (matriz de 03) y escrituras solo ADMIN: dos routers con el mismo prefijo.
router_publico = APIRouter(prefix="/editoriales", tags=["editoriales"])
router_admin = APIRouter(prefix="/editoriales", tags=["editoriales"], dependencies=[Depends(solo_admin)])

CONFLICTO = "Ya existe una editorial con ese nombre"


def get_uow(session: Annotated[AsyncSession, Depends(get_session)]) -> EditorialesUnitOfWork:
    return EditorialesUnitOfWork(session)


UowDep = Annotated[EditorialesUnitOfWork, Depends(get_uow)]


@router_admin.post("", response_model=EditorialRead, status_code=status.HTTP_201_CREATED)
async def crear_editorial(datos: EditorialCreate, uow: UowDep) -> EditorialRead:
    with traducir_errores(CONFLICTO):
        return await service.crear(uow, datos)


@router_publico.get("", response_model=Pagina[EditorialRead])
async def listar_editoriales(pagina: PaginaDep, uow: UowDep) -> Pagina[EditorialRead]:
    with traducir_errores(CONFLICTO):
        return await service.listar(uow, pagina.page, pagina.size)


@router_publico.get("/{editorial_id}", response_model=EditorialRead)
async def obtener_editorial(editorial_id: IdPath, uow: UowDep) -> EditorialRead:
    with traducir_errores(CONFLICTO):
        return await service.obtener(uow, editorial_id)


@router_admin.patch("/{editorial_id}", response_model=EditorialRead)
async def actualizar_editorial(editorial_id: IdPath, datos: EditorialUpdate, uow: UowDep) -> EditorialRead:
    with traducir_errores(CONFLICTO):
        return await service.actualizar(uow, editorial_id, datos)


def get_libros_uow(session: Annotated[AsyncSession, Depends(get_session)]) -> LibrosUnitOfWork:
    return LibrosUnitOfWork(session)


@router_publico.get("/{editorial_id}/libros", response_model=Pagina[LibroRead])
async def listar_libros_de_editorial(
    editorial_id: IdPath,
    pagina: PaginaDep,
    uow: Annotated[LibrosUnitOfWork, Depends(get_libros_uow)],
) -> Pagina[LibroRead]:
    with traducir_errores(CONFLICTO):
        return await libros_service.listar_por(
            uow, pagina.page, pagina.size, editorial_id=editorial_id
        )
