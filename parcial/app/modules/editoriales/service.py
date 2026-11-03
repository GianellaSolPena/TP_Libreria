from app.core.errores import NoEncontrado, PaginaInexistente
from app.core.paginacion import Pagina, calcular_offset, calcular_paginas
from app.modules.editoriales.models import Editorial
from app.modules.editoriales.schemas import EditorialCreate, EditorialUpdate
from app.modules.editoriales.unit_of_work import EditorialesUnitOfWork


async def crear(uow: EditorialesUnitOfWork, datos: EditorialCreate) -> Editorial:
    async with uow:
        return await uow.editoriales.add(Editorial(**datos.model_dump()))


async def obtener(uow: EditorialesUnitOfWork, editorial_id: int) -> Editorial:
    async with uow:
        editorial = await uow.editoriales.get_by_id(editorial_id)
        if editorial is None:
            raise NoEncontrado("Editorial no encontrada")
        return editorial


async def actualizar(uow: EditorialesUnitOfWork, editorial_id: int, datos: EditorialUpdate) -> Editorial:
    async with uow:
        editorial = await uow.editoriales.get_by_id(editorial_id)
        if editorial is None:
            raise NoEncontrado("Editorial no encontrada")
        return await uow.editoriales.update(editorial, datos.model_dump(exclude_unset=True))


async def listar(uow: EditorialesUnitOfWork, page: int, size: int) -> Pagina[Editorial]:
    async with uow:
        total = await uow.editoriales.count()
        pages = calcular_paginas(total, size)
        if page > pages:
            raise PaginaInexistente(page, pages)
        items = await uow.editoriales.get_all(offset=calcular_offset(page, size), limit=size)
        return Pagina[Editorial](items=items, total=total, page=page, size=size, pages=pages)
