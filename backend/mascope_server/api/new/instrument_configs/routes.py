from fastapi import APIRouter, Depends, BackgroundTasks, Request

from mascope_server.db.id import gen_id
from mascope_server.api.new.auth.dependencies import editor_user, guest_user
from mascope_server.api.lib.api_features import api_route
from mascope_server.api.controllers.sample.lib.sample_file_fetch import (
    fetch_sample_file,
)

from mascope_server.api.new.instrument_configs.service import (
    get_instrument_configs,
    get_instrument_config,
    create_instrument_config,
    delete_instrument_config,
    fit_instrument_config,
)
from mascope_server.api.new.instrument_configs.schemas import (
    GetInstrumentConfigsQueryParams,
    CreateInstrumentConfigBody,
    FitInstrumentConfigBody,
)


instrument_configs_router = APIRouter(
    prefix="/api/instrument_configs", tags=["Instrument Configs"]
)


@instrument_configs_router.get("")
@api_route()
async def get_instrument_configs_route(
    query_params: GetInstrumentConfigsQueryParams = Depends(),
    user=Depends(guest_user),
):
    """
    Retrieve a list of instrument functions.

    :param query_params: Query parameters for filtering, sorting, and pagination.
    :type query_params: GetInstrumentConfigsQueryParams
    :param user: The current authenticated user (guest or higher).
    :type user: User
    :return: A list of instrument functions and the total count.
    :rtype: dict
    """
    return await get_instrument_configs(**query_params.model_dump())


@instrument_configs_router.get("/by_filename/{filename}")
@api_route()
async def get_instrument_config_by_filename_route(
    filename: str,
    user=Depends(guest_user),
):
    """
    Retrieve details of a specific instrument config by a sample filename.

    :param filename: The filename for which to retrieve the instrument config.
    :type filename: str
    :return: The requested instrument function's details.
    :rtype: dict
    """
    return await get_instrument_config(
        filename=filename,
    )


@instrument_configs_router.get("/by_id/{instrument_function_id}")
@api_route()
async def get_instrument_config_by_id_route(
    instrument_function_id: str,
    user=Depends(guest_user),
):
    """
    Retrieve details of a specific instrument config by its instrument function id.

    :param instrument_function_id: The unique identifier of the instrument config to retrieve.
    :type instrument_function_id: str
    :return: The requested instrument function's details.
    :rtype: dict
    """
    return await get_instrument_config(
        instrument_function_id=instrument_function_id,
    )


@instrument_configs_router.post("")
@api_route(status_code=201, token_access=True)
async def create_instrument_config_route(
    body: CreateInstrumentConfigBody,
    user=Depends(editor_user),
):
    """Create a new instrument function.

    :param body: The data required to create a new instrument function.
    :type body: InstrumentConfigCreateBody
    :param user: The current authenticated user, defaults to Depends(editor_user).
    :type user: User, optional
    :return: A dictionary containing the details of the created instrument function.
    :rtype: dict
    """
    return await create_instrument_config(instrument_config=body)


@instrument_configs_router.delete("/{instrument_function_id}")
@api_route()
async def delete_instrument_config_route(
    instrument_function_id: str,
    user=Depends(editor_user),
):
    """Delete a specific instrument function by ID.

    :param instrument_function_id: The unique identifier of the instrument function to delete.
    :type instrument_function_id: str
    :param user: The current authenticated user, defaults to Depends(editor_user).
    :type user: User, optional
    """
    return await delete_instrument_config(instrument_function_id)


@instrument_configs_router.post("/fit")
@api_route(status_code=202)
async def fit_instrument_config_route(
    request: Request,
    body: FitInstrumentConfigBody,
    background_tasks: BackgroundTasks,
    user=Depends(editor_user),
):
    """Fit instrument functions for a specific sample file.

    :param request: The request object.
    :type request: Request
    :param body: The details required for fitting instrument functions.
    :type body: FitInstrumentConfigBody
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
        fit_instrument_config,
        sample_file=sample_file,
        fit_params=body.instrument_config_params,
        independent_transaction=True,
        sid=request.headers.get("X-SID"),
        process_id=process_id,
    )
    return {
        "message": f"Fitting instrument config for {body.filename}, this can take a moment.",
        "process_id": process_id,
    }
