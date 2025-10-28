# pylint: disable=line-too-long
"""
This module contains all the functionalities related to the calibration processes. It provides endpoints and
background tasks to process calibration and related operations.

"""

from mascope_signal.compute import get_sum_signal
from sqlalchemy import select, func, and_
from mascope_backend.db import async_session
from mascope_backend.db.id import gen_id
from mascope_backend.db.models import IonizationMode, Sample, SampleItem
from mascope_backend.api.lib.api_features import (
    api_controller,
    api_controller_background_task,
)
from mascope_backend.api.lib.exceptions.api_exceptions import (
    ApiException,
    NotFoundException,
    raise_api_warning,
)

from mascope_backend.api.controllers.calibration.lib.calibration_mz_fit import (
    get_calibration_handler,
    calibration_params_factory,
)
from mascope_backend.api.controllers.match.match_controller import match_remove_sample
from mascope_backend.api.controllers.sample.files.sample_files_controller import (
    update_sample_file,
    get_sample_files,
)
from mascope_backend.api.controllers.sample.items.sample_items_controller import (
    get_sample_item,
)
from mascope_backend.api.controllers.sample.lib.fetch_affected_sample_data import (
    fetch_affected_sample_data,
)
from mascope_backend.api.controllers.sample.lib.sample_batches_fetch import (
    fetch_sample_batch,
)
from mascope_backend.api.controllers.sample.batches.status.service import (
    update_sample_batch_status,
)
from mascope_backend.api.models.sample.files.sample_file_pydantic_model import (
    SampleFileUpdate,
)
from mascope_backend.api.models.calibration.calibration_pydantic_model import (
    MzCalibrationParams,
    CalibrationFitParams,
)
from mascope_backend.socket.notifications import (
    UserNotification,
    send_progress_user_notification,
)

from mascope_backend.runtime import runtime


@api_controller()
async def get_mz_calibration(
    instrument: str = None,
    sample_item_id: str = None,
):
    """
    Retrieve the m/z calibration for a given instrument or sample item ID.

    :param instrument: (Optional) The instrument name.
    :type instrument: str, optional
    :param sample_item_id: (Optional) The sample item ID.
    :type sample_item_id: str, optional
    :return: The m/z calibration for the given parameters.
    :rtype: dict
    """
    async with async_session() as session:
        stmt = select(Sample.mz_calibration)
        if instrument:
            stmt = select(Sample.mz_calibration).where(
                and_(
                    Sample.instrument == instrument,
                    Sample.mz_calibration.isnot(None),
                    Sample.datetime_utc
                    == select(func.max(Sample.datetime_utc))
                    .where(
                        and_(
                            Sample.instrument == instrument,
                            Sample.mz_calibration.isnot(None),
                        )
                    )
                    .scalar_subquery(),
                )
            )
        elif sample_item_id:
            stmt = stmt.filter(Sample.sample_item_id == sample_item_id)

        result = await session.execute(stmt)
        mz_calibration = result.scalars().first()

    return {
        "message": "m/z calibration retrieved successfully.",
        "data": {"mz_calibration": mz_calibration} if mz_calibration else {},
    }


@api_controller_background_task(
    success_notification_rooms=["sid"],
    error_notification_rooms=["sid"],
)
async def calibration_mz_fit(
    sample_item_id: str,
    mz_calibration_params: MzCalibrationParams,
    independent_transaction: bool = False,
    sid: str = None,
    process_id=None,
    parent_id=None,
) -> dict:
    """
    Start m/z fit calibration for a given sample item based on the calibration parameters.

    This controller fits calibration parameters but does not apply them to the sample.
    It collects affected sample data for reload events.

    Steps:
    1. Retrieve sample and batch data
    2. Fetch affected samples data
    3. Perform m/z fitting using the provided parameters
    4. Handle errors and warnings with standardized notification data

    :param sample_item_id: ID of the sample item
    :type sample_item_id: str
    :param mz_calibration_params: Calibration parameters
    :type mz_calibration_params: MzCalibrationParams
    :param independent_transaction: Whether to run as independent transaction
    :type independent_transaction: bool
    :param sid: Session ID for notifications
    :type sid: str
    :param process_id: Process ID for tracking
    :type process_id: str
    :param parent_id: Parent process ID for tracking
    :type parent_id: str
    :return: Dictionary containing fit results and notification data
    :rtype: dict
    :raises NotFoundException: If sample item, batch or calibration collection not found
    :raises ApiException: If m/z fitting fails
    """
    # Retrieve and validate sample and batch data
    async with async_session() as session:
        sample = await session.get(SampleItem, sample_item_id)
        if not sample:
            raise NotFoundException(f"Sample item with ID '{sample_item_id}' not found")

        ionization_mode = await session.get(IonizationMode, sample.ionization_mode_id)
        if not ionization_mode:
            raise NotFoundException(
                f"Ionization mode with ID '{sample.ionization_mode_id}' not found"
            )

    # Check if calibration collection is present
    if not ionization_mode.calibration_collection_id:
        raise NotFoundException(
            f"Calibration collection not found for ionization mode '{ionization_mode.ionization_mode_id}'"
        )

    # Fetch affected samples data
    (
        affected_sample_item_ids,
        affected_sample_batch_ids,
        *_,
    ) = await fetch_affected_sample_data(filenames=[sample.filename])

    # Prepare progress user notification.
    notification = UserNotification(
        process_id=process_id,
        parent_id=parent_id,
        type="calibration_mz_fit",
        status="pending",
        message=f"m/z fitting sample '{sample.sample_item_name}'.",
        # NOTE: Set the internal metadata for the pending user_notifications like
        # room_ids and sid of the user.
        # Internal metadata will be cleaned up the from data in send_progress_user_notification.
        data={
            "sample_item_id": sample_item_id,
            "filename": sample.filename,
            "_room_ids": [sid],
        },
    )

    # m/z fit the sample file
    default_calibration_params = calibration_params_factory(filename=sample.filename)
    if mz_calibration_params.mz_error_tolerance is None:
        # m/z tolerance was not passed, use default value
        mz_calibration_params.mz_error_tolerance = (
            default_calibration_params.mz_error_tolerance
        )
    calibration_parameters = CalibrationFitParams(
        filename=sample.filename,
        calibration_collection_id=ionization_mode.calibration_collection_id,
        ionization_mechanism_ids=ionization_mode.ionization_mechanism_ids,
        **mz_calibration_params.model_dump(),
    )
    calibration_handler = get_calibration_handler(
        sample.filename, calibration_parameters, notification
    )
    await calibration_handler.fit()
    calibration_data = calibration_handler.to_dict()

    # Handle errors and warnings
    notification_data = {
        "affected_sample_item_ids": affected_sample_item_ids,
        "affected_sample_batch_ids": affected_sample_batch_ids,
        "sample_item_id": sample_item_id,
        "filename": sample.filename,
    }

    if calibration_data["error"] is not None:
        error_message = f"m/z fitting for sample '{sample.sample_item_name}' failed: {calibration_data["error"]}"
        runtime.logger.error(calibration_data["error"])
        raise ApiException(
            error_message,
            {
                "data": calibration_data,
                "_notification_data": notification_data,
            },
            422,
        )
    elif calibration_data["warning"] is not None:
        warning_message = f"m/z fitting sample '{sample.sample_item_name}' warning: {calibration_data["warning"]}"
        raise_api_warning(
            warning_message,
            {
                "data": calibration_data,
                "_notification_data": notification_data,
            },
        )
    # Return m/z fit result data and message
    return {
        "data": calibration_data,
        "message": f"Finished to m/z fit sample '{sample.sample_item_name}'.",
        "_notification_data": {
            **calibration_data,
            **notification_data,
        },
    }


@api_controller_background_task(
    success_notification_rooms=["sid"],
    success_reload=[("match_reload", "affected_sample_batch_ids")],
    error_notification_rooms=["sid"],
    error_reload=[("match_reload", "affected_sample_batch_ids")],
)
async def calibration_mz_apply(
    fit: dict,
    filename: str,
    independent_transaction: bool = False,
    sid: str = None,
    process_id=None,
    parent_id=None,
):
    """
    Apply m/z calibration to a sample file.
    - Sets batch status to "processing" for all affected batches during operation.
    - Removes existing matches for all affected samples since calibration invalidates them.
    - Batch status sets to "rematch" for all affected batches because of removed matches.

    :param fit: Fit dictionary.
    :param filename: Name of the sample file.
    :return: List of calibrated sample item IDs.
    """
    # Step 1: Get affected sample items and their batches
    (
        affected_sample_item_ids,
        affected_sample_batch_ids,
        affected_sample_items,
        affected_sample_batches,
    ) = await fetch_affected_sample_data(filenames=[filename], include_objects=True)
    total_samples = len(affected_sample_item_ids)

    # Set non-ACQUISITION batches to "processing", already "processing" batches will not change the status
    await update_sample_batch_status(
        sample_batch_ids=[
            batch.sample_batch_id
            for batch in affected_sample_batches
            if batch.sample_batch_type != "ACQUISITION"
        ],
        status="processing",
        independent_transaction=True,
    )

    runtime.logger.info(
        f"Set {sum(1 for b in affected_sample_batches if b.sample_batch_type != 'ACQUISITION')} "
        f"non-ACQUISITION batch(es) to 'processing' for calibration apply"
    )

    # Step 2: Prepare progress user notification.
    notification = UserNotification(
        process_id=process_id,
        parent_id=parent_id,
        type="calibration_mz_apply",
        status="pending",
        message=f"Applying m/z fit for sample file '{filename}', {total_samples} sample item{'s' if total_samples != 1 else ''} affected.",
        # NOTE: Set the internal metadata for the pending user_notifications like
        # room_ids and sid of the user.
        # Internal metadata will be cleaned up the from data in send_progress_user_notification.
        data={
            "sample_item_ids": affected_sample_item_ids,
            "filename": filename,
            "_room_ids": [sid],
            "_sid": sid,
        },
    )

    await send_progress_user_notification(notification, 0.1)

    # Step 3: Get sample file data and apply m/z fit
    sample_file_data = await get_sample_files(filename=filename)
    if not sample_file_data["data"]:
        raise NotFoundException(f"Sample file '{filename}' not found")

    sample_file = sample_file_data["data"][0]

    calibration_handler = get_calibration_handler(filename, None, notification)
    await calibration_handler.apply(fit)
    updated_mz_axis = get_sum_signal(filename).mz.values
    new_mz_range = [updated_mz_axis[0], updated_mz_axis[-1]]

    fit.update({"verified": True})

    await send_progress_user_notification(notification, 0.3)

    # Step 4: Update sample file database record
    sample_file["mz_calibration"] = fit
    sample_file["range"] = new_mz_range
    runtime.logger.info(sample_file)
    await update_sample_file(
        sample_file["sample_file_id"], SampleFileUpdate(**sample_file)
    )

    await send_progress_user_notification(notification, 0.8)

    # Step 5: Notify completion for each affected batch
    for sample_batch in affected_sample_batches:
        sample_batch_id = sample_batch.sample_batch_id
        sample_batch_name = sample_batch.sample_batch_name
        batch_samples = [
            item
            for item in affected_sample_items
            if item.sample_batch_id == sample_batch_id
        ]
        batch_samples_count = len(batch_samples)

        # Notify batch specific application
        batch_notification = UserNotification(
            process_id=gen_id(8),
            parent_id=process_id,
            type="calibration_mz_apply",
            status="pending",
            message=f"New m/z fit applied for sample file '{filename}'. {batch_samples_count} sample{'s' if batch_samples_count != 1 else ''} affected in sample batch '{sample_batch_name}'.",
            data={
                "sample_batch_id": sample_batch_id,
                "_room_ids": [sample_batch_id],
                "_sid": sid,
            },
        )
        await send_progress_user_notification(batch_notification)

        # FAQ_match removes matches in all samples associated with filename
        # Delete outdated matches, sid is not send to not receive the match_remove_sample notification for every sample
        for sample_item in batch_samples:
            await match_remove_sample(
                sample_item_id=sample_item.sample_item_id,
                full_remove=True,
                independent_transaction=False,
                sid=sid,
                process_id=gen_id(8),
                parent_id=process_id,
            )
    # Step 6: Set non-ACQUISITION batches to "rematch" , since calibration removes matches
    # ACQUISITION batches being matched for the first time
    await update_sample_batch_status(
        sample_batch_ids=[
            batch.sample_batch_id
            for batch in affected_sample_batches
            if batch.sample_batch_type != "ACQUISITION"
        ],
        status="rematch",
        independent_transaction=True,  # reload UI status icons
    )
    runtime.logger.info(
        f"Set {sum(1 for b in affected_sample_batches if b.sample_batch_type != 'ACQUISITION')} "
        f"non-ACQUISITION batch(es) to 'rematch' after applying m/z calibration"
    )

    # Step 7: Return m/z fit result data and message
    message = f"Applied m/z fit for sample file '{filename}', {total_samples} sample item{'s' if total_samples != 1 else ''} affected."
    runtime.logger.info(message)
    return {
        "data": {
            "fit": fit,
        },
        "message": message,
        "_notification_data": {
            "affected_sample_item_ids": affected_sample_item_ids,
            "affected_sample_batch_ids": affected_sample_batch_ids,
            "filename": filename,
        },
    }


@api_controller_background_task(
    success_notification_rooms=["sid"],
    success_reload=[("match_reload", "affected_sample_batch_ids")],
    error_notification_rooms=["sid"],
    error_reload=[("match_reload", "affected_sample_batch_ids")],
)
async def calibration_mz_calibrate_sample(
    sample_item_id: str,
    mz_calibration_params: MzCalibrationParams,
    independent_transaction: bool = False,
    sid: str = None,
    process_id=None,
    parent_id=None,
):
    """
    Performs m/z calibration on a single sample using specified calibration parameters.

    Steps:
    1. Retrieve sample data and affected samples
    2. Perform m/z fit calibration
    3. Apply the calibration to the sample file
    4. Return response with notification data for reload events


    :param sample_item_id: The ID of the sample to be calibrated
    :type sample_item_id: str
    :param mz_calibration_params: The calibration parameters to be used
    :type mz_calibration_params: MzCalibrationParams
    :param independent_transaction: Whether to run as independent transaction
    :type independent_transaction: bool
    :param sid: Session ID for notifications
    :type sid: str
    :param process_id: Process ID for tracking
    :type process_id: str
    :param parent_id: Parent process ID for tracking
    :type parent_id: str
    :raises NotFoundException: If the sample with the given ID is not found in the database.
    :raises ValueError: If the sample does not have a valid filename associated with it.
    :raises ApiException: For any exceptions that occur during the calibration process.
    """
    # Step 1: Retrieve sample data and affected samples
    async with async_session() as session:
        sample = await session.get(SampleItem, sample_item_id)
    if not sample:
        raise NotFoundException(f"Sample item with ID '{sample_item_id}' not found")

    # Get affected samples data for this file
    (
        affected_sample_item_ids,
        affected_sample_batch_ids,
        *_,
    ) = await fetch_affected_sample_data(filenames=[sample.filename])
    runtime.logger.info(f"...m/z calibrating sample '{sample.sample_item_name}' ...")

    # Step 2: Prepare progress user notification.
    notification = UserNotification(
        process_id=process_id,
        parent_id=parent_id,
        type="calibration_mz_calibrate_sample",
        status="pending",
        message=f"m/z calibrating sample '{sample.sample_item_name}'.",
        # NOTE: Set the internal metadata for the pending user_notifications like
        # room_ids and sid of the user.
        # Internal metadata will be cleaned up the from data in send_progress_user_notification.
        data={
            "sample_item_id": sample_item_id,
            "filename": sample.filename,
            "_room_ids": [sid],
            "_sid": sid,
        },
    )

    await send_progress_user_notification(notification, 0.1)

    # Step 3: Perform m/z fit
    # If error/warning occure during the m/z fit it would interrupt the calibration and raise ApiException with _notification_data
    calibration_mz_fit_result = await calibration_mz_fit(
        sample_item_id=sample_item_id,
        mz_calibration_params=mz_calibration_params,
        independent_transaction=False,
        sid=sid,
        process_id=gen_id(8),
        parent_id=process_id,
    )
    fit = calibration_mz_fit_result["data"].get("fit", None)

    await send_progress_user_notification(notification, 0.3)

    # Step 4: Apply m/z calibration
    await calibration_mz_apply(
        fit=fit,
        filename=sample.filename,
        independent_transaction=False,
        sid=sid,
        process_id=gen_id(8),
        parent_id=process_id,
    )

    await send_progress_user_notification(notification, 0.95)

    # Step 5: Return rematched sample and message
    return {
        "message": f"Sample '{sample.sample_item_name}' m/z calibrated.",
        "_notification_data": {
            "sample_item_id": sample_item_id,
            "filename": sample.filename,
            "affected_sample_item_ids": affected_sample_item_ids,
            "affected_sample_batch_ids": affected_sample_batch_ids,
        },
    }


@api_controller_background_task(
    success_notification_rooms=["sid"],
    success_reload=[("match_reload", "affected_sample_batch_ids")],
    error_notification_rooms=["sid"],
    error_reload=[("match_reload", "affected_sample_batch_ids")],
)
async def calibration_mz_calibrate_samples(
    sample_item_ids: str,
    mz_calibration_params: MzCalibrationParams,
    independent_transaction: bool = False,
    sid: str = None,
    process_id=None,
    parent_id=None,
) -> list:
    """
    Performs m/z calibration on a set of sample provided a list of sample item ids using specified calibration parameters.
    It notifies about the calibration progress and completion via Socket.IO. In case of failure, an error message is emitted.

    Steps:
    1. Emit an event to notify the start of calibration.
    2. Retrieve all samples associated with the specified sample batch.
    3. Iterate over each sample, perform calibration, and accumulate results.
    4. Emit an event to notify the completion of calibration along with the results.
    5. In case of an exception, emit an event indicating calibration failure.

    :param sample_batch_id: The ID of the sample batch to be calibrated.
    :type sample_batch_id: str
    :param mz_calibration_params: Calibration parameters to be used for the calibration process.
    :type mz_calibration_params: MzCalibrationParams
    :param independent_transaction: Flag indicating if the operation is an independent transaction, default to False.
    :type independent_transaction: bool
    :raises NotFoundException: Raised if the sample batch or any samples within it are not found.
    :raises ApiException: Raised for any exceptions that occur during the calibration process.
    :return: A list of calibration results for each sample in the batch.
    :rtype: list
    """
    runtime.logger.info(f"...m/z calibrating {len(sample_item_ids)} samples ...")

    # Step 1: Prepare progress user notification
    notification = UserNotification(
        process_id=process_id,
        parent_id=parent_id,
        type="calibration_mz_calibrate_batch",
        status="pending",
        message=f"m/z calibrating {len(sample_item_ids)} samples.",
        # NOTE: Set the internal metadata for the pending user_notifications like
        # room_ids and sid of the user.
        # Internal metadata will be cleaned up the from data in send_progress_user_notification.
        data={
            "sample_item_ids": sample_item_ids,
            "_room_ids": [sid],
            "_sid": sid,
        },
    )
    await send_progress_user_notification(notification)

    # Step 2: Calibrate each sample and collect all affected IDs
    all_affected_sample_item_ids = set()
    samples_calibrate_failed = []

    for sample_item_id in sample_item_ids:
        # Wrap in try/except to not break the loop if one item fails
        try:
            # Calibrate sample using specified parameters
            calibration_result = await calibration_mz_calibrate_sample(
                sample_item_id=sample_item_id,
                mz_calibration_params=mz_calibration_params,
                independent_transaction=False,
                sid=sid,
                process_id=gen_id(8),
                parent_id=process_id,
            )
            # Collect affected items from successful calibration
            all_affected_sample_item_ids.update(
                calibration_result.get("_notification_data", {}).get(
                    "affected_sample_item_ids", []
                )
            )
        except ApiException as e:
            # Get sample details for the failure report
            sample = (await get_sample_item(sample_item_id=sample_item_id))["data"]

            # log the error and add the sample to the failed list
            runtime.logger.warning(
                f"Calibrating sample '{sample['sample_item_name']}' failed: {e.user_message}"
            )
            samples_calibrate_failed.append(
                {
                    "sample_item": {
                        "sample_item_id": sample["sample_item_id"],
                        "sample_item_name": sample["sample_item_name"],
                        "filename": sample["filename"],
                    },
                    "warning_message": e.user_message,
                }
            )
            # Collect affected items from failed calibration
            all_affected_sample_item_ids.update(
                e.tech_message.get("_notification_data", {}).get(
                    "affected_sample_item_ids", []
                )
            )

    # Step 3: Get affected batch IDs
    _, affected_sample_batch_ids, *_ = await fetch_affected_sample_data(
        sample_item_ids=list(all_affected_sample_item_ids)
    )

    # Step 4: If there are any failed to calibrate samples, raise a warning(200) exception
    if samples_calibrate_failed:
        warning_message = f"Failed to calibrate {len(samples_calibrate_failed)} sample{'s' if len(samples_calibrate_failed) != 1 else ''}."
        raise_api_warning(
            warning_message,
            {
                "samples_calibrate_failed": samples_calibrate_failed,
                "_notification_data": {
                    "affected_sample_batch_ids": affected_sample_batch_ids,
                    "affected_sample_item_ids": list(all_affected_sample_item_ids),
                },
            },
        )

    return {
        "message": f"m/z calibrated {len(sample_item_ids)} samples. {len(affected_sample_batch_ids)} sample batch{'es were' if len(affected_sample_batch_ids) > 1 else 'was'} affected.",
        "_notification_data": {
            "sample_item_ids": sample_item_ids,
            "affected_sample_batch_ids": affected_sample_batch_ids,
            "affected_sample_item_ids": list(all_affected_sample_item_ids),
        },
    }


@api_controller_background_task(
    success_notification_rooms=["sid"],
    success_reload=[("match_reload", "affected_sample_batch_ids")],
    error_notification_rooms=["sid"],
    error_reload=[("match_reload", "affected_sample_batch_ids")],
)
async def calibration_mz_calibrate_batch(
    sample_batch_id: str,
    mz_calibration_params: MzCalibrationParams,
    independent_transaction: bool = False,
    sid: str | None = None,
    process_id: str | None = None,
    parent_id: str | None = None,
) -> list:
    """
    Performs m/z calibration on all samples within a given batch using specified calibration parameters.
    Sets batch status to "processing" during operation to prevent concurrent operation.
    Batch status sets to "rematch" for all affected batches since calibration removes existing matches (calibration_mz_apply).

    Steps:
    1. Retrieve batch and validate status for concurrent operation prevention
    2. Retrieve all samples associated with the specified sample batch
    3. Set batch status to "processing" to lock concurrent operations
    4. Perform calibration on all samples via child operation
    5. Return calibration results

    :param sample_batch_id: The ID of the sample batch to be calibrated.
    :type sample_batch_id: str
    :param mz_calibration_params: Calibration parameters to be used for the calibration process.
    :type mz_calibration_params: MzCalibrationParams
    :param independent_transaction: Flag indicating if the operation is an independent transaction, default to False.
    :type independent_transaction: bool
    :param sid: Session identifier for client notifications
    :type sid: str | None
    :param process_id: Process identifier for progress tracking
    :type process_id: str | None
    :param parent_id: Parent process identifier
    :type parent_id: str | None
    :raises NotFoundException: Raised if the sample batch or any samples within it are not found.
    :raises ApiException: Raised for any exceptions that occur during the calibration process.
    :return: Calibration results with batch information and notification data
    :rtype: dict
    """
    # Step 1: Retrieve batch and check if it's already processing
    sample_batch = await fetch_sample_batch(sample_batch_id)
    sample_batch_name = sample_batch.sample_batch_name

    if sample_batch.status == "processing":
        message = f"Sample batch '{sample_batch_name}' is currently being processed - calibration is locked."
        runtime.logger.warning(message)
        return {
            "status": "locked",
            "message": message,
            "_notification_data": {"affected_sample_batch_ids": [sample_batch_id]},
        }

    runtime.logger.info(f"Starting m/z calibration for batch '{sample_batch_name}'")

    # Step 2: Fetch samples in the batch
    async with async_session() as session:
        result = await session.execute(
            select(Sample).where(Sample.sample_batch_id == sample_batch_id)
        )

        samples = result.scalars().all()
    if not samples:
        raise NotFoundException(f"Sample batch '{sample_batch_name}' has no samples")

    # Step 3: Set current batch status to processing to prevent concurrent operations
    await update_sample_batch_status(
        sample_batch_ids=[sample_batch_id],
        status="processing",
        independent_transaction=True,  # reload UI status icons
    )

    # Step 4: Perform calibration on all samples
    calibration_result = await calibration_mz_calibrate_samples(
        sample_item_ids=[sample.sample_item_id for sample in samples],
        mz_calibration_params=mz_calibration_params,
        independent_transaction=False,
        sid=sid,
        process_id=gen_id(8),
        parent_id=process_id,
    )

    # Step 5: Extract notification data from child operation and prepare response
    notification_data = calibration_result.get("_notification_data", {})
    affected_sample_batch_ids = notification_data.get("affected_sample_batch_ids", [])
    affected_sample_item_ids = notification_data.get("affected_sample_item_ids", [])

    message = (
        f"Sample batch '{sample_batch_name}' m/z calibrated successfully. "
        f"{len(affected_sample_batch_ids)} sample batch{'es were' if len(affected_sample_batch_ids) > 1 else ' was'} affected."
    )

    runtime.logger.info(f"{message} Batch status updated to 'rematch'.")

    return {
        "status": "success",
        "message": message,
        "_notification_data": {
            "affected_sample_batch_ids": affected_sample_batch_ids,
            "affected_sample_item_ids": affected_sample_item_ids,
        },
    }
