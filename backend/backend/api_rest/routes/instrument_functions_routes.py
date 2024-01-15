from fastapi import APIRouter, Query, HTTPException
from ..controllers.instrument_functions_controller import (
    get_instrument_functions,
    get_instrument_function,
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


@instrument_functions_router.get("/api/instrument_functions/")
async def get_instrument_function_route(
    filename: str = Query(
        None,
        description="The filename to query for the last instrument function of the instrument",
    ),
    instrument_function_id: str = Query(
        None, description="The instrument function ID to query for"
    ),
):
    if (instrument_function_id and filename) or (
        not instrument_function_id and not filename
    ):
        raise HTTPException(
            status_code=400,
            detail="Must provide either filename either instrument_function_id.",
        )
    return await get_instrument_function(
        filename=filename, instrument_function_id=instrument_function_id
    )
