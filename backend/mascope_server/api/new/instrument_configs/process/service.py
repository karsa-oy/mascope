import asyncio

from mascope_server.socket import sio
from mascope_server.api.models.sample.files.sample_file_pydantic_model import (
    SampleFileUpdate,
)
from mascope_server.api.lib.api_features import (
    api_controller_background_task,
)
from mascope_server.socket.notifications import (
    UserNotification,
    emit_user_notification,
)
from mascope_server.api.controllers.sample.files.sample_files_controller import (
    update_sample_file,
)
from mascope_server.api.controllers.sample.lib.sample_file_fetch import (
    fetch_sample_file,
)
from mascope_server.api.controllers.sample.lib.sample_batches_fetch import (
    fetch_sample_batch_ids,
)
from mascope_server.api.new.instrument_configs.schemas import (
    CreateInstrumentConfigBody,
    SetInstrumentConfigBody,
)
from mascope_server.api.new.instrument_configs.service import (
    fit_instrument_config,
    create_instrument_config,
    get_instrument_config,
)
from mascope_server.runtime import runtime


@api_controller_background_task(
    success_notification_rooms=["sid"],
    error_notification_rooms=["sid"],
)
async def process_instrument_config(
    filenames: list[str],
    instrument_config: SetInstrumentConfigBody,
    fit_filename: str | None = None,
    independent_transaction: bool = None,
    sid=None,
    process_id=None,
    parent_id: str = None,
):
    """
    Conditionally fit and create instrument functions for a sample file.

    Steps:
      1. Get the sample file
      2. Validate method file arguments and resolve which to use
      3. Check if record creation and/or autofitting is required
      4. Autofit instrument function (if necessary)
      5A. Create instrument function record (if necessary)
      5B. Otherwise resolve existing instrument function id
      6. Update the sample file records
      7. Reload affected batches

    :param filename: The filename of the file to associate the insturment function with.
    :type filename: str
    :param instrument_config: An instrument config to set to the sample files.
    :type instrument_config: SetInstrumentConfigBody
    """
    if len(filenames) == 0:
        raise ValueError("Process instrument config: filenames must be provided")
    elif len(filenames) == 1:
        label = f"sample file {filenames[0]}"
    else:
        label = f"{len(filenames)} sample files"

    # Step 2: Resolve method file
    if instrument_config.new_record:
        method_file = instrument_config.new_record.method_file
    else:
        instrument_config_record = await get_instrument_config(
            instrument_function_id=instrument_config.instrument_function_id
        )
        method_file = instrument_config_record["data"]["method_file"]

    runtime.logger.info(f"Processing instrument config '{method_file}' for '{label}'")

    # Step 3: Check if record creation and/or autofitting is needed
    if instrument_config.instrument_function_id:
        details = f"existing instrument config '{method_file}' for '{label}'"
        user_message = f"used {details}"
        runtime.logger.info(f"Using {details}")
        create = False
        autofit = False
    elif instrument_config.new_record:
        if instrument_config.new_record.resolution_function:
            autofit = False
            process_message = "user-provided"
        else:
            autofit = True
            process_message = "autofitted"
        details = f"new instrument config for new {process_message} instrument config '{method_file}' for '{label}'"
        user_message = f"created {details}"
        runtime.logger.info(f"Creating {details}")
        create = True

    # Step 4: Autofit instrument function
    if autofit:
        # use first file if not fit file provided
        if not fit_filename:
            fit_filename = filenames[0]
        # Get file
        fit_sample_file = await fetch_sample_file(filename=fit_filename)
        # notify the user
        notification = UserNotification(
            process_id=process_id,
            parent_id=parent_id,
            type="process_instrument_config",
            status="info",
            message=f"Autofitting instrument config for {method_file} with {fit_filename}.",
            data={
                "filename": fit_filename,
                "method_file": method_file,
            },
        )
        await emit_user_notification(notification=notification, room_id=sid, sid=sid)
        # fit to the file
        new_fields = (await fit_instrument_config(sample_file=fit_sample_file))["data"][
            "instrument_functions"
        ].model_dump()
        # create instrument config record
        new_fields["method_file"] = method_file
        instrument_config.new_record = CreateInstrumentConfigBody(**new_fields)

    if create:
        # Step 5A: Create instrument config record
        body = CreateInstrumentConfigBody(**instrument_config.new_record.model_dump())
        instrument_function_id = (await create_instrument_config(body))["data"][
            "instrument_function_id"
        ]
    else:
        # Step 5B: Get existing instrument config id
        instrument_function_id = instrument_config.instrument_function_id

    # Step 6: Update sample file records
    async def process_file(filename):
        sample_file = await fetch_sample_file(filename=filename)
        sample_file_fields = {
            **sample_file.to_dict(),
            "method_file": method_file,
            "instrument_function_id": instrument_function_id,
        }
        await update_sample_file(
            sample_file.sample_file_id,
            SampleFileUpdate(**sample_file_fields),
        )
        # TODO #673: delete invalidated peaks after update

    update_tasks = [process_file(filename) for filename in filenames]
    await asyncio.gather(*update_tasks)

    # Step 7. Reload affected batches
    affected_batch_ids = await fetch_sample_batch_ids(filenames=filenames)
    reload_tasks = [
        sio.emit(
            "sample_batch_reload",
            room=batch_id,
            namespace="/",
        )
        for batch_id in affected_batch_ids
    ]
    await asyncio.gather(*reload_tasks)

    return {
        "message": f"Processing instrument functions successful: {user_message}",
        "_notification_data": {
            "filenames": filenames,
            "instrument_function_id": instrument_function_id,
            "method_file": method_file,
            "created": create,
            "autofitted": autofit,
        },
    }
