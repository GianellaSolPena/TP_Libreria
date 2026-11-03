from app.core.errores import NoEncontrado, PaginaInexistente
from app.core.paginacion import Pagina, calcular_offset, calcular_paginas
from app.modules.generos.models import Genero
from app.modules.generos.schemas import GeneroCreate, GeneroUpdate
from app.modules.generos.unit_of_work import GenerosUnitOfWork


async def crear(uow: GenerosUnitOfWork, datos: GeneroCreate) -> Genero:
    async with uow:
        return await uow.generos.add(Genero(**datos.model_dump()))


async def obtener(uow: GenerosUnitOfWork, genero_id: int) -> Genero:
    async with uow:
        genero = await uow.generos.get_by_id(genero_id)
        if genero is None:
            raise NoEncontrado("Género no encontrado")
        return genero


async def actualizar(uow: GenerosUnitOfWork, genero_id: int, datos: GeneroUpdate) -> Genero:
    async with uow:
        genero = await uow.generos.get_by_id(genero_id)
        if genero is None:
            raise NoEncontrado("Género no encontrado")
        return await uow.generos.update(genero, datos.model_dump(exclude_unset=True))


async def listar(uow: GenerosUnitOfWork, page: int, size: int) -> Pagina[Genero]:
    async with uow:
        total = await uow.generos.count()
        pages = calcular_paginas(total, size)
        if page > pages:
            raise PaginaInexistente(page, pages)
        items = await uow.generos.get_all(offset=calcular_offset(page, size), limit=size)
        return Pagina[Genero](items=items, total=total, page=page, size=size, pages=pages)
