from fastapi import APIRouter, Depends, BackgroundTasks, Request
from mascope_server.db.id import gen_id
from mascope_server.api.new.auth.dependencies import editor_user, guest_user
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


instrument_functions_router = APIRouter(
    prefix="/api/instrument_functions", tags=["Instrument Functions"]
)


@instrument_functions_router.get("")
@api_route()
async def get_instrument_functions_route(
    query_params: GetInstrumentFunctionsQueryParams = Depends(),
    user=Depends(guest_user),
):
    """
    Retrieve a list of instrument functions.

    :param query_params: Query parameters for filtering, sorting, and pagination.
    :type query_params: GetInstrumentFunctionsQueryParams
    :param user: The current authenticated user (guest or higher).
    :type user: User
    :return: A list of instrument functions and the total count.
    :rtype: dict
    """
    return await get_instrument_functions(**query_params.model_dump())


@instrument_functions_router.get("")
@api_route()
async def get_instrument_function_route(
    query_params: GetInstrumentFunctionQueryParams = Depends(),
    user=Depends(guest_user),
):
    """
    Retrieve details of a specific instrument function.

    :param query_params: Query parameters specifying the instrument function to retrieve.
    :type query_params: GetInstrumentFunctionQueryParams
    :return: The requested instrument function's details.
    :rtype: dict
    """
    return await get_instrument_function(
        filename=query_params.filename,
        instrument_function_id=query_params.instrument_function_id,
    )


@instrument_functions_router.get("/method_files")
@api_route()
async def get_method_files_route(
    query_params: GetMethodFilesQueryParams = Depends(),
    user=Depends(guest_user),
):
    """Retrieve a list of method files based on filename.

    :param query_params: Query parameters including filename.
    :type query_params: GetMethodFilesQueryParams
    :param user: The current authenticated user, defaults to Depends(guest_user).
    :type user: User, optional
    :return: A dictionary containing the list of method files.
    :rtype: dict
    """
    return await get_method_files(filename=query_params.filename)


@instrument_functions_router.post("")
@api_route(status_code=201, jupyter_access=True)
async def create_instrument_function_route(
    body: InstrumentFunctionCreateBody,
    user=Depends(editor_user),
):
    """Create a new instrument function.

    :param body: The data required to create a new instrument function.
    :type body: InstrumentFunctionCreateBody
    :param user: The current authenticated user, defaults to Depends(editor_user).
    :type user: User, optional
    :return: A dictionary containing the details of the created instrument function.
    :rtype: dict
    """
    return await create_instrument_function(instrument_function_data=body)


@instrument_functions_router.delete("/{instrument_function_id}")
@api_route()
async def delete_instrument_function_route(
    instrument_function_id: str,
    user=Depends(editor_user),
):
    """Delete a specific instrument function by ID.

    :param instrument_function_id: The unique identifier of the instrument function to delete.
    :type instrument_function_id: str
    :param user: The current authenticated user, defaults to Depends(editor_user).
    :type user: User, optional
    """
    return await delete_instrument_function(instrument_function_id)


@instrument_functions_router.post("/fit")
@api_route(status_code=202)
async def fit_instrument_functions_route(
    request: Request,
    body: FitInstrumentFunctionsBody,
    background_tasks: BackgroundTasks,
    user=Depends(editor_user),
):
    """Fit instrument functions for a specific sample file.

    :param request: The request object.
    :type request: Request
    :param body: The details required for fitting instrument functions.
    :type body: FitInstrumentFunctionsBody
    :param background_tasks: Background tasks for asynchronous processing.
    :type background_tasks: BackgroundTasks
    :param user: The current authenticated user, defaults to Depends(editor_user).
    :type user: User, optional
    :return: A dictionary indicating the fitting process has started.
    :rtype: dict
    """
    process_id = gen_id(8)
    sample_file = await fetch_sample_file(filename=body.filename)
    background_tasks.add_task(
        instrument_functions_fit,
        sample_file=sample_file,
        instrument_function_params=body.instrument_function_params,
        independent_transaction=True,
        sid=request.headers.get("X-SID"),
        process_id=process_id,
    )
    return {
        "message": f"Fitting instrument functions for {body.filename}, this can take a moment.",
        "process_id": process_id,
    }
