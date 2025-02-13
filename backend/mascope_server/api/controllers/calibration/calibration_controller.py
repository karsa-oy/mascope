# pylint: disable=line-too-long
"""
This module contains all the functionalities related to the calibration processes. It provides endpoints and
background tasks to process calibration and related operations.

"""

from sqlalchemy import select, func, and_
from sqlalchemy.orm import joinedload
from mascope_server.db import async_session
from mascope_server.socket import sio
from mascope_server.db.id import gen_id
from mascope_server.db.models import Sample, SampleBatch, SampleItem
from mascope_server.api.lib.api_features import (
    api_controller,
    api_controller_background_task,
)
from mascope_server.api.lib.exceptions.api_exceptions import (
    ApiException,
    NotFoundException,
    raise_api_warning,
)
from mascope_server.api.controllers.calibration.lib.calibration_mz_fit import (
    mz_fit,
    signal_mz_calibration_update,
)
from mascope_server.api.controllers.match.match_controller import match_remove_sample
from mascope_server.api.controllers.sample.files.sample_files_controller import (
    update_sample_file,
    get_sample_files,
)
from mascope_server.api.controllers.sample.items.sample_items_controller import (
    get_sample_item,
)
from mascope_server.api.controllers.sample.lib.sample_batches_fetch import (
    fetch_sample_batch_ids,
)
from mascope_server.api.models.sample.files.sample_file_pydantic_model import (
    SampleFileUpdate,
)
from mascope_server.api.models.calibration.calibration_pydantic_model import (
    MzCalibrationParams,
)
from mascope_server.socket.notifications import (
    UserNotification,
    send_progress_user_notification,
)

from mascope_server.runtime import runtime


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
):
    """
    Start m/z fit calibration for a given sample item based on the calibration parameters.

    :param sample_item_id: ID of the sample item.
    :param mz_calibration_params: Calibration parameters.
    :param background_tasks: Optional background task parameter.
    """
    # Step 1: Retrieve sample and batch data
    async with async_session() as session:
        sample = await session.get(SampleItem, sample_item_id)
        if not sample:
            raise NotFoundException(f"Sample item with ID '{sample_item_id}' not found")

    async with async_session() as session:
        sample_batch = await session.get(SampleBatch, sample.sample_batch_id)
        if not sample_batch:
            raise NotFoundException(
                f"Sample batch with ID '{sample.sample_batch_id}' not found"
            )

    build_params = sample_batch.build_params

    # Step 2: Prepare progress user notification.
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
            # "_sid": sid,
        },
    )

    # Step 3: m/z fit the sample file
    calibration_mechs = build_params.get("calibration_ion_mechanisms")
    matching_mechs = build_params["ion_mechanisms"]
    if calibration_mechs:
        runtime.logger.debug(
            "Calibrating mz fit using calibration ionization mechanisms"
        )
        mechanisms = calibration_mechs
    else:
        runtime.logger.debug("Calibrating mz fit using matching ionization mechanisms")
        mechanisms = matching_mechs
    fit, stats, error, warning = await mz_fit(
        filename=sample.filename,
        calibration_collection_id=build_params["calibration_collection"],
        ionization_mechanism_ids=mechanisms,
        peak_intensity_min=mz_calibration_params.peak_intensity_min,
        isotope_abundance_min=mz_calibration_params.isotope_abundance_min,
        match_score_min=mz_calibration_params.match_score_min,
        refine_window=mz_calibration_params.refine_window,
        notification=notification,
    )

    # Step 4: Handle errors and warnings
    if error is not None:
        # Raise an error if the m/z fit failed, error user notification will be send in wrapper
        error_message = (
            f"m/z fitting for sample '{sample.sample_item_name}' failed: {error}"
        )
        runtime.logger.error(error)
        raise ApiException(
            error_message,
            {
                "data": {
                    "fit": fit,
                    "stats": stats,
                    "error": error,
                }
            },
            422,
        )
    elif warning is not None:
        warning_message = (
            f"m/z fitting sample '{sample.sample_item_name}' warning: {warning}"
        )
        raise_api_warning(
            warning_message,
            {
                "data": {
                    "fit": fit,
                    "stats": stats,
                    "warning": warning,
                }
            },
        )

    # Step 5: Return m/z fit result data and message
    data = {
        "fit": fit,
        "stats": stats,
        "error": error,
        "warning": warning,
    }
    return {
        "data": data,
        "message": f"Finished to m/z fit sample '{sample.sample_item_name}'.",
        "_notification_data": {
            "fit": fit,
            "stats": stats,
            "error": error,
            "sample_item_id": sample_item_id,
            "filename": sample.filename,
        },
    }


@api_controller_background_task(
    success_notification_rooms=["sid"],
    error_notification_rooms=["sid"],
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

    :param fit: Fit dictionary.
    :param filename: Name of the sample file.
    :return: List of calibrated sample item IDs.
    """
    # Step 1: Get affected sample items and their batches
    async with async_session() as session:
        result = await session.execute(
            select(SampleItem)
            .options(joinedload(SampleItem.sample_batch))
            .filter(SampleItem.filename == filename)
        )
        sample_items = result.scalars().all()

    if not sample_items:
        raise NotFoundException(f"No sample items found for sample file '{filename}'")

    affected_batches = {item.sample_batch for item in sample_items}
    total_samples = len(sample_items)
    sample_item_ids = [item.to_dict()["sample_item_id"] for item in sample_items]
    sample_batch_ids = set([item.to_dict()["sample_batch_id"] for item in sample_items])

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
            "sample_item_ids": sample_item_ids,
            "filename": filename,
            "_room_ids": [sid],
            "_sid": sid,
        },
    )

    await send_progress_user_notification(notification, 0.1)

    # Retrieve the sample file data
    sample_file_data = await get_sample_files(filename=filename)
    if not sample_file_data["data"]:
        raise NotFoundException(f"Sample file '{filename}' not found")

    sample_file = sample_file_data["data"][0]

    # Update zarr files
    new_mz = signal_mz_calibration_update(fit, sample_file["filename"])
    new_range = [new_mz[0], new_mz[-1]]

    fit.update({"verified": True})

    await send_progress_user_notification(notification, 0.3)

    # Update database record
    sample_file["mz_calibration"] = fit
    sample_file["range"] = new_range
    # Ensure polarity is a valid string
    sample_file["polarity"] = sample_file.get("polarity") or ""
    runtime.logger.info(sample_file)
    await update_sample_file(
        sample_file["sample_file_id"], SampleFileUpdate(**sample_file)
    )

    await send_progress_user_notification(notification, 0.8)

    # Step 3: Notify completion and emit a reload event for each affected batch
    for sample_batch in affected_batches:
        sample_batch_id = sample_batch.sample_batch_id
        sample_batch_name = sample_batch.sample_batch_name
        batch_samples = [
            item for item in sample_items if item.sample_batch_id == sample_batch_id
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

        # FAQ_match removes mathces in all samples assosiated with filename
        # Delete outdated matches, sid is not send to not receive the match_remove_sample notification for every sample
        for sample_item in batch_samples:
            await match_remove_sample(
                sample_item_id=sample_item.sample_item_id,
                independent_transaction=False,
                process_id=gen_id(8),
                parent_id=process_id,
            )

        # Emit reload event if independent transaction
        if independent_transaction:
            await sio.emit("sample_batch_reload", room=sample_batch_id, namespace="/")

    # Step 4: Return m/z fit result data and message
    return {
        "data": {
            "sample_item_ids": sample_item_ids,
            "sample_batch_ids": list(sample_batch_ids),
        },
        "message": f"Applied m/z fit for sample file '{filename}', {total_samples} sample item{'s' if total_samples != 1 else ''} affected.",
        "_notification_data": {
            "sample_item_ids": sample_item_ids,
            "filename": filename,
        },
    }


@api_controller_background_task(
    success_notification_rooms=["sid"],
    error_notification_rooms=["sid"],
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
    Emits events to notify the start, progress, and completion of the calibration process.
    In case of a failure during the process, an error message is emitted.

    Steps:
    1. Fetch the sample data using the provided sample item ID.
    2. Emit an event to notify the start of the calibration process.
    3. Perform the calibration using the specified parameters.
    4. In case of any exceptions during the process, emit an error message indicating the failure.

    :param sample_item_id: The ID of the sample to be calibrated.
    :type sample_item_id: str
    :param mz_calibration_params: The calibration parameters to be used for the calibration process.
    :type mz_calibration_params: MzCalibrationParams
    :raises NotFoundException: If the sample with the given ID is not found in the database.
    :raises ValueError: If the sample does not have a valid filename associated with it.
    :raises ApiException: For any exceptions that occur during the calibration process.
    """
    # Step 1: Retrieve sample data
    async with async_session() as session:
        sample = await session.get(SampleItem, sample_item_id)
    if not sample:
        raise NotFoundException(f"Sample item with ID '{sample_item_id}' not found")

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
    # If error/warning occure during the m/z fit it would interrupt the calibration and raise ApiException
    calibration_mz_fit_data = await calibration_mz_fit(
        sample_item_id=sample_item_id,
        mz_calibration_params=mz_calibration_params,
        independent_transaction=False,
        sid=sid,
        process_id=gen_id(8),
        parent_id=process_id,
    )
    fit = calibration_mz_fit_data["data"].get("fit", None)

    await send_progress_user_notification(notification, 0.3)

    # Step 4: Apply m/z calibration
    calibration_mz_apply_data = await calibration_mz_apply(
        fit=fit,
        filename=sample.filename,
        sid=sid,
        process_id=gen_id(8),
        parent_id=process_id,
    )
    sample_item_ids = calibration_mz_apply_data["data"].get("sample_item_ids", None)
    sample_batch_ids = calibration_mz_apply_data["data"].get("sample_batch_ids", None)

    await send_progress_user_notification(notification, 0.95)

    # TODO_reload Reload affected sample batches
    if independent_transaction:
        for sample_batch_id in sample_batch_ids:
            await sio.emit("sample_batch_reload", room=sample_batch_id, namespace="/")

    # Step 5: Return rematched sample and message
    response_data = {
        "data": {
            "affected_sample_item_ids": list(sample_item_ids),
            "affected_sample_batch_ids": list(sample_batch_ids),
        },
        "message": f"Sample '{sample.sample_item_name}' m/z calibrated.",
        "_notification_data": {
            "sample_item_id": sample_item_id,
            "filename": sample.filename,
            "affected_sample_item_ids": sample_item_ids,
            "affected_sample_batch_ids": sample_batch_ids,
        },
    }

    return response_data


@api_controller_background_task(
    success_notification_rooms=["sid"],
    success_reload=[("sample_batch_reload", "sample_batch_ids")],
    error_notification_rooms=["sid"],
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
    # Prepare progress user notification.
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

    # Step 3: Calibrate each sample and collect results
    sample_item_ids_to_reload = set()
    samples_calibrate_failed = []
    for sample_item_id in sample_item_ids:
        # Wrap in try/except to not break the loop if one item fails
        try:
            # Calibrate sample using specified parameters
            calibration = await calibration_mz_calibrate_sample(
                sample_item_id=sample_item_id,
                mz_calibration_params=mz_calibration_params,
                independent_transaction=False,
                sid=sid,
                process_id=gen_id(8),
                parent_id=process_id,
            )

            affected_sample_item_ids = calibration["data"].get(
                "affected_sample_item_ids", None
            )
            sample_item_ids_to_reload.update(affected_sample_item_ids)
        except ApiException as e:
            sample = (await get_sample_item(sample_item_id=sample_item_id))["data"]
            # If an exception occurs during sample calibration, log the error and add the sample to the failed list
            runtime.logger.error(
                f"Calibrating sample '{sample['sample_item_name']}' failed: {e}"
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

    sample_batch_ids_to_reload = fetch_sample_batch_ids(
        sample_item_ids=sample_item_ids_to_reload
    )

    # Step 4: If there are any failed to calibrate samples, raise a warning(200) exception
    # with the list of failed to calibrate samples included in the error detail (tech_message)
    if samples_calibrate_failed:
        warning_message = f"Failed to calibrate {len(samples_calibrate_failed)} sample{'s' if len(samples_calibrate_failed) != 1 else ''}."
        raise_api_warning(
            warning_message,
            {
                "samples_calibrate_failed": samples_calibrate_failed,
            },
        )

    # Step 5: Return rematched batch and message
    return {
        "data": {
            "sample_batch_ids": list(sample_batch_ids_to_reload),
        },
        "message": f"m/z calibrated {len(sample_item_ids)} samples. {len(sample_batch_ids_to_reload)} sample batch{'es were' if len(sample_batch_ids_to_reload) > 1 else 'was'} affected.",
        "_notification_data": {
            "sample_item_ids": sample_item_ids,
            "affected_sample_batch_ids": list(sample_batch_ids_to_reload),
        },
    }


@api_controller_background_task(
    success_notification_rooms=["sid"],
    error_notification_rooms=["sid"],
)
async def calibration_mz_calibrate_batch(
    sample_batch_id: str,
    mz_calibration_params: MzCalibrationParams,
    independent_transaction: bool = False,
    sid: str = None,
    process_id=None,
    parent_id=None,
) -> list:
    """
    Performs m/z calibration on all samples within a given batch using specified calibration parameters.
    It notifies about the calibration progress and completion via Socket.IO. In case of failure, an error message is emitted.

    Steps:
    1. Emit an event to notify the start of calibration.
    2. Retrieve all samples associated with the specified sample batch.
    3. Iterate over each sample, perform calibration, and accumulate results.
    4. Emit an event to notify the completion of calibration along with the results.
    5. Emit a reload event for the sample batch if this is an independent transaction.
    6. In case of an exception, emit an event indicating calibration failure.

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
    # Step 1: Fetch sample batch data
    async with async_session() as session:
        sample_batch = await session.get(SampleBatch, sample_batch_id)
    if not sample_batch:
        raise NotFoundException(f"Sample batch with ID '{sample_batch_id}' not found")
    sample_batch_name = sample_batch.sample_batch_name
    async with async_session() as session:
        # Fetch samples
        result = await session.execute(
            select(Sample).where(Sample.sample_batch_id == sample_batch_id)
        )

        samples = result.scalars().all()
    if not samples:
        raise NotFoundException(f"Sample batch '{sample_batch_name}' has no samples")

    calibration_result = await calibration_mz_calibrate_samples(
        sample_item_ids=[sample.sample_item_id for sample in samples],
        mz_calibration_params=mz_calibration_params,
        independent_transaction=independent_transaction,
        sid=sid,
        process_id=gen_id(8),
        parent_id=process_id,
    )
    sample_batch_ids_to_reload = calibration_result["data"]["sample_batch_ids"]

    # Step 5: Return rematched batch and message
    return {
        "data": {
            "affected_sample_batch_ids": list(sample_batch_ids_to_reload),
        },
        "message": f"Sample batch '{sample_batch.sample_batch_name}' m/z calibrated. {len(sample_batch_ids_to_reload)} sample batch{'es were' if len(sample_batch_ids_to_reload) > 1 else 'was'} affected.",
        "_notification_data": {
            "sample_batch_id": sample_batch_id,
            "affected_sample_batch_ids": list(sample_batch_ids_to_reload),
        },
    }
