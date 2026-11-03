import asyncio

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def live() -> dict[str, str]:
    return {"estado": "vivo"}


@router.get("/ready")
async def ready(request: Request):
    try:
        async with asyncio.timeout(3):
            async with request.app.state.engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(status_code=503, content={"estado": "no listo"})
    return {"estado": "ok"}
