from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import COOKIE_SESION, leer_token
from app.core.unit_of_work import UnitOfWork
from app.modules.usuarios.models import Usuario
from app.modules.usuarios.repository import UsuarioRepository


@dataclass
class SesionActual:
    usuario: Usuario
    roles_token: list[str]


async def get_usuario_actual(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SesionActual:
    """Usuario de la cookie `access_token`. Ignora el encabezado Bearer."""
    token = request.cookies.get(COOKIE_SESION)
    payload = leer_token(token) if token else None
    if payload is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "No autenticado")

    # Solo lectura: el UoW confirma al salir (no hay cambios) y libera la conexion
    # antes de que el servicio verifique la contrasena.
    async with UnitOfWork(session):
        usuario = await UsuarioRepository(session).get_by_id(payload["sub"])

    if usuario is None or not usuario.activo:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "No autenticado")

    return SesionActual(usuario=usuario, roles_token=payload["roles"])


UsuarioActualDep = Annotated[SesionActual, Depends(get_usuario_actual)]
