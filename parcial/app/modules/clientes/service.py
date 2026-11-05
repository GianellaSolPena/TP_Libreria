from app.core.errores import Conflicto, NoEncontrado, PaginaInexistente
from app.core.paginacion import Pagina, calcular_offset, calcular_paginas
from app.modules.clientes.models import Cliente, PerfilCliente
from app.modules.clientes.schemas import ClienteCreate, ClienteUpdate, PerfilCreate
from app.modules.clientes.unit_of_work import ClientesUnitOfWork
from app.modules.ventas.models import Venta

CLIENTE_NO_ENCONTRADO = "Cliente no encontrado"
CORREO_DE_CUENTA = "El correo de un cliente con cuenta no se puede cambiar"


async def crear(uow: ClientesUnitOfWork, datos: ClienteCreate) -> Cliente:
    # Sin chequeo previo: la UNIQUE del correo rechaza el duplicado (RN-01).
    async with uow:
        cliente = await uow.clientes.add(Cliente(**datos.model_dump()))
        return await uow.clientes.get_con_perfil(cliente.id)


async def listar(uow: ClientesUnitOfWork, page: int, size: int) -> Pagina[Cliente]:
    async with uow:
        total = await uow.clientes.count()
        pages = calcular_paginas(total, size)
        if page > pages:
            raise PaginaInexistente(page, pages)
        items = await uow.clientes.listar_con_perfil(calcular_offset(page, size), size)
        return Pagina[Cliente](items=items, total=total, page=page, size=size, pages=pages)


async def obtener(uow: ClientesUnitOfWork, cliente_id: int) -> Cliente:
    async with uow:
        cliente = await uow.clientes.get_con_perfil(cliente_id)
        if cliente is None:
            raise NoEncontrado(CLIENTE_NO_ENCONTRADO)
        return cliente


async def actualizar(uow: ClientesUnitOfWork, cliente_id: int, datos: ClienteUpdate) -> Cliente:
    async with uow:
        cliente = await uow.clientes.get_con_perfil(cliente_id)
        if cliente is None:
            raise NoEncontrado(CLIENTE_NO_ENCONTRADO)
        cambios = datos.model_dump(exclude_unset=True)
        # QA-12: el correo de un cliente con usuario es su credencial de login; no se cambia
        # por aquí, así `cliente.email` y `usuario.email` nunca divergen.
        if "email" in cambios and cliente.usuario_id is not None:
            raise Conflicto(CORREO_DE_CUENTA)
        return await uow.clientes.update(cliente, cambios)


async def crear_perfil(
    uow: ClientesUnitOfWork, cliente_id: int, datos: PerfilCreate
) -> PerfilCliente:
    async with uow:
        # La lectura es por el 404 del recurso de la ruta; la unicidad la garantiza la base.
        if await uow.clientes.get_by_id(cliente_id) is None:
            raise NoEncontrado(CLIENTE_NO_ENCONTRADO)
        return await uow.perfiles.add(PerfilCliente(cliente_id=cliente_id, **datos.model_dump()))


async def listar_ventas(
    uow: ClientesUnitOfWork, cliente_id: int, page: int, size: int
) -> Pagina[Venta]:
    async with uow:
        if await uow.clientes.get_by_id(cliente_id) is None:
            raise NoEncontrado(CLIENTE_NO_ENCONTRADO)
        total = await uow.ventas.contar(cliente_id)
        pages = calcular_paginas(total, size)
        if page > pages:
            raise PaginaInexistente(page, pages)
        items = await uow.ventas.listar(calcular_offset(page, size), size, cliente_id)
        return Pagina[Venta](items=items, total=total, page=page, size=size, pages=pages)
