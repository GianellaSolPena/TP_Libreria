import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.core import security
from app.core.config import get_settings
from app.core.errores import (
    Conflicto,
    CredencialesInvalidas,
    DemasiadosIntentos,
    NoEncontrado,
    PaginaInexistente,
)
from app.core.paginacion import Pagina, calcular_offset, calcular_paginas
from app.modules.clientes.models import Cliente
from app.modules.usuarios.models import (
    AsignacionRol,
    EventoSeguridad,
    IntentoAcceso,
    Rol,
    Usuario,
)
from app.modules.usuarios.schemas import (
    AsignacionRead,
    AsignarRolIn,
    CambiarPasswordIn,
    EventoRead,
    LoginIn,
    PersonalIn,
    RegistroIn,
    UsuarioRead,
    YoOut,
)
from app.modules.usuarios.unit_of_work import (
    IntentosAccesoUnitOfWork,
    UsuariosUnitOfWork,
)

MAX_FALLOS = 5
VENTANA = timedelta(seconds=60)


@dataclass
class ResultadoLogin:
    token: str
    debe_cambiar_password: bool
    expira_en_segundos: int


async def registrar(uow: UsuariosUnitOfWork, datos: RegistroIn) -> Usuario:
    # bcrypt antes de abrir la transaccion que guarda el hash.
    password_hash = await security.hashear_password(datos.password)
    async with uow:
        usuario = await uow.usuarios.add(
            Usuario(email=datos.email, nombre=datos.nombre, password_hash=password_hash)
        )
        await uow.asignaciones.add(
            AsignacionRol(usuario_id=usuario.id, rol=Rol.CLIENTE)
        )
        await uow.clientes.add(
            Cliente(nombre=datos.nombre, email=datos.email, usuario_id=usuario.id)
        )
        return usuario


async def login(
    uow: UsuariosUnitOfWork,
    intentos_uow: IntentosAccesoUnitOfWork,
    datos: LoginIn,
    ip: str,
    hash_ficticio: str,
) -> ResultadoLogin:
    ahora = datetime.now(UTC)

    # Bloque 1: solo lecturas. Limite primero (429 sin hash ni registro).
    async with uow:
        fallos = await uow.intentos.fallos_recientes(datos.email, ip, ahora)
        if len(fallos) >= MAX_FALLOS:
            restante = (fallos[-1] + VENTANA - ahora).total_seconds()
            raise DemasiadosIntentos(max(1, math.ceil(restante)))
        usuario = await uow.usuarios.get_by_email(datos.email)

    # Fuera del bloque: la conexion volvio al pool durante el hash.
    hash_a_verificar = usuario.password_hash if usuario is not None else hash_ficticio
    ok = await security.verificar_password(datos.password, hash_a_verificar)
    exito = ok and usuario is not None and usuario.activo

    # Siempre se registra el intento, en su propia sesion y transaccion.
    async with intentos_uow:
        if intentos_uow.intentos is None:
            raise RuntimeError("UoW de intentos sin repositorio inicializado")
        await intentos_uow.intentos.add(
            IntentoAcceso(email=datos.email, ip=ip, exito=exito, cuando=ahora)
        )

    if not exito:
        raise CredencialesInvalidas("Correo o contraseña incorrectos")

    # Bloque 2: roles solo en el exito.
    async with uow:
        roles = await uow.asignaciones.roles_vigentes(usuario.id)

    settings = get_settings()
    token = security.crear_token(usuario.id, [rol.value for rol in roles])
    return ResultadoLogin(
        token=token,
        debe_cambiar_password=usuario.debe_cambiar_password,
        expira_en_segundos=settings.ACCESS_TOKEN_EXPIRE_SECONDS,
    )


def yo(usuario: Usuario, roles_vigentes: list[Rol], roles_token: list[str]) -> YoOut:
    """Arma la respuesta con lo que ya leyo `get_usuario_actual` (sin otro bloque)."""
    return YoOut(
        usuario=UsuarioRead.model_validate(usuario),
        roles_vigentes=roles_vigentes,
        roles_token=roles_token,
    )


async def cambiar_password(
    uow: UsuariosUnitOfWork, usuario: Usuario, datos: CambiarPasswordIn
) -> None:
    ok = await security.verificar_password(datos.password_actual, usuario.password_hash)
    if not ok:
        raise CredencialesInvalidas("La contraseña actual no es correcta")

    nuevo_hash = await security.hashear_password(datos.password_nueva)

    async with uow:
        actual = await uow.usuarios.get_by_id(usuario.id)
        if actual is None:
            raise RuntimeError("Usuario autenticado inexistente al cambiar la contraseña")
        await uow.usuarios.update(
            actual,
            {
                "password_hash": nuevo_hash,
                "debe_cambiar_password": False,
            },
        )
        await uow.eventos.add(
            EventoSeguridad(actor=actual.email, accion="Cambio de contraseña")
        )


def _a_lectura(asignacion: AsignacionRol, ahora: datetime) -> AsignacionRead:
    """`vigente` se calcula con el `ahora` de la operacion, no con otro reloj."""
    vigente = asignacion.revocada_en is None and (
        asignacion.vence_en is None or asignacion.vence_en > ahora
    )
    return AsignacionRead(**asignacion.model_dump(), vigente=vigente)


async def alta_personal(
    uow: UsuariosUnitOfWork, actor: Usuario, datos: PersonalIn
) -> Usuario:
    """RN-16: usuario con cambio pendiente + rol + evento, todo en un bloque."""
    # bcrypt antes de abrir la transaccion.
    password_hash = await security.hashear_password(datos.password)
    ahora = datetime.now(UTC)
    async with uow:
        usuario = await uow.usuarios.add(
            Usuario(
                email=datos.email,
                nombre=datos.nombre,
                password_hash=password_hash,
                debe_cambiar_password=True,
            )
        )
        await uow.asignaciones.add(
            AsignacionRol(
                usuario_id=usuario.id,
                rol=datos.rol,
                desde=ahora,
                otorgada_por=actor.id,
            )
        )
        await uow.eventos.add(
            EventoSeguridad(
                actor=actor.email,
                accion=f"Alta de personal {usuario.email} con rol {datos.rol.value}",
            )
        )
        return usuario


async def roles_de_usuario(uow: UsuariosUnitOfWork, usuario_id: int) -> list[AsignacionRead]:
    ahora = datetime.now(UTC)
    async with uow:
        if await uow.usuarios.get_by_id(usuario_id) is None:
            raise NoEncontrado("Usuario no encontrado")
        asignaciones = await uow.asignaciones.listar_de_usuario(usuario_id)
        return [_a_lectura(a, ahora) for a in asignaciones]


async def asignar_rol(
    uow: UsuariosUnitOfWork, actor: Usuario, usuario_id: int, datos: AsignarRolIn
) -> AsignacionRead:
    """RN-03 la garantiza el indice unico parcial: sin comprobacion previa de vigencia."""
    ahora = datetime.now(UTC)
    async with uow:
        usuario = await uow.usuarios.get_by_id(usuario_id)
        if usuario is None:
            raise NoEncontrado("Usuario no encontrado")
        abierta = await uow.asignaciones.get_abierta(usuario_id, datos.rol)
        if abierta is not None and abierta.vence_en is not None and abierta.vence_en <= ahora:
            # El UPDATE llega a la base antes del INSERT y libera el indice parcial.
            await uow.asignaciones.update(abierta, {"revocada_en": ahora})
        nueva = await uow.asignaciones.add(
            AsignacionRol(
                usuario_id=usuario_id,
                rol=datos.rol,
                desde=ahora,
                vence_en=datos.vence_en,
                otorgada_por=actor.id,
            )
        )
        accion = f"Asignación de rol {datos.rol.value} a {usuario.email}"
        if datos.vence_en is not None:
            accion += f" hasta {datos.vence_en.isoformat()}"
        await uow.eventos.add(EventoSeguridad(actor=actor.email, accion=accion))
        return _a_lectura(nueva, ahora)


async def revocar_rol(
    uow: UsuariosUnitOfWork, actor: Usuario, usuario_id: int, rol: Rol
) -> AsignacionRead:
    """RN-05: ni autorrevocarse ni dejar el sistema sin ADMIN vigentes."""
    ahora = datetime.now(UTC)
    async with uow:
        usuario = await uow.usuarios.get_by_id(usuario_id)
        if usuario is None:
            raise NoEncontrado("Usuario no encontrado")
        vigente = await uow.asignaciones.get_vigente(usuario_id, rol, ahora)
        if vigente is None:
            raise NoEncontrado("El usuario no tiene ese rol vigente")
        if rol == Rol.ADMIN:
            if usuario_id == actor.id:
                raise Conflicto("No podés revocarte tu propio rol ADMIN")
            admins = await uow.asignaciones.admins_vigentes_bloqueando(ahora)
            if not any(a.usuario_id != usuario_id for a in admins):
                raise Conflicto("El sistema no puede quedar sin administradores vigentes")
        revocada = await uow.asignaciones.update(vigente, {"revocada_en": ahora})
        await uow.eventos.add(
            EventoSeguridad(
                actor=actor.email,
                accion=f"Revocación de rol {rol.value} a {usuario.email}",
            )
        )
        return _a_lectura(revocada, ahora)


async def listar_eventos(
    uow: UsuariosUnitOfWork, page: int, size: int
) -> Pagina[EventoRead]:
    async with uow:
        total = await uow.eventos.count()
        pages = calcular_paginas(total, size)
        if page > pages:
            raise PaginaInexistente(page, pages)
        eventos = await uow.eventos.listar_recientes(calcular_offset(page, size), size)
        return Pagina[EventoRead](
            items=[EventoRead.model_validate(e) for e in eventos],
            total=total,
            page=page,
            size=size,
            pages=pages,
        )
