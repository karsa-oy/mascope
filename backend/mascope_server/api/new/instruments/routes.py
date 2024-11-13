from .service import get_instruments

from mascope_server.api.lib.api_features import api_route

from fastapi import APIRouter


instruments_router = APIRouter()


@instruments_router.get("/api/instruments")
@api_route(
    status_code=200,
)
async def get_instruments_route():
    return await get_instruments()
