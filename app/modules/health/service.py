from fastapi import Request

from app.core.database import run_select_one


async def check_database(request: Request) -> None:
    await run_select_one(request.app.state.engine)
