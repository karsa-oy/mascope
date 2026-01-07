import asyncio

from mascope_backend.api.controllers.match.match_controller import rematch_samples
from mascope_backend.api.controllers.sample.files.sample_files_controller import (
    update_sample_file,
)
from mascope_backend.api.controllers.sample.lib.fetch_affected_sample_data import (
    fetch_affected_sample_data,
)
from mascope_backend.api.controllers.sample.lib.sample_file_fetch import (
    fetch_sample_file,
    fetch_sample_files,
)
from mascope_backend.api.lib.api_features import (
    api_controller_background_task,
)
from mascope_backend.api.models.sample.files.sample_file_pydantic_model import (
    SampleFileUpdate,
)
from mascope_backend.api.new.instrument_configs.lib import (
    read_instrument_functions,
)
from mascope_backend.api.new.instrument_configs.schemas import (
    CreateInstrumentConfigBody,
    SetInstrumentConfigBody,
)
from mascope_backend.api.new.instrument_configs.service import (
    create_instrument_config,
    fit_instrument_config,
    get_instrument_config,
)
from mascope_backend.db import db_semaphore
from mascope_backend.db.id import gen_id
from mascope_backend.runtime import runtime
from mascope_backend.socket.notifications import (
    UserNotification,
    emit_user_notification,
)
from mascope_signal.peak import compute_peaks


@api_controller_background_task(
    success_notification_rooms=["user_id"],
    error_notification_rooms=["user_id"],
)
async def process_instrument_config(
    filenames: list[str],
    instrument_config: SetInstrumentConfigBody,
    fit_filename: str | None = None,
    independent_transaction: bool = None,
    user_id: int | None = None,
    process_id: str | None = None,
    parent_id: str | None = None,
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
      6. Fetch sample file records
      7. Update the sample file records
      8. Recompute peaks for sample files with new instrument config
      9. Gather affected sample data
      10. Recompute sample item matches

    :param filename: The filename of the file to associate the insturment function with.
    :type filename: str
    :param instrument_config: An instrument config to set to the sample files.
    :type instrument_config: SetInstrumentConfigBody
    :param fit_filename: Optional filename to use for fitting the instrument config.
    :type fit_filename: str | None, optional
    :param independent_transaction: Flag to indicate if the operation should be treated as an independent transaction.
    :type independent_transaction: bool | None, optional
    :param user_id: Current user triggered operation (for user notifications)
    :type user_id: int | None, optional
    :param process_id: Process identifier for progress tracking
    :type process_id: str | None, optional
    :param parent_id: Parent process identifier
    :type parent_id: str | None, optional
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
        await emit_user_notification(notification=notification, user_id=user_id)
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

    # Step 6. Fetch sample file records
    sample_files = await fetch_sample_files(filenames=filenames)

    # Step 7: Update sample file records
    async def process_file(sample_file):
        sample_file_fields = {
            **sample_file.to_dict(),
            "method_file": method_file,
            "instrument_function_id": instrument_function_id,
        }
        # Limit concurrent updates with the semaphore to prevent database overload ("QueuePool limit reached")
        async with db_semaphore:
            await update_sample_file(
                sample_file.sample_file_id,
                SampleFileUpdate(**sample_file_fields),
            )

    update_tasks = [process_file(sample_file) for sample_file in sample_files]
    await asyncio.gather(*update_tasks)

    # Step 8. Recompute peaks for sample files with new instrument config
    label = f"file {filenames[0]}" if len(filenames) == 1 else f"{len(filenames)} files"
    runtime.logger.info(f"Recomputing peaks for {label}")
    for filename in filenames:
        instrument_functions = await read_instrument_functions(filename=filename)
        await compute_peaks(filename, instrument_functions)

    # Step 9. Gather affected sample data
    sample_file_ids = [sf.sample_file_id for sf in sample_files]
    (
        affected_sample_item_ids,
        affected_sample_batch_ids,
        *_,
    ) = await fetch_affected_sample_data(sample_file_ids=sample_file_ids)

    # Step 10. Recompute sample item matches
    if independent_transaction:
        await rematch_samples(
            sample_item_ids=affected_sample_item_ids,
            full_remove=True,
            independent_transaction=True,
            user_id=user_id,
            process_id=gen_id(8),
            parent_id=process_id,
        )

    return {
        "message": f"Processing instrument config successful: {user_message}",
        "_notification_data": {
            "filenames": filenames,
            "instrument_function_id": instrument_function_id,
            "method_file": method_file,
            "created": create,
            "autofitted": autofit,
            "affected_sample_batch_ids": affected_sample_batch_ids,
            "affected_sample_item_ids": affected_sample_item_ids,
        },
    }
