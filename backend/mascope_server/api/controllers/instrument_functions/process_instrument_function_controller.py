from typing import Optional

from mascope_server.api.lib.api_features import api_controller_background_task
from mascope_server.api.controllers.sample.files.sample_files_controller import (
    update_sample_file,
)
from mascope_server.api.models.sample.files.sample_file_pydantic_model import (
    SampleFileUpdate,
)
from mascope_server.api.controllers.sample.lib.sample_file_fetch import (
    fetch_sample_file,
)
from mascope_server.api.models.instrument_functions.instrument_function_pydantic_model import (
    InstrumentFunctionBase,
    InstrumentFunctionCreateBody,
)

from mascope_server.api.controllers.instrument_functions.instrument_functions_controller import (
    instrument_functions_fit,
    create_instrument_function,
    get_method_files,
)
from mascope_server.socket.notifications import (
    UserNotification,
    emit_user_notification,
)

from mascope_server.runtime import runtime


@api_controller_background_task(
    success_notification_rooms=["sid"],
    error_notification_rooms=["sid"],
)
async def process_instrument_function(
    filename: str,
    existing_method_file: Optional[str] = None,
    new_method_file: Optional[str] = None,
    new_instrument_function: Optional[InstrumentFunctionBase] = None,
    independent_transaction: bool = False,
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
      6. Update sample file record

    :param filename: The filename of the file to associate the insturment function with.
    :type filename: str
    :param existing_method_file: A method file already in the instrument function table to use.
    :type existing_method_file: str, optional
    :param new_method_file: A new method file not in the instrument function table to create an instrument function for.
    :type new_method_file: str, optional
    :param new_instrument_function: A new instrument function to create a record for.
    :type new_instrument_function: InstrumentFunctionBase, optional
    """
    # Step 1: Get the sample file
    sample_file = await fetch_sample_file(filename=filename)

    # Step 2: Resolve method file
    if existing_method_file and new_method_file:
        raise ValueError(
            f"Process instrument function ({filename}): expecting either an existing_method_file argument or a new_method_file_argument but not both."
        )
    else:
        method_file = new_method_file or existing_method_file

    runtime.logger.info(
        f"Processing instrument function for sample file {filename} and method file {method_file}"
    )

    # Step 3: Check if record creation and/or autofitting is needed
    if existing_method_file and new_instrument_function:
        details = f"instrument functions for existing method file {method_file} for sample file {filename}"
        user_message = f"updated {details}"
        runtime.logger.info(f"Updating {details}")
        create = True
        autofit = False
    elif existing_method_file and not new_instrument_function:
        details = f"latest instrument functions for existing method file {method_file} for sample file {filename}"
        user_message = f"used {details}"
        runtime.logger.info(f"Using {details}")
        create = False
        autofit = False
    elif new_method_file and new_instrument_function:
        details = f"new instrument functions for new method file {method_file} with user-provided fit for sample file {filename}"
        user_message = f"created {details}"
        runtime.logger.info(f"Creating {details}")
        create = True
        autofit = False
    elif new_method_file and not new_instrument_function:
        details = f"new instrument functions for new method file {method_file} with automated fit for sample file {filename}"
        user_message = f"created {details}"
        runtime.logger.info(f"Creating {details}")
        create = True
        autofit = True

    # Step 4: Autofit instrument function
    if autofit:
        # notify the user
        notification = UserNotification(
            process_id=process_id,
            parent_id=parent_id,
            type="process_instrument_function",
            status="info",
            message=f"Autofitting instrument function for {method_file} with {sample_file.filename}.",
            data={
                "filename": sample_file.filename,
                "method_file": method_file,
            },
        )
        await emit_user_notification(notification=notification, room_id=sid, sid=sid)
        # fit to the file
        new_instrument_function = (
            await instrument_functions_fit(sample_file=sample_file)
        )["data"]["instrument_functions"].model_dump()
        # create instrument function record
        new_instrument_function["method_file"] = method_file

    if create:
        # Step 5A: Create instrument function record
        body = InstrumentFunctionCreateBody(
            **{**new_instrument_function.model_dump(), "method_file": method_file}
        )
        instrument_function_id = (await create_instrument_function(body))["data"][
            "instrument_function_id"
        ]
    else:
        # Step 5B: Get instrument record id
        instrument_function_id = [
            *filter(  # *
                lambda f: f.method_file == method_file,
                (await get_method_files(filename=filename))["data"],
            )
        ][0].instrument_function_id
        # * Since this controller returns one instrument function
        # per method file, filtering would produce exactly one
        # record.

    # Step 6: Update sample file record
    sample_file_fields = {
        **sample_file.to_dict(),
        "method_file": method_file,
        "instrument_function_id": instrument_function_id,
    }
    await update_sample_file(
        sample_file.sample_file_id,
        SampleFileUpdate(**sample_file_fields),
    )

    return {
        "message": f"Processing instrument functions successful: {user_message}",
        "_notification_data": {
            "filename": filename,
            "instrument_function_id": instrument_function_id,
            "method_file": method_file,
            "created": create,
            "autofitted": autofit,
        },
    }
