from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.database import get_session
from app.core.dependencies import UsuarioActualDep
from app.core.errores import MENSAJE_GENERICO, traducir_errores
from app.core.security import borrar_cookie_sesion, poner_cookie_sesion
from app.modules.usuarios import service
from app.modules.usuarios.schemas import (
    CambiarPasswordIn,
    LoginIn,
    LoginOut,
    MensajeOut,
    RegistroIn,
    UsuarioRead,
    YoOut,
)
from app.modules.usuarios.unit_of_work import (
    IntentosAccesoUnitOfWork,
    UsuariosUnitOfWork,
)

router = APIRouter(prefix="/auth", tags=["auth"])

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
async def yo(sesion: UsuarioActualDep, uow: UowDep) -> YoOut:
    return await service.yo(uow, sesion.usuario, sesion.roles_token)


@router.post("/cambiar-password", response_model=MensajeOut)
async def cambiar_password(
    datos: CambiarPasswordIn,
    sesion: UsuarioActualDep,
    uow: UowDep,
) -> MensajeOut:
    with traducir_errores(MENSAJE_GENERICO):
        await service.cambiar_password(uow, sesion.usuario, datos)
    return MensajeOut(mensaje="Contraseña actualizada")
