from fastapi import APIRouter
from mascope_server.api.lib.api_features import api_route

from .service import get_params

params_router = APIRouter()


@params_router.get("/api/params")
@api_route()
async def get_params_route():
    return await get_params()
