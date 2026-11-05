from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.database import get_session
from app.core.dependencies import UsuarioActualDep, solo_admin
from app.core.errores import MENSAJE_GENERICO, IdPath, traducir_errores
from app.core.paginacion import Pagina, PaginaDep
from app.core.security import borrar_cookie_sesion, poner_cookie_sesion
from app.modules.usuarios import service
from app.modules.usuarios.schemas import (
    AsignacionRead,
    AsignarRolIn,
    CambiarPasswordIn,
    EventoRead,
    LoginIn,
    LoginOut,
    MensajeOut,
    PersonalIn,
    RegistroIn,
    UsuarioRead,
    YoOut,
)
from app.modules.usuarios.models import Rol
from app.modules.usuarios.unit_of_work import (
    IntentosAccesoUnitOfWork,
    UsuariosUnitOfWork,
)

router = APIRouter(prefix="/auth", tags=["auth"])

router_usuarios = APIRouter(
    prefix="/usuarios", tags=["usuarios"], dependencies=[Depends(solo_admin)]
)
router_eventos = APIRouter(
    prefix="/eventos", tags=["eventos"], dependencies=[Depends(solo_admin)]
)

CONFLICTO_ALTA_PERSONAL = "Ya existe un usuario con ese correo"
CONFLICTO_ROL = "El usuario ya tiene ese rol vigente"
CONFLICTO_REGISTRO = "Ya existe una cuenta o un cliente con ese correo"


def get_uow(session: Annotated[AsyncSession, Depends(get_session)]) -> UsuariosUnitOfWork:
    return UsuariosUnitOfWork(session)


def get_intentos_uow(request: Request) -> IntentosAccesoUnitOfWork:
    session_factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    return IntentosAccesoUnitOfWork(session_factory)


UowDep = Annotated[UsuariosUnitOfWork, Depends(get_uow)]
IntentosUowDep = Annotated[IntentosAccesoUnitOfWork, Depends(get_intentos_uow)]


@router.post("/registro", response_model=UsuarioRead, status_code=status.HTTP_201_CREATED)
async def registro(datos: RegistroIn, uow: UowDep) -> UsuarioRead:
    with traducir_errores(CONFLICTO_REGISTRO):
        return await service.registrar(uow, datos)


@router.post("/login", response_model=LoginOut)
async def login(
    datos: LoginIn,
    request: Request,
    response: Response,
    uow: UowDep,
    intentos_uow: IntentosUowDep,
) -> LoginOut:
    ip = request.client.host if request.client is not None else "desconocida"
    with traducir_errores(MENSAJE_GENERICO):
        resultado = await service.login(
            uow, intentos_uow, datos, ip, request.app.state.hash_ficticio
        )
    poner_cookie_sesion(response, resultado.token)
    return LoginOut(
        mensaje="Sesión iniciada",
        debe_cambiar_password=resultado.debe_cambiar_password,
        expira_en_segundos=resultado.expira_en_segundos,
    )


@router.post("/logout", response_model=MensajeOut)
async def logout(response: Response) -> MensajeOut:
    borrar_cookie_sesion(response)
    return MensajeOut(mensaje="Sesión cerrada")


@router.get("/yo", response_model=YoOut)
async def yo(sesion: UsuarioActualDep) -> YoOut:
    return service.yo(sesion.usuario, sesion.roles_vigentes, sesion.roles_token)


@router.post("/cambiar-password", response_model=MensajeOut)
async def cambiar_password(
    datos: CambiarPasswordIn,
    sesion: UsuarioActualDep,
    uow: UowDep,
) -> MensajeOut:
    with traducir_errores(MENSAJE_GENERICO):
        await service.cambiar_password(uow, sesion.usuario, datos)
    return MensajeOut(mensaje="Contraseña actualizada")


@router_usuarios.post("", response_model=UsuarioRead, status_code=status.HTTP_201_CREATED)
async def alta_personal(
    datos: PersonalIn, sesion: UsuarioActualDep, uow: UowDep
) -> UsuarioRead:
    with traducir_errores(CONFLICTO_ALTA_PERSONAL):
        return await service.alta_personal(uow, sesion.usuario, datos)


@router_usuarios.get("/{usuario_id}/roles", response_model=list[AsignacionRead])
async def roles_de_usuario(usuario_id: IdPath, uow: UowDep) -> list[AsignacionRead]:
    with traducir_errores(CONFLICTO_ROL):
        return await service.roles_de_usuario(uow, usuario_id)


@router_usuarios.post(
    "/{usuario_id}/roles",
    response_model=AsignacionRead,
    status_code=status.HTTP_201_CREATED,
)
async def asignar_rol(
    usuario_id: IdPath, datos: AsignarRolIn, sesion: UsuarioActualDep, uow: UowDep
) -> AsignacionRead:
    with traducir_errores(CONFLICTO_ROL):
        return await service.asignar_rol(uow, sesion.usuario, usuario_id, datos)


@router_usuarios.delete("/{usuario_id}/roles/{rol}", response_model=AsignacionRead)
async def revocar_rol(
    usuario_id: IdPath, rol: Rol, sesion: UsuarioActualDep, uow: UowDep
) -> AsignacionRead:
    with traducir_errores(CONFLICTO_ROL):
        return await service.revocar_rol(uow, sesion.usuario, usuario_id, rol)


@router_eventos.get("", response_model=Pagina[EventoRead])
async def listar_eventos(pagina: PaginaDep, uow: UowDep) -> Pagina[EventoRead]:
    with traducir_errores(CONFLICTO_ROL):
        return await service.listar_eventos(uow, pagina.page, pagina.size)
