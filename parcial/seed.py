"""Datos iniciales del parcial (Ej. 9 del PDF): `python seed.py` desde `parcial/`.

Deja la base en un estado conocido y repetible:
  1. vacía TODAS las tablas de la aplicación (TRUNCATE ... RESTART IDENTITY CASCADE),
  2. carga catálogo, personas, stock, venta 1 y la línea SISTEMA,
  3. comprueba `libro.stock == SUM(movimiento_stock.cantidad)`,
todo en UNA transacción: si algo falla se revierte también el vaciado.

Toma la conexión de la misma configuración que la aplicación (`.env` / variables de
entorno), así que no lleva credenciales. El esquema (migraciones y disparador de sólo
agregado) no se toca: TRUNCATE no dispara los disparadores de DELETE.

Las contraseñas en claro de abajo son de MENTIRA, sólo para estos datos iniciales.
"""

import asyncio
import sys
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel

from app.core.config import get_settings
from app.core.database import create_engine, create_session_factory
from app.core.security import hashear_password
from app.modules import models as _modelos  # noqa: F401  (registra TODAS las tablas en el metadata)
from app.modules.autores.models import Autor
from app.modules.clientes.models import Cliente, PerfilCliente
from app.modules.editoriales.models import Editorial
from app.modules.generos.models import Genero
from app.modules.libros.models import Libro, LibroAutor, MovimientoStock
from app.modules.libros.repository import (
    MOTIVO_STOCK_INICIAL,
    MOTIVO_VENTA,
    LibroRepository,
)
from app.modules.usuarios.models import (
    ACTOR_SISTEMA,
    AsignacionRol,
    EventoSeguridad,
    Rol,
    Usuario,
)
from app.modules.ventas.models import RenglonVenta, Venta

# (email, nombre, contraseña de mentira, rol, debe_cambiar_password)
USUARIOS = [
    ("admin@example.com", "Administración", "admin1234", Rol.ADMIN, False),
    ("admin2@example.com", "Administración 2", "admin21234", Rol.ADMIN, False),
    ("vendedor@example.com", "Vendedor", "vendedor1234", Rol.VENDEDOR, False),
    ("ana@example.com", "Ana Paz", "ana12345", Rol.CLIENTE, False),
    ("nuevo@example.com", "Personal nuevo", "nuevo1234", Rol.VENDEDOR, True),
]

# id del usuario según el orden de USUARIOS (los ids salen del orden de inserción).
ADMIN_ID = 1
VENDEDOR_ID = 3
ANA_USUARIO_ID = 4

# (isbn, título, precio, stock inicial, editorial_id, genero_id, [(autor_id, rol, orden)])
LIBROS = [
    ("978-950-00-0001-1", "Rayuela", "25000.00", 11, 1, 1, [(1, "autor", 1)]),
    (
        "978-950-00-0002-8",
        "Antología de la literatura fantástica",
        "30000.00",
        5,
        2,
        2,
        [(2, "autor", 1), (3, "coautor", 2), (4, "coautor", 3)],
    ),
    ("978-950-00-0003-3", "Ficciones", "22000.00", 10, 1, 2, [(2, "autor", 1)]),
    ("978-950-00-0004-4", "Respiración artificial", "27000.00", 3, 2, 1, [(5, "autor", 1)]),
    ("978-950-00-0005-5", "Bestiario", "16000.00", 1, 1, 2, [(1, "autor", 1)]),
]

FECHA_VENTA_1 = datetime(2026, 10, 1, 15, 0, 0, tzinfo=UTC)


class SeedError(Exception):
    """Error de coherencia de los datos iniciales (provoca rollback y código de salida 1)."""


def comprobar_ids(entidades: list, esperados: list[int], nombre: str) -> None:
    obtenidos = [e.id for e in entidades]
    if obtenidos != esperados:
        raise SeedError(f"Ids inesperados en {nombre}: {obtenidos} (esperados {esperados})")


async def vaciar(session: AsyncSession) -> None:
    """Un único TRUNCATE de todas las tablas del modelo (alembic_version no está en el metadata)."""
    tablas = ", ".join(f'"{t.name}"' for t in SQLModel.metadata.sorted_tables)
    await session.execute(text(f"TRUNCATE {tablas} RESTART IDENTITY CASCADE"))


async def cargar_catalogo(session: AsyncSession) -> list[Libro]:
    editoriales = [
        Editorial(nombre="Sudamericana", pais="Argentina"),
        Editorial(nombre="Alfaguara", pais="España"),
        Editorial(nombre="Emecé", pais="Argentina"),
    ]
    generos = [Genero(nombre="Novela"), Genero(nombre="Cuento"), Genero(nombre="Ensayo")]
    autores = [
        Autor(nombre="Julio Cortázar", nacionalidad="Argentina"),
        Autor(nombre="Jorge Luis Borges", nacionalidad="Argentina"),
        Autor(nombre="Adolfo Bioy Casares", nacionalidad="Argentina"),
        Autor(nombre="Silvina Ocampo", nacionalidad="Argentina"),
        Autor(nombre="Ricardo Piglia", nacionalidad="Argentina"),
        Autor(nombre="Ernesto Sabato", nacionalidad="Argentina"),
    ]
    for grupo in (editoriales, generos, autores):
        session.add_all(grupo)
        await session.flush()
    comprobar_ids(editoriales, [1, 2, 3], "editorial")
    comprobar_ids(generos, [1, 2, 3], "genero")
    comprobar_ids(autores, [1, 2, 3, 4, 5, 6], "autor")

    # stock = 0: el stock real se escribe sólo con LibroRepository.aplicar_movimiento (D6).
    libros = [
        Libro(
            isbn=isbn,
            titulo=titulo,
            precio=Decimal(precio),
            stock=0,
            editorial_id=editorial_id,
            genero_id=genero_id,
        )
        for isbn, titulo, precio, _stock, editorial_id, genero_id, _aut in LIBROS
    ]
    session.add_all(libros)
    await session.flush()
    comprobar_ids(libros, [1, 2, 3, 4, 5], "libro")

    for libro, (*_resto, autorias) in zip(libros, LIBROS, strict=True):
        for autor_id, rol, orden in autorias:
            session.add(LibroAutor(libro_id=libro.id, autor_id=autor_id, rol=rol, orden=orden))
    await session.flush()
    return libros


async def cargar_personas(session: AsyncSession, hashes: list[str]) -> None:
    usuarios = [
        Usuario(
            email=email,
            nombre=nombre,
            password_hash=hash_,
            activo=True,
            debe_cambiar_password=debe_cambiar,
        )
        for (email, nombre, _plano, _rol, debe_cambiar), hash_ in zip(
            USUARIOS, hashes, strict=True
        )
    ]
    session.add_all(usuarios)
    await session.flush()
    comprobar_ids(usuarios, [1, 2, 3, 4, 5], "usuario")

    ahora = datetime.now(UTC)
    for usuario, (*_resto, rol, _debe) in zip(usuarios, USUARIOS, strict=True):
        # Abiertas: sin vencimiento ni revocación; otorgadas por el sistema (otorgada_por nulo).
        session.add(AsignacionRol(usuario_id=usuario.id, rol=rol, desde=ahora))

    clientes = [
        Cliente(nombre="Lucía Fernández", email="lucia@example.com"),
        Cliente(nombre="Tomás Ríos", email="tomas@example.com"),
        Cliente(nombre="Ana Paz", email="ana@example.com", usuario_id=ANA_USUARIO_ID),
    ]
    session.add_all(clientes)
    await session.flush()
    comprobar_ids(clientes, [1, 2, 3], "cliente")
    session.add(PerfilCliente(cliente_id=1, telefono="11-5555-0001", direccion="Av. Corrientes 1234"))
    await session.flush()


async def cargar_stock_y_venta(session: AsyncSession, libros: list[Libro]) -> None:
    repo = LibroRepository(session)

    # Stock inicial por libro, registrado por el administrador (Q-08).
    for libro, stock_inicial in zip(libros, (fila[3] for fila in LIBROS), strict=True):
        mov = await repo.aplicar_movimiento(libro.id, stock_inicial, MOTIVO_STOCK_INICIAL, ADMIN_ID)
        if mov is None:
            raise SeedError(f"No se pudo cargar el stock inicial del libro {libro.id}")

    # Venta 1 de Lucía: precio copiado del libro, total calculado, registrada por el vendedor.
    renglones = [(1, 1), (3, 2)]  # (libro_id, cantidad): Rayuela x1, Ficciones x2
    precios = {libro.id: libro.precio for libro in libros}
    total = sum((precios[libro_id] * cantidad for libro_id, cantidad in renglones), Decimal("0"))
    venta = Venta(cliente_id=1, fecha=FECHA_VENTA_1, total=total)
    session.add(venta)
    await session.flush()
    comprobar_ids([venta], [1], "venta")
    for libro_id, cantidad in renglones:
        session.add(
            RenglonVenta(
                venta_id=venta.id,
                libro_id=libro_id,
                cantidad=cantidad,
                precio_unitario=precios[libro_id],
            )
        )
    await session.flush()
    for libro_id, cantidad in renglones:
        mov = await repo.aplicar_movimiento(
            libro_id, -cantidad, MOTIVO_VENTA, VENDEDOR_ID, venta_id=venta.id
        )
        if mov is None:
            raise SeedError(f"No se pudo descontar el stock del libro {libro_id}")


async def comprobar_stock(session: AsyncSession) -> None:
    suma = func.coalesce(func.sum(MovimientoStock.cantidad), 0)
    stmt = (
        select(Libro.id, Libro.stock, suma)
        .outerjoin(MovimientoStock, MovimientoStock.libro_id == Libro.id)
        .group_by(Libro.id, Libro.stock)
        .order_by(Libro.id)
    )
    for libro_id, stock, movimientos in (await session.execute(stmt)).all():
        if stock != movimientos:
            raise SeedError(
                f"Libro {libro_id}: stock {stock} distinto de la suma de movimientos {movimientos}"
            )


async def resumen(session: AsyncSession) -> None:
    print("Datos iniciales cargados:")
    for tabla in SQLModel.metadata.sorted_tables:
        cantidad = (await session.execute(select(func.count()).select_from(tabla))).scalar_one()
        if cantidad:
            print(f"  {tabla.name:<18} {cantidad}")
    print("Usuarios de prueba (contraseñas de mentira, sólo para estos datos):")
    for email, _nombre, plano, rol, debe_cambiar in USUARIOS:
        extra = "  (debe cambiar la contraseña)" if debe_cambiar else ""
        print(f"  {email:<22} {plano:<14} {rol.value}{extra}")


async def main() -> None:
    settings = get_settings()  # falla nombrando la variable que falta, antes de tocar la base
    # Los hashes se calculan antes de abrir la transacción (bcrypt es lento).
    hashes = [await hashear_password(plano) for _e, _n, plano, _r, _d in USUARIOS]

    engine = create_engine(settings)
    try:
        session_factory = create_session_factory(engine)
        async with session_factory() as session, session.begin():
            await vaciar(session)
            libros = await cargar_catalogo(session)
            await cargar_personas(session, hashes)
            await cargar_stock_y_venta(session, libros)
            session.add(EventoSeguridad(actor=ACTOR_SISTEMA, accion="Carga de los datos iniciales"))
            await session.flush()
            await comprobar_stock(session)
            await resumen(session)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except SeedError as exc:
        print(f"ERROR: {exc}. No se escribió nada.", file=sys.stderr)
        sys.exit(1)
