import logging
import secrets
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI

from app.core import security
from app.core.config import get_settings
from app.core.database import create_engine, create_session_factory
from app.core.dependencies import exigir_password_al_dia
from app.modules import models as _modelos  # noqa: F401  (registra TODOS los mapeos, incl. usuarios)
from app.modules.autores import router as autores
from app.modules.clientes.router import router as clientes_router
from app.modules.editoriales import router as editoriales
from app.modules.generos import router as generos
from app.modules.health.router import router as health_router
from app.modules.libros import router as libros
from app.modules.usuarios.router import (
    router as auth_router,
    router_eventos,
    router_usuarios,
)
from app.modules.ventas.router import router_autenticado as ventas_autenticado
from app.modules.ventas.router import router_personal as ventas_personal


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    settings = get_settings()
    engine = create_engine(settings)
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)
    # Hash ficticio (costo = BCRYPT_ROUNDS) para igualar tiempos en el login (C-05).
    # Se calcula con el mismo camino (hilo + semáforo) que un hash real, sobre un
    # valor aleatorio que nadie conoce.
    app.state.hash_ficticio = await security.hashear_password(secrets.token_urlsafe(32))
    try:
        yield
    finally:
        await engine.dispose()


# Solo el logger de la app: con basicConfig en la raíz, echo=True de SQLAlchemy duplica cada consulta.
_app_logger = logging.getLogger("app")
_app_logger.setLevel(logging.INFO)
_handler = logging.StreamHandler()
_handler.setFormatter(logging.Formatter("%(levelname)s:     %(name)s - %(message)s"))
_app_logger.addHandler(_handler)
_app_logger.propagate = False

app = FastAPI(
    title="Librería",
    description="Catálogo, clientes y ventas",
    lifespan=lifespan,
)

# Dos grupos (D4). `protegido` declara UNA vez el control del cambio obligatorio de
# contrasena: FastAPI suma dependencias y no las resta, por eso /auth/cambiar-password
# vive en `abierto`. Una ruta nueva solo hereda el control si se incluye en `protegido`.
abierto = APIRouter()
protegido = APIRouter(dependencies=[Depends(exigir_password_al_dia)])

# Sin sesion (o con sesion pero sin control de cambio): salud, auth y GET del catalogo.
abierto.include_router(health_router)
abierto.include_router(auth_router)
abierto.include_router(editoriales.router_publico)
abierto.include_router(generos.router_publico)
abierto.include_router(autores.router_publico)
abierto.include_router(libros.router_publico)

# Con sesion, cambio de contrasena al dia y rol (declarado en cada router).
protegido.include_router(editoriales.router_admin)
protegido.include_router(generos.router_admin)
protegido.include_router(autores.router_admin)
protegido.include_router(libros.router_admin)
protegido.include_router(router_usuarios)
protegido.include_router(router_eventos)
protegido.include_router(clientes_router)
protegido.include_router(ventas_personal)
protegido.include_router(ventas_autenticado)

app.include_router(abierto)
app.include_router(protegido)
