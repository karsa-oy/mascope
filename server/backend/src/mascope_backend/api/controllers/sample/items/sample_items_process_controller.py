import asyncio

from mascope_file.name import get_instrument_type

from mascope_backend.db.id import gen_id
from mascope_backend.api.lib.api_features import (
    api_controller_background_task,
)
from mascope_backend.api.lib.exceptions.api_exceptions import ApiException
from mascope_backend.api.controllers.match.match_controller import match_compute_sample

from mascope_backend.api.controllers.calibration.calibration_controller import (
    calibration_mz_calibrate_sample,
)
from mascope_backend.api.controllers.samples.samples_controller import get_sample
from mascope_backend.api.models.sample.items.sample_item_pydantic_model import (
    SampleItemCreate,
)
from mascope_backend.api.controllers.sample.items.sample_items_controller import (
    create_sample_item,
)
from mascope_backend.api.controllers.sample.lib.fetch_affected_sample_data import (
    fetch_affected_sample_data,
)
from mascope_backend.api.controllers.match.match_controller import rematch_samples
from mascope_backend.api.models.calibration.calibration_pydantic_model import (
    MzCalibrationParams,
)
from mascope_backend.socket.notifications import (
    UserNotification,
    send_progress_user_notification,
)
from mascope_backend.api.new.instrument_configs.process.service import (
    process_instrument_config,
)
from mascope_backend.api.new.instrument_configs.schemas import (
    SetInstrumentConfigBody,
)

from mascope_backend.runtime import runtime


@api_controller_background_task(
    success_notification_rooms=["sid"],
    success_reload=[("sample_batch_reload", "affected_sample_batch_ids")],
    error_notification_rooms=["sid"],
    error_reload=[("sample_batch_reload", "affected_sample_batch_ids")],
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
    4. Compute matches for the processed sample
    5. Create separate independent task to recompute matches for other affected samples
    6. Gather all affected batch IDs for ui reload events
    7. Fetch processed sample details including match data

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
    # Initialize collector for affected sample items
    all_affected_sample_item_ids = set()

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
            "_sid": sid,
        },
    )
    await send_progress_user_notification(notification, 0.1)

    # Step 1: process instrument config
    instrument_config_result = await process_instrument_config(
        filenames=[sample_item.filename],
        instrument_config=instrument_config,
        independent_transaction=False,
        sid=sid,
        process_id=gen_id(8),
        parent_id=process_id,
    )
    # Collect affected items from instrument config processing
    all_affected_sample_item_ids.update(
        instrument_config_result["_notification_data"].get(
            "affected_sample_item_ids", []
        )
    )

    # Step 2: create the sample item

    # TODO_invalidation
    # Set independent_transaction to true to trigger sample_batch_reload after creating the sample item record
    create_sample_result = await create_sample_item(
        sample_item=sample_item, independent_transaction=True
    )
    created_sample_item = create_sample_result.get("data")
    created_sample_item_id = created_sample_item["sample_item_id"]

    # Add newly created item to affected items
    all_affected_sample_item_ids.add(created_sample_item_id)

    notification.message = f"Sample '{sample_item.sample_item_name}' record created with ID: {created_sample_item_id}."
    notification.data = {
        "sample_item_id": created_sample_item_id,
        "filename": sample_item.filename,
        "sample_batch_id": sample_item.sample_batch_id,
        "_room_ids": [sid],
        "_sid": sid,
    }
    await send_progress_user_notification(notification, 0.2)

    # Step 3: Calibrate the sample item if instrument is TOF
    if get_instrument_type(created_sample_item["filename"]) == "tof":
        try:
            calibration_result = await calibration_mz_calibrate_sample(
                sample_item_id=created_sample_item_id,
                mz_calibration_params=mz_calibration_params,
                independent_transaction=False,
                sid=sid,
                process_id=gen_id(8),
                parent_id=process_id,
            )
            # Collect calibration-affected sample items
            all_affected_sample_item_ids.update(
                calibration_result["_notification_data"].get(
                    "affected_sample_item_ids", []
                )
            )

            notification.message = (
                f"Sample '{sample_item.sample_item_name}' m/z calibrated."
            )
            await send_progress_user_notification(notification, 0.6)
        except ApiException as e:
            if e.status_code == 200:
                # Handle warnings, collect affected items from warning response
                all_affected_sample_item_ids.update(
                    e.tech_message.get("_notification_data", {}).get(
                        "affected_sample_item_ids", []
                    )
                )
            else:
                # This is a critical error, re-raise it
                raise

    # Step 4: Compute matches for processed sample
    await match_compute_sample(
        sample_item_id=created_sample_item_id,
        independent_transaction=False,
        sid=sid,
        process_id=gen_id(8),
        parent_id=process_id,
    )

    notification.message = (
        f"Matches computed for sample '{sample_item.sample_item_name}'."
    )
    await send_progress_user_notification(notification, 0.9)

    # Step 5: Create separate independent task to recompute matches for other affected samples
    other_affected_sample_item_ids = [
        si_id
        for si_id in all_affected_sample_item_ids
        if si_id != created_sample_item_id  # exclude the processed sample
    ]
    if other_affected_sample_item_ids:
        asyncio.create_task(
            rematch_samples(
                sample_item_ids=other_affected_sample_item_ids,
                independent_transaction=True,  # Set to true to handle reloads independantly
                sid=sid,
                process_id=gen_id(8),
            )
        )

        runtime.logger.info(
            f"Started independant rematch task for {len(other_affected_sample_item_ids)} affected samples"
        )

    # Step 6. Gather all affected batch IDs for ui reload events
    _, affected_sample_batch_ids, *_ = await fetch_affected_sample_data(
        sample_item_ids=list(all_affected_sample_item_ids)
    )

    # Step 7: Fetch processed sample details including match data
    sample = (
        await get_sample(
            sample_item_id=created_sample_item_id,
        )
    )["data"]

    return {
        "message": f"Sample '{sample['sample_item_name']}' was successfully processed.",
        "data": sample,
        "_notification_data": {
            "sample_item_id": created_sample_item_id,
            "filename": sample["filename"],
            "affected_sample_batch_ids": affected_sample_batch_ids,
            "affected_sample_item_ids": list(all_affected_sample_item_ids),
        },
    }
