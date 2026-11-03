from fastapi import APIRouter, Request

from app.modules.health import service

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def live() -> dict[str, str]:
    return {"estado": "vivo"}


@router.get("/ready")
async def ready(request: Request) -> dict[str, str]:
    await service.check_database(request)
    return {"estado": "ok"}
