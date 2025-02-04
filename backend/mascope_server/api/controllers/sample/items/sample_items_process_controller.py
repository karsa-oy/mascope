from mascope_lib.file_func import get_instrument_type
from mascope_server.db.id import gen_id
from mascope_server.api.lib.api_features import (
    api_controller_background_task,
)
from mascope_server.api.controllers.match.match_controller import match_compute_sample
from mascope_server.api.controllers.calibration.calibration_controller import (
    calibration_mz_calibrate_sample,
)
from mascope_server.api.controllers.samples.samples_controller import get_sample
from mascope_server.api.models.sample.items.sample_item_pydantic_model import (
    SampleItemCreate,
)
from mascope_server.api.models.calibration.calibration_pydantic_model import (
    MzCalibrationParams,
)
from mascope_server.socket.notifications import (
    UserNotification,
    send_progress_user_notification,
)
from mascope_server.api.new.instrument_configs.process.service import (
    process_instrument_config,
)
from mascope_server.api.new.instrument_configs.schemas import (
    SetInstrumentConfigBody,
)
from mascope_server.api.controllers.sample.items.sample_items_controller import (
    create_sample_item,
)


@api_controller_background_task(
    # success_notification_rooms=["sample_batch_id"],  # TEMP for postman testing
    success_notification_rooms=["sid"],
    success_reload=[("sample_batch_reload", "sample_batch_id")],
    error_notification_rooms=["sid"],
    error_reload=[("sample_batch_reload", "sample_batch_id")],
    # error_notification_rooms=["sample_batch_id"],  # TEMP for postman testing
)
async def process_sample_item(
    sample_item: SampleItemCreate,
    instrument_config: SetInstrumentConfigBody,
    mz_calibration_params: MzCalibrationParams = MzCalibrationParams(),
    independent_transaction: bool = False,
    sid=None,
    process_id=None,
) -> dict:
    """
    TODO_api_circular_import  destinguish sample and sample_item controller, should be moved to samples_controller.py?
    Automates the process of sample item creation, calibration, and match computation
    as a single workflow. This process ensures that once a sample item is created, it is
    then calibrated and matches are computed without requiring manual intervention.
    NOTE that the sample_file record with the same filename should already exist in the database.

    Steps:
    1. Process instrument functions for the sample file
    2. Create a new sample item using the provided details.
    3. Perform m/z calibration on the newly created sample item if instrument is TOF
        using provided calibration parameters.
    4. Compute matches for the sample item, integrating any newly identified matches.
    5. Fetch the final sample details including match data for verification and further processing.

    :param sample_item: Details of the sample item to be created.
    :type sample_item: SampleItemCreate
    :param instrument_config: An instrument config to use for the processed item.
    :type instrument_config: SetIntrumentConfigBody
    :param mz_calibration_params: Calibration parameters to use, defaults to a preconfigured set.
    :type mz_calibration_params: MzCalibrationParams, optional
    :param independent_transaction: Indicates whether this operation should be treated as a standalone transaction.
    :type independent_transaction: bool, optional
    :param sid: Session ID for client-specific communications, defaults to None.
    :type sid: str, optional
    :raises RuntimeError: Raised if calibration or match computation fails.
    :return: Details of the processed sample including matches.
    :rtype: dict
    """

    notification = UserNotification(
        process_id=process_id,
        type="process_sample_item",
        status="pending",
        message=f"Processing sample item '{sample_item.sample_item_name}', filename '{sample_item.filename}'.",
        # NOTE: Set the internal metadata for the pending user_notifications like
        # room_ids and sid of the user.
        # Internal metadata will be cleaned up the from data in send_progress_user_notification.
        data={
            "filename": sample_item.filename,
            "sample_batch_id": sample_item.sample_batch_id,
            "_room_ids": [sid],
            # "_room_ids": [sample_item.sample_batch_id],  # TEMP for postman testing
            "_sid": sid,
        },
    )
    await send_progress_user_notification(notification, 0.1)

    # Step 1: process instrument config
    await process_instrument_config(
        filenames=[sample_item.filename],
        instrument_config=instrument_config,
        independent_transaction=False,
        sid=sid,
        process_id=gen_id(8),
        parent_id=process_id,
    )

    # Step 2: create the sample item

    # TODO_invalidation
    # Set independent_transaction to true to trigger sample_batch_reload after creating the sample item record
    create_sample_result = await create_sample_item(
        sample_item=sample_item, independent_transaction=True
    )
    created_sample_item = create_sample_result.get("data")
    sample_item_id = created_sample_item["sample_item_id"]

    notification.message = f"Sample '{sample_item.sample_item_name}' record created with ID: {sample_item_id}."
    notification.data = {
        "sample_item_id": sample_item_id,
        "filename": sample_item.filename,
        "sample_batch_id": sample_item.sample_batch_id,
        "_room_ids": [sid],
        # "_room_ids": [sample_item.sample_batch_id],  # TEMP for postman testing
        "_sid": sid,
    }
    await send_progress_user_notification(notification, 0.2)

    # Step 3: Calibrate the sample item if instrument is TOF
    if get_instrument_type(created_sample_item["filename"]) == "tof":
        await calibration_mz_calibrate_sample(
            sample_item_id=sample_item_id,
            mz_calibration_params=mz_calibration_params,
            sid=sid,
            process_id=gen_id(8),
            parent_id=process_id,
        )
        notification.message = (
            f"Sample '{sample_item.sample_item_name}' m/z calibrated."
        )
        await send_progress_user_notification(notification, 0.6)

    # Step 4: Compute matches if calibration is successful
    await match_compute_sample(
        sample_item_id=sample_item_id,
        independent_transaction=False,
        sid=sid,
        process_id=gen_id(8),
        parent_id=process_id,
    )

    notification.message = (
        f"Matches computed for sample '{sample_item.sample_item_name}'."
    )
    await send_progress_user_notification(notification, 0.9)

    # Step 5: Fetch updated sample details including match data
    sample = (
        await get_sample(
            sample_item_id=sample_item_id,
        )
    )["data"]

    return {
        "message": f"Sample '{sample['sample_item_name']}' was successfully processed.",
        "data": sample,
        "_notification_data": {
            "sample_item_id": sample_item_id,
            "filename": sample["filename"],
            "sample_batch_id": sample["sample_batch_id"],
        },
    }
