from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.dependencies import UsuarioActualDep, personal
from app.core.errores import IdPath, traducir_errores
from app.core.paginacion import Pagina, PaginaDep
from app.modules.ventas import service
from app.modules.ventas.schemas import VentaCreate, VentaDetalleRead, VentaRead
from app.modules.ventas.unit_of_work import VentasUnitOfWork

# Personal (VENDEDOR, ADMIN): registrar y listar.
router_personal = APIRouter(prefix="/ventas", tags=["ventas"], dependencies=[Depends(personal)])
# Sólo sesión, sin rol: el servicio decide por la relación con la venta (RN-14, D7).
router_autenticado = APIRouter(tags=["ventas"])

CONFLICTO = "Los datos de la venta violan una restricción"
CONFLICTO_FK = "El cliente indicado no existe"


def get_uow(session: Annotated[AsyncSession, Depends(get_session)]) -> VentasUnitOfWork:
    return VentasUnitOfWork(session)


UowDep = Annotated[VentasUnitOfWork, Depends(get_uow)]


@router_personal.post("", response_model=VentaDetalleRead, status_code=status.HTTP_201_CREATED)
async def crear_venta(
    datos: VentaCreate,
    background_tasks: BackgroundTasks,
    uow: UowDep,
    sesion: UsuarioActualDep,
) -> VentaDetalleRead:
    with traducir_errores(CONFLICTO, CONFLICTO_FK):
        venta = await service.crear(uow, datos, sesion.usuario)
    # Sólo se agenda si el servicio devolvió (venta confirmada); corre tras enviar la respuesta.
    background_tasks.add_task(service.avisar_comprobante, venta.id)
    return venta


@router_personal.get("", response_model=Pagina[VentaRead])
async def listar_ventas(pagina: PaginaDep, uow: UowDep) -> Pagina[VentaRead]:
    with traducir_errores(CONFLICTO, CONFLICTO_FK):
        return await service.listar(uow, pagina.page, pagina.size)


@router_autenticado.get("/ventas/{venta_id}", response_model=VentaDetalleRead)
async def obtener_venta(
    venta_id: IdPath, uow: UowDep, sesion: UsuarioActualDep
) -> VentaDetalleRead:
    with traducir_errores(CONFLICTO, CONFLICTO_FK):
        return await service.obtener(uow, venta_id, sesion)


@router_autenticado.get("/mis-ventas", response_model=Pagina[VentaRead])
async def mis_ventas(
    pagina: PaginaDep, uow: UowDep, sesion: UsuarioActualDep
) -> Pagina[VentaRead]:
    with traducir_errores(CONFLICTO, CONFLICTO_FK):
        return await service.mis_ventas(uow, sesion, pagina.page, pagina.size)
