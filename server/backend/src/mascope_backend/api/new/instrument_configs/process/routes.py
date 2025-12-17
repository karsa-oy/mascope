from fastapi import APIRouter, Depends, BackgroundTasks
from mascope_backend.db.id import gen_id
from mascope_backend.api.lib.api_features import api_route
from mascope_backend.api.controllers.sample.lib.sample_file_fetch import (
    fetch_sample_file,
)
from mascope_backend.api.new.auth.dependencies import editor_user
from mascope_backend.api.new.instrument_configs.service import get_instrument_config
from mascope_backend.api.new.instrument_configs.process.service import (
    process_instrument_config,
)
from mascope_backend.api.new.instrument_configs.process.schemas import (
    ProcessInstrumentConfigBody,
)

instrument_configs_process_router = APIRouter(
    prefix="/api/instrument_configs/process", tags=["Instrument Configs"]
)


@instrument_configs_process_router.post("")
@api_route(status_code=202)
async def process_instrument_config_route(
    body: ProcessInstrumentConfigBody,
    background_tasks: BackgroundTasks,
    user=Depends(editor_user),
):
    """
    Initiates processing of instrument functions for a given sample file and method file.

    This route is used to process and associate instrument functions with a specified sample file.
    Depending on the provided inputs, the route supports the following scenarios:

    Scenarios:
    1. Using an existing instrument config:
      - Specify `body.instrument_config.instrument_function_id` to use an existing instrument config from the database.
    2. Creating a new instrument config with automated fit:
      - Specify `body.instrument_config.new_record` with a `method_file` field and without other fields to
        create a new instrument config and fit instrument functions automatically.
    3. Creating a new instrument config with user-provided fit:
      - Specify a `body.instrument_config.new_record` with `resolution_function` and `method_file` to create
        a new instrument config and associate user-provided instrument functions with the sample file.

    :param body: The request body containing details of the sample file, method file, and optional
                 instrument functions.
    :type body: ProcessInstrumentConfigBody
    :param background_tasks: The background task manager to queue the instrument function processing task.
    :type background_tasks: BackgroundTasks
    :param user: The authenticated user, restricted to editor-level access or higher.
    :type user: User, optional
    :return: A response containing a message and a unique process ID for tracking the background task.
    :rtype: dict
    """
    # verify filename and instrument config exists
    await fetch_sample_file(filename=body.filename)
    if body.instrument_config.instrument_function_id is not None:
        await get_instrument_config(
            instrument_function_id=body.instrument_config.instrument_function_id
        )
    process_id = gen_id(8)
    background_tasks.add_task(
        process_instrument_config,
        filenames=[body.filename],
        instrument_config=body.instrument_config,
        independent_transaction=True,
        user_id=user.id,
        process_id=process_id,
    )
    return {
        "message": f"Processing instrument configs for {body.filename}",
        "process_id": process_id,
    }
