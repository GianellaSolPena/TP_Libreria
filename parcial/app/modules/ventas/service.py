import asyncio
import logging
from decimal import Decimal

from app.core.dependencies import SesionActual
from app.core.errores import Conflicto, NoEncontrado, PaginaInexistente, SinPermiso
from app.core.paginacion import Pagina, calcular_offset, calcular_paginas
from app.modules.libros.repository import MOTIVO_VENTA
from app.modules.usuarios.models import Rol, Usuario
from app.modules.ventas.models import RenglonVenta, Venta
from app.modules.ventas.schemas import VentaCreate
from app.modules.ventas.unit_of_work import VentasUnitOfWork

logger = logging.getLogger(__name__)

VENTA_NO_ENCONTRADA = "Venta no encontrada"


async def avisar_comprobante(venta_id: int) -> None:
    """Tarea en segundo plano (Ej. 8): simula el envío del comprobante sin bloquear el loop."""
    await asyncio.sleep(0.5)
    logger.info("Comprobante de la venta %s enviado al cliente", venta_id)


async def crear(uow: VentasUnitOfWork, datos: VentaCreate, actor: Usuario) -> Venta:
    """RN-09/RN-10: venta, renglones, descuentos y movimientos en UN bloque; o todo o nada."""
    async with uow:
        ids = [r.libro_id for r in datos.renglones]
        libros = await uow.libros.get_vigentes_por_ids(ids)
        faltan = sorted(set(ids) - libros.keys())
        if faltan:
            raise Conflicto(f"Los libros {faltan} no existen o están dados de baja")

        # RN-06: el precio se copia del libro; RN-07: total = Σ cantidad × precio_unitario.
        renglones = [
            RenglonVenta(
                libro_id=r.libro_id,
                cantidad=r.cantidad,
                precio_unitario=libros[r.libro_id].precio,
            )
            for r in datos.renglones
        ]
        total = sum((r.cantidad * r.precio_unitario for r in renglones), Decimal("0"))
        venta = Venta(cliente_id=datos.cliente_id, total=total)
        venta.renglones = renglones
        # Un cliente inexistente lo rechaza la FK en este flush (23503 -> 409 en el router).
        await uow.ventas.add(venta)

        # Siempre en el mismo orden (libro_id) para que ventas simultáneas no se interbloqueen.
        for renglon in sorted(renglones, key=lambda r: r.libro_id):
            movimiento = await uow.libros.aplicar_movimiento(
                renglon.libro_id, -renglon.cantidad, MOTIVO_VENTA, actor.id, venta.id
            )
            if movimiento is None:
                libro = libros[renglon.libro_id]
                raise Conflicto(
                    f"No hay stock suficiente de «{libro.titulo}»: "
                    f"hay {libro.stock}, se pidieron {renglon.cantidad}"
                )
        # El detalle se lee dentro del bloque, antes de que el UoW cierre el bloque.
        return await uow.ventas.get_detalle(venta.id)


async def listar(uow: VentasUnitOfWork, page: int, size: int) -> Pagina[Venta]:
    async with uow:
        return await _pagina(uow, page, size)


async def _pagina(
    uow: VentasUnitOfWork, page: int, size: int, cliente_id: int | None = None
) -> Pagina[Venta]:
    total = await uow.ventas.contar(cliente_id)
    pages = calcular_paginas(total, size)
    if page > pages:
        raise PaginaInexistente(page, pages)
    items = await uow.ventas.listar(calcular_offset(page, size), size, cliente_id)
    return Pagina[Venta](items=items, total=total, page=page, size=size, pages=pages)


async def obtener(uow: VentasUnitOfWork, venta_id: int, sesion: SesionActual) -> Venta:
    """RN-14: primero quién es y qué relación tiene con la venta; recién después qué se devuelve."""
    async with uow:
        # Roles vigentes de la base, nunca los del token.
        es_personal = bool({Rol.VENDEDOR, Rol.ADMIN} & set(sesion.roles_vigentes))
        if not es_personal:
            dueno = await uow.ventas.get_dueno(venta_id)
            if dueno is None:
                raise NoEncontrado(VENTA_NO_ENCONTRADA)
            if dueno[1] != sesion.usuario.id:
                raise SinPermiso("No podés ver una venta de otro cliente")
        venta = await uow.ventas.get_detalle(venta_id)
        if venta is None:
            raise NoEncontrado(VENTA_NO_ENCONTRADA)
        return venta


async def mis_ventas(
    uow: VentasUnitOfWork, sesion: SesionActual, page: int, size: int
) -> Pagina[Venta]:
    async with uow:
        cliente = await uow.clientes.get_por_usuario(sesion.usuario.id)
        if cliente is None:  # QA-09: sin ficha de cliente, página vacía
            if page > 1:
                raise PaginaInexistente(page, 1)
            return Pagina[Venta](items=[], total=0, page=page, size=size, pages=1)
        return await _pagina(uow, page, size, cliente.id)
