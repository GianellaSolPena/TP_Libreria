from app.core.errores import NoEncontrado, PaginaInexistente
from app.core.paginacion import Pagina, calcular_offset, calcular_paginas
from app.modules.autores.models import Autor
from app.modules.autores.schemas import AutorCreate, AutorUpdate
from app.modules.autores.unit_of_work import AutoresUnitOfWork


async def crear(uow: AutoresUnitOfWork, datos: AutorCreate) -> Autor:
    async with uow:
        return await uow.autores.add(Autor(**datos.model_dump()))


async def obtener(uow: AutoresUnitOfWork, autor_id: int) -> Autor:
    async with uow:
        autor = await uow.autores.get_by_id(autor_id)
        if autor is None:
            raise NoEncontrado("Autor no encontrado")
        return autor


async def actualizar(uow: AutoresUnitOfWork, autor_id: int, datos: AutorUpdate) -> Autor:
    async with uow:
        autor = await uow.autores.get_by_id(autor_id)
        if autor is None:
            raise NoEncontrado("Autor no encontrado")
        return await uow.autores.update(autor, datos.model_dump(exclude_unset=True))


async def listar(uow: AutoresUnitOfWork, page: int, size: int) -> Pagina[Autor]:
    async with uow:
        total = await uow.autores.count()
        pages = calcular_paginas(total, size)
        if page > pages:
            raise PaginaInexistente(page, pages)
        items = await uow.autores.get_all(offset=calcular_offset(page, size), limit=size)
        return Pagina[Autor](items=items, total=total, page=page, size=size, pages=pages)
