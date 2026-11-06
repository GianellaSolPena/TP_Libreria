import asyncio
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any, TypedDict

import bcrypt
import jwt
from fastapi import Response
from pydantic import AfterValidator, StringConstraints

from app.core.config import get_settings
from app.core.validacion import rechazar_nulo

COOKIE_SESION = "access_token"

# Como maximo, esta cantidad de operaciones bcrypt simultaneas. El PDF solo pide
# que el costo sea configurable; la concurrencia es una constante comentada.
BCRYPT_CONCURRENTES = 4
_SEMAFORO = asyncio.Semaphore(BCRYPT_CONCURRENTES)


def _max_72_bytes(valor: str) -> str:
    if len(valor.encode("utf-8")) > 72:
        raise ValueError("La contrasena no puede superar los 72 bytes en UTF-8")
    return valor


# bcrypt rechaza mas de 72 bytes: el contrato lo valida antes de llegar a la base.
PasswordBcrypt = Annotated[
    str,
    AfterValidator(rechazar_nulo),
    StringConstraints(min_length=1),
    AfterValidator(_max_72_bytes),
]


async def hashear_password(plano: str) -> str:
    settings = get_settings()
    salt = bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)
    async with _SEMAFORO:
        return (await asyncio.to_thread(bcrypt.hashpw, plano.encode("utf-8"), salt)).decode(
            "utf-8"
        )


async def verificar_password(plano: str, hash_guardado: str) -> bool:
    async with _SEMAFORO:
        return await asyncio.to_thread(
            bcrypt.checkpw, plano.encode("utf-8"), hash_guardado.encode("utf-8")
        )


class PayloadToken(TypedDict):
    sub: int
    roles: list[str]


def crear_token(usuario_id: int, roles: list[str]) -> str:
    settings = get_settings()
    payload = {
        "sub": str(usuario_id),
        "exp": datetime.now(UTC) + timedelta(seconds=settings.ACCESS_TOKEN_EXPIRE_SECONDS),
        "roles": list(roles),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")


def leer_token(token: str) -> PayloadToken | None:
    settings = get_settings()
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=["HS256"],
            options={"require": ["sub", "exp"]},
        )
    except jwt.InvalidTokenError:
        return None

    sub = payload.get("sub")
    if not isinstance(sub, str):
        return None
    try:
        usuario_id = int(sub)
    except ValueError:
        return None

    roles = payload.get("roles", [])
    if not isinstance(roles, list) or not all(isinstance(rol, str) for rol in roles):
        return None

    return {"sub": usuario_id, "roles": list(roles)}


def poner_cookie_sesion(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        COOKIE_SESION,
        token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_SECONDS,
        httponly=True,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
        path="/",
    )


def borrar_cookie_sesion(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        COOKIE_SESION,
        httponly=True,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
        path="/",
    )
