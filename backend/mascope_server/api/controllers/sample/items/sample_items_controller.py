from datetime import datetime, timezone
import os
from fastapi import BackgroundTasks
from mascope_server.api.controllers.sample.lib.sample_batches_fetch import (
    fetch_sample_batch_data,
)
from mascope_server.api.controllers.samples.samples_controller import get_sample
from mascope_server.api.new.instrument_configs.lib import read_instrument_functions
import numpy as np
import pandas as pd
from sqlalchemy import (
    select,
    asc,
    desc,
    func,
)
from mascope_server.socket import sio
from mascope_server.db import async_session
from mascope_server.db.id import gen_id
from mascope_server.db.models import (
    SampleBatch,
    SampleItem,
    SampleFile,
)
from mascope_server.api.lib.api_features import (
    api_controller,
    api_controller_background_task,
)
from mascope_server.api.lib.exceptions.api_exceptions import (
    NotFoundException,
)
from mascope_server.api.controllers.sample.lib.sample_items_copy import (
    copy_sample_item_match_data,
)
from mascope_server.api.controllers.samples.lib.samples_fetch import fetch_sample
from mascope_server.api.controllers.match.match_controller import match_compute_sample
from mascope_server.api.models.sample.items.sample_item_pydantic_model import (
    SampleItemCreate,
    SampleItemUpdate,
)
from mascope_server.socket.notifications import (
    UserNotification,
    send_progress_user_notification,
)
from mascope_server.api.new.instrument_configs.service import get_instrument_config
from mascope_server.api.new.instrument_configs.schemas import (
    SetInstrumentConfigBody,
)
from mascope_server.api.new.instrument_configs.process.service import (
    process_instrument_config,
)
from mascope_server.runtime import runtime

from mascope_lib.file_func import get_filestore_path, get_instrument_type, load_signal
from mascope_lib.peak import detect_peaks


@api_controller()
async def get_sample_items(
    sample_batch_id: str = None,
    filename: str = None,
    sort: str = "sample_item_utc_created",
    order: str = "asc",
    page: int = 0,
    limit: int = 10000,
) -> dict:
    """
    Retrieves a paginated list of sample items, optionally sorted by a specified column in either ascending or descending order.

    Steps:
    1. Construct a SQLAlchemy query to select all sample items.
    2. Apply filtering if specified by the parameters.
    3. Apply sorting if specified by the sort and order parameters.
    3. Apply pagination based on the page and limit parameters.
    4. Execute the query to fetch the results.
    5. Convert the results into a list of dictionaries for JSON serialization.

    :param sample_batch_id: The sample batch ID for which you want to fetch the sample items, defaults to None
    :type sample_batch_id: str, optional
    :param filename: The filename for which you want to fetch the sample items, defaults to None
    :type filename: str, optional
    :param sort:  Column to sort by, defaults to "sample_item_utc_created"
    :type sort: str, optional
    :param order: Sorting order ('asc' for ascending, 'desc' for descending), defaults to "asc"
    :type order: str, optional
    :param page: Page number for pagination.
    :type page: int, optional
    :param limit: Number of items per page.
    :type limit: int, optional
    :return: A dictionary with the total count and a list of sample items.
    :rtype: dict
    """
    async with async_session() as session:
        stmt = select(SampleItem)

        # Step 1: Apply filters if specified
        if sample_batch_id:
            stmt = stmt.filter(SampleItem.sample_batch_id == sample_batch_id)

        if filename:
            stmt = stmt.filter(SampleItem.filename == filename)

        # Step 2: Apply sorting if specified
        if sort:
            if order == "desc":
                stmt = stmt.order_by(desc(getattr(SampleItem, sort)))
            else:
                stmt = stmt.order_by(asc(getattr(SampleItem, sort)))

        # Step 3: Get total count for pagination
        count_stmt = select(func.count()).select_from(  # pylint: disable=not-callable
            stmt
        )
        total = await session.scalar(count_stmt)

        # Step 4: Apply pagination
        stmt = stmt.offset(page * limit).limit(limit)
        result = await session.execute(stmt)
        sample_items = result.scalars().all()

        # Step 5: Return the total count and the list of sample items
        return {
            "message": "Sample items retrieved successfully.",
            "results": total,
            "data": [sample_item.to_dict() for sample_item in sample_items],
        }


@api_controller()
async def get_sample_item(sample_item_id: str) -> dict:
    """
    Retrieves a single sample item by its unique ID.

    Steps:
    1. Execute a query to fetch the sample item with the specified ID.
    2. Check if the sample item exists. If not, raise a NotFoundException.
    3. Return the sample item's details as a dictionary.

    :param sample_item_id: Unique identifier of the sample item to retrieve.
    :type sample_item_id: str
    :raises NotFoundException: If the sample item with the given ID is not found.
    :return: The requested sample item's details.
    :rtype: dict
    """
    async with async_session() as session:
        # Step 1: Fetch sample item by ID
        sample_item = await session.get(SampleItem, sample_item_id)

        # Step 2: If sample item not found, raise exception
        if not sample_item:
            raise NotFoundException(f"Sample item with ID '{sample_item_id}' not found")
    # Step 3: Return sample item details
    return {
        "message": f"Sample item '{sample_item.sample_item_name}' retrieved successfully.",
        "data": sample_item.to_dict(),
    }


@api_controller(
    success_reload_events=[
        ("sample_batch_reload", "sample_batch_id"),
    ],  # TODO_invalidation
)
async def create_sample_item(
    sample_item: SampleItemCreate, independent_transaction: bool = False
) -> dict:
    """
    Creates a new sample item with the specified details after verifying that an associated
    sample file exists in the database.

    Steps:
    1. Verify that the sample file with the given filename exists in the database.
    2. Create a new sample item object with the provided details and a generated ID.
    3. Add the new sample item to the session and commit the changes to the database.
    4. Return the details of the created sample item.

    :param sample_item: Sample item creation details from the request body.
    :type sample_item: SampleItemCreate
    :param independent_transaction: Flag indicating whether the sample item create is an independent transaction, defaults to False
    :type independent_transaction: bool, optional
    :return: The created sample item's details.
    :rtype: dict
    :raises NotFoundException: Raised if the associated sample file does not exist.
    """
    async with async_session() as session:
        # Step 1: Verify the existence of the sample file
        result = await session.execute(
            select(SampleFile).where(SampleFile.filename == sample_item.filename)
        )
        sample_file = result.scalars().one_or_none()

        if not sample_file:
            raise NotFoundException(
                f"Sample file with filename '{sample_item.filename}' not found"
            )
        # Step 2: Generate unique ID and create new sample item
        new_sample_item = SampleItem(
            sample_item_id=gen_id(),
            **sample_item.model_dump(),  # Pydantic model's data
            sample_item_utc_created=datetime.now(timezone.utc),
            sample_item_utc_modified=datetime.now(timezone.utc),
        )
        # Step 3: Add to session and commit
        session.add(new_sample_item)
        await session.commit()
        await session.refresh(new_sample_item)

    # Step 4: Return the new sample item details
    return {
        "message": f"Sample item '{new_sample_item.sample_item_name}' was created.",
        "data": new_sample_item.to_dict(),
    }


@api_controller()
async def update_sample_item(
    sample_item_id: str,
    sample_item: SampleItemUpdate,
    instrument_config: SetInstrumentConfigBody | None = None,
    background_tasks: BackgroundTasks | None = None,
    independent_transaction: bool = False,
    sid: str | None = None,
    process_id: str | None = None,
) -> dict:
    """
    Updates an existing sample item with new data provided in the sample item update request body.

    Steps:
    1. Fetch the existing sample item by its ID from the database.
    2. If the sample item is found, update its properties with the new data provided.
    3. Set the sample item's modification timestamp to the current UTC time.
    4. Commit the updated sample item to the database.
    5. Process instrument configs for the sample item if needed.
    6. Reload of sample batch happens in the end of update operation if only basic fields were updated,
        or in the end of potential process_instrument_config.

    :param sample_item_id: The unique identifier of the sample item to update.
    :type sample_item_id: str
    :param sample_item: The new data for the sample item update.
    :type sample_item: SampleItemUpdate
    :param instrument_config: Optional instrument configuration to process.
    :type instrument_config: SetInstrumentConfigBody | None
    :param background_tasks: FastAPI background tasks for processing instrument config post-update.
    :type background_tasks: BackgroundTasks | None
    :param independent_transaction: Flag to indicate if the operation should be treated as an independent transaction.
    :type independent_transaction: bool
    :param sid: Socket.IO session ID, used for emitting notifications to specific clients.
    :type sid: str | None
    :param process_id: Process identifier for tracking background operations.
    :type process_id: str | None
    :raises NotFoundException: If no sample item is found with the provided ID.
    :return: The updated sample item data as a dictionary.
    :rtype: dict[str, Any]
    """
    # verify instrument config exists
    if instrument_config and instrument_config.instrument_function_id is not None:
        await get_instrument_config(
            instrument_function_id=instrument_config.instrument_function_id
        )

    # Step 1: Fetch the existing sample item
    async with async_session() as session:
        existing_sample_item = await session.get(SampleItem, sample_item_id)
        if not existing_sample_item:
            raise NotFoundException(f"Sample item with ID '{sample_item_id}' not found")

        # Step 2: Update the sample item properties if anything changed
        update_data = sample_item.model_dump(exclude_unset=True)
        changed_fields = {
            key: value
            for key, value in update_data.items()
            if getattr(existing_sample_item, key) != value
        }
        if changed_fields:
            # Update only the changed fields
            for key, value in changed_fields.items():
                setattr(existing_sample_item, key, value)

            # Step 3: Update modification timestamp
            existing_sample_item.sample_item_utc_modified = datetime.now(timezone.utc)

            # Step 4: Commit the updates
            await session.commit()
            await session.refresh(existing_sample_item)

    # Step 5: Process instrument config
    sample = await fetch_sample(sample_item_id)
    current_instrument_id = getattr(sample, "instrument_function_id", None)

    # Process only if there's a new record or the instrument_function_id changed
    if (
        instrument_config.new_record
        or instrument_config.instrument_function_id != current_instrument_id
    ):
        background_tasks.add_task(
            process_instrument_config,
            filenames=[existing_sample_item.filename],
            instrument_config=instrument_config,
            independent_transaction=True,
            sid=sid,
            process_id=process_id,
        )
    # Step 6: Directly reload batch if needed # TODO_invalidation
    elif changed_fields:
        await sio.emit(
            "sample_batch_reload",
            room=existing_sample_item.sample_batch_id,
            namespace="/",
        )

    return {
        "message": f"Sample '{existing_sample_item.sample_item_name}' was updated.",
        "data": existing_sample_item.to_dict(),
    }


@api_controller()
async def delete_sample_item(sample_item_id: str):
    """
    Deletes a sample item by its unique identifier.

    Steps:
    1. Fetch the sample item by its ID from the database.
    2. If the sample item is found, delete it from the session and commit the changes to the database.
    3. Emit socket.io events to inform clients about the sample item deletion.

    :param sample_item_id: The unique identifier of the sample item to delete.
    :type sample_item_id: str
    :raises NotFoundException: If no sample item is found with the provided ID.
    """
    # Step 1: Fetch the sample item
    async with async_session() as session:
        sample_item = await session.get(SampleItem, sample_item_id)
        if not sample_item:
            raise NotFoundException(f"Sample item with ID '{sample_item_id}' not found")
        # Step 2: Delete the sample item and commit changes
        await session.delete(sample_item)
        await session.commit()
    # Step 3: Emit socket.io events
    await sio.emit(
        "sample_batch_reload",
        room=sample_item.sample_batch_id,
        namespace="/",
    )

    return {
        "message": f"Sample item '{sample_item.sample_item_name}' was deleted.",
    }


@api_controller_background_task(
    success_notification_rooms=["sid"],
    success_reload=[("sample_batch_reload", "sample_batch_id")],
    error_notification_rooms=["sid"],
)
async def copy_sample_item(
    sample_item_id: str,
    sample_batch_id: str,
    sample_item_name: str,
    independent_transaction: bool = False,
    background_tasks: BackgroundTasks = None,
    sid=None,
    process_id=None,
    parent_id=None,
) -> dict:
    """
    TODO_api_circular_import  destinguish sample and sample_item controller, should be mocveved to samples_controller.py?
    The function copies the specified sample item and associates the new copy with a specified sample batch.
    May be a part of the copy sample batch operation or independent.
    Copies matches, match interferences of the original sample if part of a larger copy batch operation
    or if it is copied to the same batch, since targets and ionization mechanisms are the same for original batch and new batch.
    Computes matches if it's an independent operation and target and original batch differ,
    since the targets and ionization mechanisms may differ between original batch and new batch.


    Steps:
    1. Validate the batch into which the sample is being copied.
    2. Fetch and validate the original sample item from the database.
    3. Create and add to session a new sample item with updated information.
    4. Copy matches and match interferences if copying to the same batch or as part of a larger copy batch operation.
    5. Commit the transaction to the database.
    6. If an independent operation, compute matches due to target changes.

    :param sample_item_id: ID of the original sample item to be copied.
    :type sample_item_id: str
    :param sample_batch_id: ID of the sample batch where the new item will be placed.
    :type sample_batch_id: str
    :param sample_item_name: Name for the new copied sample item.
    :type sample_item_name: str
    :param independent_transaction: Flag indicating whether the sample item copy is an independent transaction and if the operation should emit a reload event for the sample batch and if the sample should be rematched for new batch targets, defaults to False
    :type independent_transaction: bool, optional
    :param background_tasks: FastAPI background tasks for computing matches post-copy, defaults to None
    :type background_tasks: BackgroundTasks, optional
    :param sid: Session ID, used for emitting notifications to specific clients, defaults to None
    :type sid: str, optional
    :raises NotFoundException: If the original sample item is not found.
    :return: The newly created sample item dict.
    :rtype: dict
    """
    async with async_session() as session:
        # Step 1: Validate the batch into which the sample is being copied.
        batch = await session.get(SampleBatch, sample_batch_id)

        if not batch:
            raise NotFoundException(
                f"Sample batch with ID '{sample_batch_id}' not found"
            )

        # Step 2: Fetch and validate the original sample item along with related match records
        stmt = select(SampleItem).filter(SampleItem.sample_item_id == sample_item_id)
        result = await session.execute(stmt)
        original_sample_item = result.scalars().first()

        if not original_sample_item:
            raise NotFoundException(f"Sample item with ID '{sample_item_id}' not found")

        # Step 3: Create and add to session the new sample item with a new ID, name, batch and time of creation, but copy all other data
        new_sample_item_id = gen_id()
        new_sample_item_data = {
            c.name: getattr(original_sample_item, c.name)
            for c in SampleItem.__table__.columns
            if c.name != "sample_item_id"
        }
        new_sample_item_data.update(
            {
                "sample_item_id": new_sample_item_id,
                "sample_batch_id": sample_batch_id,
                "sample_item_name": sample_item_name,
                "sample_item_utc_created": datetime.now(timezone.utc),
            }
        )
        new_sample_item = SampleItem(**new_sample_item_data)
        session.add(new_sample_item)

        # Steps 4: Copy match records when called as part of copy_sample_batch or if sample is copied within the same batch
        if (
            not independent_transaction
            or original_sample_item.sample_batch_id == sample_batch_id
        ):
            # Prepare progress user notification for match copying
            notification = UserNotification(
                process_id=process_id,
                parent_id=parent_id,
                type="copy_sample_item",
                status="pending",
                message=f"Copying match records for sample '{sample_item_name}'.",
                data={
                    "sample_item_id": new_sample_item_id,
                    "sample_batch_id": sample_batch_id,
                    "_room_ids": [sid],
                    "_sid": sid,
                },
            )

            await copy_sample_item_match_data(
                original_sample_item.sample_item_id,
                new_sample_item_id,
                session,
                notification,
            )

        # Step 5: Commit the transaction
        await session.commit()
        await session.refresh(new_sample_item)

    # Step 6: Create task to compute the sample match data when called independently and not withing the same batch.
    if (
        independent_transaction
        and original_sample_item.sample_batch_id != sample_batch_id
    ):
        background_tasks.add_task(
            match_compute_sample,
            sample_item_id=new_sample_item_id,
            added_target_compound_ids=None,
            added_ionization_mechanism_ids=None,
            independent_transaction=independent_transaction,
            sid=sid,
            process_id=process_id,
        )

    # Step 7: Return the copied samle and message
    return {
        "message": f"Sample '{new_sample_item.sample_item_name}' was successfully copied to sample batch '{batch.sample_batch_name}'.",
        "data": new_sample_item.to_dict(),
        "_notification_data": {
            "sample_item_id": new_sample_item_id,
            "sample_batch_id": sample_batch_id,
        },
    }


@api_controller_background_task(
    success_notification_rooms=["sid"],
    error_notification_rooms=["sid"],
)
async def sample_item_export_peaks(
    sample_item_id: str,
    independent_transaction: bool = False,
    sid=None,
    process_id=None,
    parent_id=None,
):
    """Exports peak data for a specific sample item to a CSV file. This process involves loading sample file
    as a sample view, detecting peaks, and compiling peak data into a DataFrame before saving it to a file.

    Peak data is exported as a CSV file with the following columns:
    - datetime: The date and time of the scan in the local timezone.
    - datetime_utc: The date and time of the scan in UTC.
    - tic: The total ion current for the scan.
    - mz: The mass-to-charge ratio of the peak.
    - intensity: The intensity of the peak in each scan.
    - unit: The unit of the intensity value (ions for TOF or relative for Orbitrap).
    - sample_batch_name: The name of the sample batch.
    - sample_item_name: The name of the sample item.
    - filename: The filename of the sample file.
    - filter_id: The ID of the filter used.
    - sample_item_type: The type of the sample item.
    - sample_file_id: The ID of the sample file.
    - sample_item_id: The ID of the sample item.
    - instrument: The type of the instrument used for the sample file.

    :param sample_item_id: ID of the sample item.
    :type sample_item_id: str
    :param independent_transaction: Flag to indicate if the operation should be treated as an independent transaction, defaults to False.
    :type independent_transaction: bool, optional
    :param sid: Session ID for targeting specific clients when emitting events, defaults to None.
    :type sid: str, optional
    """
    # Get sample item data as a sample view
    sample_item_result = await get_sample(sample_item_id)
    sample_item = sample_item_result.get("data")
    sample_item_name = sample_item["sample_item_name"]

    # Get sample batch name
    sample_batch_id = sample_item["sample_batch_id"]
    sample_batch_data = await fetch_sample_batch_data(sample_batch_id)
    sample_batch_name = sample_batch_data.sample_batch_name

    # Prepare notification
    notification = UserNotification(
        process_id=process_id,
        parent_id=parent_id,
        type="sample_item_export_peaks",
        status="pending",
        message=f"Exporting peak data for sample item '{sample_item_name}'",
        # NOTE set the internal room_ids for the pending user_notifications and sid of the user, will be removed from the data.
        data={
            "sample_item_id": sample_item_id,
            "sample_batch_id": sample_batch_id,
            "_room_ids": [sid],
            "_sid": sid,
        },
    )

    await send_progress_user_notification(notification, 0.1)

    try:
        filename = sample_item["filename"]
        instrument_functions = await read_instrument_functions(filename=filename)
        instrument_type = get_instrument_type(filename)

        await send_progress_user_notification(notification, 0.1)

        # Assign peak fitting threshold and peak abundance units
        # depending on the instrument type
        # Correct intrument type unsured by get_instrument_type
        if instrument_type == "orbi":
            threshold = 0.8
            peak_data_type = "peak_heights"
        if instrument_type == "tof":
            threshold = 0.9
            peak_data_type = "peak_areas"
        sample_file = await detect_peaks(
            filename,
            instrument_functions,
            threshold,
            u_list=None,
            if_exists="append",
            instrument_type=instrument_type,
        )

        sample_peak_data = sample_file[peak_data_type].dropna(dim="mz", how="all")

        await send_progress_user_notification(notification, 0.8)
    except Exception as e:
        runtime.logger.error(repr(e))

    # Get scan timestamps
    base_datetime = sample_item["datetime"]
    scan_timestamps = pd.to_timedelta(
        sample_peak_data.time.values, unit="s"
    ) + pd.Timestamp(base_datetime)
    # Get scan timestamps UTC
    base_datetime_utc = sample_item["datetime_utc"]
    scan_timestamps_utc = pd.to_timedelta(
        sample_peak_data.time.values, unit="s"
    ) + pd.Timestamp(base_datetime_utc)

    # Get ticks for each time scan
    scan_tics = load_signal(filename).sum(dim="mz").signal.values

    mz_values = sample_peak_data.mz.values
    intensities = sample_peak_data.values.T  # Transpose to get (n_scans, n_mz)

    # Create arrays for the repeated values
    repeated_datetimes = np.repeat(
        scan_timestamps.values[:, np.newaxis], len(mz_values), axis=1
    )
    repeated_datetimes_utc = np.repeat(
        scan_timestamps_utc.values[:, np.newaxis], len(mz_values), axis=1
    )
    repeated_tics = np.repeat(scan_tics[:, np.newaxis], len(mz_values), axis=1)
    repeated_mz = np.repeat(mz_values, len(scan_timestamps))

    # Create the final DataFrame
    batch_peak_df = pd.DataFrame(
        {
            "datetime": repeated_datetimes.T.flatten(),
            "datetime_utc": repeated_datetimes_utc.T.flatten(),
            "tic": repeated_tics.T.flatten(),
            "mz": repeated_mz.flatten(),
            "intensity": intensities.flatten(),
        }
    ).assign(
        unit="ions" if instrument_type == "tof" else "rel.",
        sample_batch_name=sample_batch_name,
        sample_item_name=sample_item_name,
        filename=filename,
        filter_id=sample_item["filter_id"],
        sample_item_type=sample_item["sample_item_type"],
        sample_file_id=sample_item["sample_file_id"],
        sample_item_id=sample_item["sample_item_id"],
        instrument=instrument_type,
    )

    await send_progress_user_notification(notification, 1)

    # Get the current date and time as a string for a filename
    dt_str = datetime.now().isoformat().replace("-", "").replace(":", "").split(".")[0]

    # Save the peak data to a CSV file
    peakfile_path = get_filestore_path()
    peakfile_filename = "_".join(
        [dt_str, "peak_data", sample_item_name.replace(" ", "_") + ".csv"]
    )
    runtime.logger.info(f"Writing peak data to file {peakfile_filename}")
    batch_peak_df.to_csv(
        os.path.join(peakfile_path, peakfile_filename), index=False, sep=";"
    )
    message = f"Peak data for sample item '{sample_item_name}' was exported to file '{peakfile_filename}' and saved to '{peakfile_path}'."
    runtime.logger.info(message)

    # Return the status message
    return {
        "message": message,
        "data": {"filename": peakfile_filename},
        "_notification_data": {
            "sample_item_id": sample_item_id,
        },
    }
