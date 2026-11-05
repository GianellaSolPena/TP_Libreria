from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import COOKIE_SESION, leer_token
from app.core.unit_of_work import UnitOfWork
from app.modules.usuarios.models import Rol, Usuario
from app.modules.usuarios.repository import AsignacionRolRepository, UsuarioRepository


@dataclass
class SesionActual:
    usuario: Usuario
    roles_vigentes: list[Rol]
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
    # antes de que el servicio verifique la contrasena. Los roles vigentes se leen
    # de la base en cada peticion (RN-04); los del token son solo informativos.
    roles_vigentes: list[Rol] = []
    async with UnitOfWork(session):
        usuario = await UsuarioRepository(session).get_by_id(payload["sub"])
        if usuario is not None and usuario.activo:
            roles_vigentes = await AsignacionRolRepository(session).roles_vigentes(usuario.id)

    if usuario is None or not usuario.activo:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "No autenticado")

    return SesionActual(
        usuario=usuario, roles_vigentes=roles_vigentes, roles_token=payload["roles"]
    )


UsuarioActualDep = Annotated[SesionActual, Depends(get_usuario_actual)]


def requiere_rol(*roles: Rol) -> Callable[..., Awaitable[SesionActual]]:
    """Fabrica de dependencias: 403 si el usuario no tiene alguno de `roles` vigente.

    Depende de `get_usuario_actual`, asi que el 401 siempre sale antes que el 403.
    Autoriza solo con los roles vigentes leidos de la base, nunca con los del token.
    """
    permitidos = set(roles)

    async def dependencia(sesion: UsuarioActualDep) -> SesionActual:
        if not permitidos & set(sesion.roles_vigentes):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No tenés permiso para esta operación")
        return sesion

    # Nombre legible al recorrer las rutas (p. ej. requiere_ADMIN).
    dependencia.__name__ = "requiere_" + "_".join(sorted(r.value for r in permitidos))
    return dependencia


# Una sola instancia por regla: FastAPI cachea cada dependencia por peticion.
solo_admin = requiere_rol(Rol.ADMIN)
personal = requiere_rol(Rol.VENDEDOR, Rol.ADMIN)


async def exigir_password_al_dia(sesion: UsuarioActualDep) -> None:
    """403 mientras el usuario tenga el cambio de contrasena pendiente."""
    if sesion.usuario.debe_cambiar_password:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Tenés que cambiar la contraseña antes de seguir"
        )
