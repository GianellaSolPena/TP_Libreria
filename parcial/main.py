import logging
import secrets
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core import security
from app.core.config import get_settings
from app.core.database import create_engine, create_session_factory
from app.modules import models as _modelos  # noqa: F401  (registra TODOS los mapeos, incl. usuarios)
from app.modules.autores.router import router as autores_router
from app.modules.clientes.router import router as clientes_router
from app.modules.editoriales.router import router as editoriales_router
from app.modules.generos.router import router as generos_router
from app.modules.health.router import router as health_router
from app.modules.libros.router import router as libros_router
from app.modules.usuarios.router import router as auth_router
from app.modules.ventas.router import router as ventas_router


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

app.include_router(health_router)
app.include_router(autores_router)
app.include_router(clientes_router)
app.include_router(editoriales_router)
app.include_router(generos_router)
app.include_router(libros_router)
app.include_router(auth_router)
app.include_router(ventas_router)
