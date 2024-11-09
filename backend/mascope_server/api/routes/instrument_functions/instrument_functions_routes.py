from fastapi import APIRouter, Depends
from mascope_server.api.lib.api_features import api_route
from mascope_server.api.controllers.sample.lib.sample_file_fetch import (
    fetch_sample_file,
)
from mascope_server.api.controllers.instrument_functions.instrument_functions_controller import (
    get_instrument_functions,
    get_instrument_function,
    get_method_files,
    create_instrument_function,
    delete_instrument_function,
    instrument_functions_fit,
)
from mascope_server.api.models.instrument_functions.instrument_function_pydantic_model import (
    GetInstrumentFunctionsQueryParams,
    GetInstrumentFunctionQueryParams,
    GetMethodFilesQueryParams,
    InstrumentFunctionCreateBody,
    FitInstrumentFunctionsBody,
)


instrument_functions_router = APIRouter()


@instrument_functions_router.get("/api/instrument_functions")
@api_route()
async def get_instrument_functions_route(
    query_params: GetInstrumentFunctionsQueryParams = Depends(),
):
    """
    Get multiple instrument functions
    """
    return await get_instrument_functions(**query_params.model_dump())


@instrument_functions_router.get("/api/instrument_functions/")
@api_route()
async def get_instrument_function_route(
    query_params: GetInstrumentFunctionQueryParams = Depends(),
):
    """
    Get one instrument function
    """
    return await get_instrument_function(
        filename=query_params.filename,
        instrument_function_id=query_params.instrument_function_id,
    )


@instrument_functions_router.get("/api/instrument_functions/method_files")
@api_route()
async def get_method_files_route(
    query_params: GetMethodFilesQueryParams = Depends(),
):
    return await get_method_files(filename=query_params.filename)


@instrument_functions_router.post("/api/instrument_functions")
@api_route(
    status_code=201,
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


@instrument_functions_router.post("/api/instrument_functions/fit")
@api_route(
    status_code=200,
)
async def fit_instrument_functions_route(body: FitInstrumentFunctionsBody):
    sample_file = await fetch_sample_file(filename=body.filename)
    return await instrument_functions_fit(sample_file=sample_file, params=body.params)
