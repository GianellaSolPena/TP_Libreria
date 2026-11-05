import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.core import security
from app.core.config import get_settings
from app.core.errores import CredencialesInvalidas, DemasiadosIntentos
from app.modules.clientes.models import Cliente
from app.modules.usuarios.models import (
    AsignacionRol,
    EventoSeguridad,
    IntentoAcceso,
    Rol,
    Usuario,
)
from app.modules.usuarios.schemas import (
    CambiarPasswordIn,
    LoginIn,
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


async def yo(
    uow: UsuariosUnitOfWork, usuario: Usuario, roles_token: list[str]
) -> YoOut:
    async with uow:
        roles_vigentes = await uow.asignaciones.roles_vigentes(usuario.id)
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
