from fastapi import APIRouter
from ..controllers.instrument_functions_controller import (
    get_instrument_function_by_id,
    get_instrument_functions,
)

instrument_functions_router = APIRouter()


@instrument_functions_router.get("/api/instrument_functions")
async def get_instrument_functions_route(
    instrument: str = None,
    sort: str = None,
    order: str = None,
    page: int = 0,
    limit: int = 100,
):
    return await get_instrument_functions(instrument, sort, order, page, limit)


@instrument_functions_router.get("/api/instrument_functions/{instrument_function_id}")
async def get_instrument_function_by_id_route(instrument_function_id: str):
    return await get_instrument_function_by_id(instrument_function_id)
