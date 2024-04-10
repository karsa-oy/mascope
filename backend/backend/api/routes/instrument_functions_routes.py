from fastapi import APIRouter, Depends
from ..utils.api_features import api_route
from ..controllers.instrument_functions_controller import (
    get_instrument_functions,
    get_instrument_function,
    create_instrument_function,
    delete_instrument_function,
)
from ..models.pydantic_models.instrument_function_pydantic_model import (
    GetInstrumentFunctionsQueryParams,
    GetInstrumentFunctionQueryParams,
    InstrumentFunctionCreateBody,
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


@instrument_functions_router.post("/api/instrument_functions")
@api_route(
    status_code_success=201,
    include_message=True,
    success_message="Instrument function created successfully",
)
async def create_instrument_function_route(body: InstrumentFunctionCreateBody):
    return await create_instrument_function(instrument_function_data=body)


@instrument_functions_router.delete(
    "/api/instrument_functions/{instrument_function_id}"
)
@api_route(
    include_data=False,
    include_message=True,
    success_message="Instrument function deleted successfully",
)
async def delete_instrument_function_route(instrument_function_id: str):
    return await delete_instrument_function(instrument_function_id)
