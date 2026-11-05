from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.dependencies import personal
from app.core.errores import IdPath, traducir_errores
from app.core.paginacion import Pagina, PaginaDep
from app.modules.clientes import service
from app.modules.clientes.schemas import (
    ClienteCreate,
    ClienteRead,
    ClienteUpdate,
    PerfilCreate,
    PerfilRead,
)
from app.modules.clientes.unit_of_work import ClientesUnitOfWork
from app.modules.ventas.schemas import VentaRead

router = APIRouter(prefix="/clientes", tags=["clientes"], dependencies=[Depends(personal)])

CONFLICTO = "Ya existe un cliente con ese correo"
CONFLICTO_PERFIL = "El cliente ya tiene un perfil"


def get_uow(session: Annotated[AsyncSession, Depends(get_session)]) -> ClientesUnitOfWork:
    return ClientesUnitOfWork(session)


UowDep = Annotated[ClientesUnitOfWork, Depends(get_uow)]


@router.post("", response_model=ClienteRead, status_code=status.HTTP_201_CREATED)
async def crear_cliente(datos: ClienteCreate, uow: UowDep) -> ClienteRead:
    with traducir_errores(CONFLICTO):
        return await service.crear(uow, datos)


@router.get("", response_model=Pagina[ClienteRead])
async def listar_clientes(pagina: PaginaDep, uow: UowDep) -> Pagina[ClienteRead]:
    with traducir_errores(CONFLICTO):
        return await service.listar(uow, pagina.page, pagina.size)


@router.get("/{cliente_id}", response_model=ClienteRead)
async def obtener_cliente(cliente_id: IdPath, uow: UowDep) -> ClienteRead:
    with traducir_errores(CONFLICTO):
        return await service.obtener(uow, cliente_id)


@router.patch("/{cliente_id}", response_model=ClienteRead)
async def actualizar_cliente(cliente_id: IdPath, datos: ClienteUpdate, uow: UowDep) -> ClienteRead:
    with traducir_errores(CONFLICTO):
        return await service.actualizar(uow, cliente_id, datos)


@router.post("/{cliente_id}/perfil", response_model=PerfilRead, status_code=status.HTTP_201_CREATED)
async def crear_perfil(cliente_id: IdPath, datos: PerfilCreate, uow: UowDep) -> PerfilRead:
    with traducir_errores(CONFLICTO_PERFIL):
        return await service.crear_perfil(uow, cliente_id, datos)


@router.get("/{cliente_id}/ventas", response_model=Pagina[VentaRead])
async def listar_ventas_de_cliente(
    cliente_id: IdPath, pagina: PaginaDep, uow: UowDep
) -> Pagina[VentaRead]:
    with traducir_errores(CONFLICTO):
        return await service.listar_ventas(uow, cliente_id, pagina.page, pagina.size)
