from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session_tp as get_session
from app.core.dependencies import solo_admin
from app.modules.libros import service
from app.modules.libros.schemas import (
    LibroCreate,
    LibroDetalleRead,
    LibroRead,
    LibroUpdate,
)

# GET sin sesion; escrituras solo ADMIN (matriz de 03). Misma logica del TP hasta C-07.
router_publico = APIRouter(prefix="/libros", tags=["libros"])
router_admin = APIRouter(prefix="/libros", tags=["libros"], dependencies=[Depends(solo_admin)])


@router_admin.post("/", response_model=LibroDetalleRead, status_code=status.HTTP_201_CREATED)
async def crear_libro(
    datos: LibroCreate, session: AsyncSession = Depends(get_session)
) -> LibroDetalleRead:
    return await service.crear(session, datos)


@router_publico.get("/", response_model=list[LibroRead])
async def listar_libros(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    titulo: str | None = Query(None),
    genero_id: int | None = Query(None),
    session: AsyncSession = Depends(get_session),
) -> list[LibroRead]:
    return await service.listar(session, limit, offset, titulo, genero_id)


@router_publico.get("/{libro_id}", response_model=LibroDetalleRead)
async def obtener_libro(
    libro_id: int, session: AsyncSession = Depends(get_session)
) -> LibroDetalleRead:
    return await service.obtener(session, libro_id)


@router_admin.patch("/{libro_id}", response_model=LibroDetalleRead)
async def actualizar_libro(
    libro_id: int, datos: LibroUpdate, session: AsyncSession = Depends(get_session)
) -> LibroDetalleRead:
    return await service.actualizar(session, libro_id, datos)
