from fastapi import APIRouter, Depends
from ..utils.api_features import api_route
from ..controllers.instrument_functions_controller import (
    get_instrument_functions,
    get_instrument_function,
)
from ..models.pydantic_models.instrument_function_pydantic_model import (
    GetInstrumentFunctionsQueryParams,
    GetInstrumentFunctionQueryParams,
)

instrument_functions_router = APIRouter()


@instrument_functions_router.get("/api/instrument_functions")
@api_route()
async def get_instrument_functions_route(
    query_params: GetInstrumentFunctionsQueryParams = Depends(),
):
    return await get_instrument_functions(**query_params.dict())


@instrument_functions_router.get("/api/instrument_functions/")
@api_route()
async def get_instrument_function_route(
    query_params: GetInstrumentFunctionQueryParams = Depends(),
):
    return await get_instrument_function(
        filename=query_params.filename,
        instrument_function_id=query_params.instrument_function_id,
    )
