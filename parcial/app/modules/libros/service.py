from app.core.errores import Conflicto, NoEncontrado, PaginaInexistente
from app.core.paginacion import Pagina, calcular_offset, calcular_paginas
from app.modules.libros.models import Libro, LibroAutor
from app.modules.libros.repository import MOTIVO_REPOSICION, MOTIVO_STOCK_INICIAL
from app.modules.libros.schemas import (
    LibroCreate,
    LibroUpdate,
    MovimientoRead,
    ReposicionRead,
)
from app.modules.libros.unit_of_work import LibrosUnitOfWork
from app.modules.usuarios.models import Usuario

LIBRO_NO_ENCONTRADO = "Libro no encontrado"


async def crear(uow: LibrosUnitOfWork, datos: LibroCreate, actor: Usuario) -> Libro:
    async with uow:
        # El INSERT va con stock=0: el stock sólo lo escribe `aplicar_movimiento` (D3).
        libro = await uow.libros.add(
            Libro(
                isbn=datos.isbn,
                titulo=datos.titulo,
                precio=datos.precio,
                stock=0,
                editorial_id=datos.editorial_id,
                genero_id=datos.genero_id,
            )
        )
        for autor in datos.autores:
            await uow.autorias.add(LibroAutor(libro_id=libro.id, **autor.model_dump()))
        if datos.stock_inicial > 0:  # CHECK cantidad <> 0 (QA-03)
            movimiento = await uow.libros.aplicar_movimiento(
                libro.id, datos.stock_inicial, MOTIVO_STOCK_INICIAL, actor.id
            )
            if movimiento is None:
                raise Conflicto("No se pudo registrar el stock inicial")
        return await uow.libros.get_detalle(libro.id)


async def actualizar(uow: LibrosUnitOfWork, libro_id: int, datos: LibroUpdate) -> Libro:
    async with uow:
        libro = await uow.libros.get_by_id(libro_id)  # filtra baja
        if libro is None:
            raise NoEncontrado(LIBRO_NO_ENCONTRADO)
        await uow.libros.update(libro, datos.model_dump(exclude_unset=True))
        return await uow.libros.get_detalle(libro_id)


async def dar_de_baja(uow: LibrosUnitOfWork, libro_id: int) -> None:
    async with uow:
        libro = await uow.libros.get_by_id(libro_id)  # filtra baja
        if libro is None:
            raise NoEncontrado(LIBRO_NO_ENCONTRADO)
        await uow.libros.soft_delete(libro)


async def reponer(
    uow: LibrosUnitOfWork, libro_id: int, cantidad: int, actor: Usuario
) -> ReposicionRead:
    async with uow:
        libro = await uow.libros.get_by_id_including_deleted(libro_id)
        if libro is None:
            raise NoEncontrado(LIBRO_NO_ENCONTRADO)
        if libro.borrado_en is not None:
            raise Conflicto("No se puede reponer un libro dado de baja")
        movimiento = await uow.libros.aplicar_movimiento(
            libro_id, cantidad, MOTIVO_REPOSICION, actor.id
        )
        if movimiento is None:  # se dio de baja entre la lectura y el UPDATE
            raise Conflicto("No se puede reponer un libro dado de baja")
        detalle = await uow.libros.get_detalle(libro_id)
        return ReposicionRead.model_validate(
            {"libro": detalle, "movimiento": movimiento}, from_attributes=True
        )


async def listar_movimientos(
    uow: LibrosUnitOfWork, libro_id: int, page: int, size: int
) -> Pagina[MovimientoRead]:
    async with uow:
        # Historial de auditoría: también para un libro dado de baja (QA-07).
        if await uow.libros.get_by_id_including_deleted(libro_id) is None:
            raise NoEncontrado(LIBRO_NO_ENCONTRADO)
        total = await uow.movimientos.contar_de_libro(libro_id)
        pages = calcular_paginas(total, size)
        if page > pages:
            raise PaginaInexistente(page, pages)
        items = await uow.movimientos.listar_de_libro(libro_id, calcular_offset(page, size), size)
        return Pagina[MovimientoRead](
            items=[MovimientoRead.model_validate(m) for m in items],
            total=total,
            page=page,
            size=size,
            pages=pages,
        )


async def _listar(
    uow: LibrosUnitOfWork, page: int, size: int, **filtros: str | int | None
) -> Pagina[Libro]:
    total = await uow.libros.contar_vigentes(**filtros)
    pages = calcular_paginas(total, size)
    if page > pages:
        raise PaginaInexistente(page, pages)
    items = await uow.libros.listar_vigentes(
        offset=calcular_offset(page, size), limit=size, **filtros
    )
    return Pagina[Libro](items=items, total=total, page=page, size=size, pages=pages)


async def listar(
    uow: LibrosUnitOfWork,
    page: int,
    size: int,
    titulo: str | None = None,
    genero_id: int | None = None,
) -> Pagina[Libro]:
    async with uow:
        return await _listar(uow, page, size, titulo=titulo, genero_id=genero_id)


async def obtener(uow: LibrosUnitOfWork, libro_id: int) -> Libro:
    async with uow:
        libro = await uow.libros.get_detalle(libro_id)
        if libro is None:
            raise NoEncontrado(LIBRO_NO_ENCONTRADO)
        return libro


async def listar_por(
    uow: LibrosUnitOfWork,
    page: int,
    size: int,
    *,
    editorial_id: int | None = None,
    genero_id: int | None = None,
    autor_id: int | None = None,
) -> Pagina[Libro]:
    """Libros vigentes de una editorial, un género o un autor; 404 si el padre no existe."""
    async with uow:
        if editorial_id is not None and await uow.editoriales.get_by_id(editorial_id) is None:
            raise NoEncontrado("Editorial no encontrada")
        if genero_id is not None and await uow.generos.get_by_id(genero_id) is None:
            raise NoEncontrado("Género no encontrado")
        if autor_id is not None and await uow.autores.get_by_id(autor_id) is None:
            raise NoEncontrado("Autor no encontrado")
        return await _listar(
            uow, page, size, editorial_id=editorial_id, genero_id=genero_id, autor_id=autor_id
        )
