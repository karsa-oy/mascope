import os
from datetime import datetime
from fastapi import UploadFile
from sqlalchemy import (
    select,
    asc,
    desc,
    func,
)
from typing import Literal
from mascope_lib.file_func import load_file, sum_signal_for_time_range
from mascope_lib.peak import detect_peaks, get_peaks
from mascope_lib.file_func import get_instrument_type
from mascope_server.socket import sio
from mascope_server.db import async_session
from mascope_server.db.id import gen_id
from mascope_server.db.models import SampleFile, User
from mascope_server.api.new.auth.access_token.service import get_access_token
from mascope_server.api.new.instruments import get_instruments
from mascope_server.api.new.instrument_configs.lib import (
    read_instrument_functions,
)
from mascope_server.api.lib.api_features import (
    api_controller,
    api_controller_background_task,
)
from mascope_server.api.lib.exceptions.api_exceptions import (
    ApiException,
    NotFoundException,
)
from mascope_server.api.models.sample.files.sample_file_pydantic_model import (
    SampleFileCreate,
    SampleFileUpdate,
)
from mascope_server.socket import event_emitter
from mascope_server.socket.notifications import (
    UserNotification,
    emit_user_notification,
)


from mascope_server.runtime import runtime

# ---------------------
# Sample file CRUD controllers
# ---------------------


@api_controller()
async def get_sample_files(
    datetime_min: datetime = None,
    datetime_max: datetime = None,
    instrument: str = None,
    filename: str = None,
    sort: str = "datetime_utc",
    order: str = "asc",
    page: int = 0,
    limit: int = 10000,
) -> dict:
    """
    Retrieves a paginated list of sample files, optionally filtered by date range, instrument, or filename, and sorted by a specified column.

    Steps:
    1. Construct a query to select all sample files.
    2. Apply filtering based on provided date range, instrument, and filename parameters.
    3. Apply sorting based on the provided sort and order parameters.
    4. Apply pagination based on the provided page and limit parameters.
    5. Execute the query and fetch the results.
    6. Convert the results into a list of dictionaries for JSON serialization.

    :param datetime_min: Minimum date and time for filtering sample files, optional.
    :type datetime_min: datetime, optional
    :param datetime_max: Maximum date and time for filtering sample files, optional.
    :type datetime_max: datetime, optional
    :param instrument: Instrument name for filtering sample files, optional.
    :type instrument: str, optional
    :param filename: Filename for filtering sample files, optional.
    :type filename: str, optional
    :param sort: Column to sort by, defaults to "datetime_utc".
    :type sort: str, optional
    :param order: Sorting order, "asc" for ascending or "desc" for descending, defaults to "asc".
    :type order: str, optional
    :param page: Page number for pagination, defaults to 0.
    :type page: int, optional
    :param limit: Number of items per page, defaults to 10000.
    :type limit: int, optional
    :return: A dictionary containing the total count of filtered sample files and a list of sample file details.
    :rtype: dict
    """
    async with async_session() as session:
        # Step 1: Construct query
        stmt = select(SampleFile)

        # Step 2: Apply filters
        if datetime_min:
            stmt = stmt.where(SampleFile.datetime_utc >= datetime_min)
        if datetime_max:
            stmt = stmt.where(SampleFile.datetime_utc <= datetime_max)
        if instrument:
            stmt = stmt.where(SampleFile.instrument == instrument)
        if filename:
            stmt = stmt.where(SampleFile.filename.contains(filename))

        # Step 3: Apply sorting
        stmt = (
            stmt.order_by(desc(getattr(SampleFile, sort)))
            if order == "desc"
            else stmt.order_by(asc(getattr(SampleFile, sort)))
        )

        # Step 4: Apply pagination
        total = await session.scalar(
            select(func.count()).select_from(stmt)  # pylint: disable=not-callable
        )
        stmt = stmt.offset(page * limit).limit(limit)

        # Step 5: Execute query and fetch results
        result = await session.execute(stmt)
        sample_files = result.scalars().all()

        # Step 6: Return results
        return {
            "message": "Sample files retrieved successfully.",
            "results": total,
            "data": [sample_file.to_dict() for sample_file in sample_files],
        }


@api_controller()
async def get_sample_file(sample_file_id: str) -> dict:
    """
    Retrieves a single sample file by its unique ID.

    Steps:
    1. Execute a query to fetch the sample file with the specified ID.
    2. Check if the sample file exists. If not, raise a NotFoundException.
    3. Return the sample file's details as a dictionary.

    :param sample_file_id: Unique identifier of the sample file to retrieve.
    :type sample_file_id: str
    :raises NotFoundException: If the sample file with the given ID is not found.
    :return: The requested sample file's details.
    :rtype: dict
    """
    async with async_session() as session:
        # Step 1: Fetch sample file by ID
        sample_file = await session.get(SampleFile, sample_file_id)

        # Step 2: Check existence
        if not sample_file:
            raise NotFoundException(f"Sample file with ID '{sample_file_id}' not found")

        # Step 3: Return sample file details
        return {
            "message": f"Sample file '{sample_file.filename}' retrieved successfully.",
            "data": sample_file.to_dict(),
        }


@api_controller()
async def create_sample_file(sample_file: SampleFileCreate) -> dict:
    """
    Creates a new sample file with the given data.

    Steps:
    1. Construct a new SampleFile object with provided data and add it to the session.
    2. Commit the transaction to persist the new sample file in the database.
    3. Refresh the instance to get the created data from the database.
    4. Emit a 'sample_file_created' event with the filename and instrument.
    5. Ensure instruments are reloaded
    6. Return the created sample file data.

    :param sample_file: Data for creating the sample file.
    :type sample_file: SampleFileCreate
    :raises NotFoundException: If the new sample file is not found after creation.
    :return: The created sample file data.
    :rtype: dict
    """
    async with async_session() as session:
        initial_instruments = [
            i["instrument"] for i in (await get_instruments())["data"]
        ]

        # Step 1: Construct new sample file
        new_sample_file = SampleFile(
            sample_file_id=gen_id(16), **sample_file.model_dump()
        )
        session.add(new_sample_file)

        # Step 2: Commit transaction
        await session.commit()

        # Step 3: Refresh instance
        await session.refresh(new_sample_file)

        # Step 4: Emit create_sample_file event
        notification = UserNotification(
            process_id=gen_id(8),
            type="create_sample_file",
            status="success",
            message=f"Sample file record '{sample_file.filename}' created.",
            data={
                "filename": sample_file.filename,
                "instrument": sample_file.instrument,
            },
        )
        await emit_user_notification(notification, sample_file.instrument)

        # Step 5. Trigger instruments reload
        if sample_file.instrument not in initial_instruments:
            # instrument added by creation and needs reload
            await sio.emit(
                "instruments_reload",
                namespace="/",
            )

        # Step 6: Return created sample file
        return {
            "message": f"Sample file '{new_sample_file.filename}' created successfully.",
            "data": new_sample_file.to_dict(),
        }


@api_controller()
async def delete_sample_file(sample_file_id: str):
    """
    Deletes a sample file by its unique ID.

    Steps:
    1. Fetch the sample file from the database using the provided ID.
    2. Delete the fetched sample file from the session and commit the changes to the database.
    3. Conditionally reload instruments

    :param sample_file_id: The ID of the sample file to delete.
    :type sample_file_id: str
    :raises NotFoundException: If the sample file with the given ID is not found.
    """
    async with async_session() as session:
        # Step 1: Fetch the sample file
        sample_file = await session.get(SampleFile, sample_file_id)
        if not sample_file:
            raise NotFoundException(f"Sample file with ID '{sample_file_id}' not found")

        # Step 2: Delete and commit
        await session.delete(sample_file)
        await session.commit()

        # Step 3: Trigger instruments reload
        final_instruments = [i["instrument"] for i in (await get_instruments())["data"]]
        if sample_file.instrument not in final_instruments:
            # instrument removed by deletion and needs reload
            await sio.emit(
                "instruments_reload",
                namespace="/",
            )

    return {
        "message": f"Sample file '{sample_file.filename}' deleted successfully.",
    }


@api_controller()
async def update_sample_file(
    sample_file_id: str, sample_file_update_data: SampleFileUpdate
) -> dict:
    """
    Updates an existing sample file with new data.

    Steps:
    1. Fetch the existing sample file from the database using the provided ID.
    2. Update the sample file's properties with the new data.
    3. Commit the changes to the database.
    4. Refresh the instance to get updated data from the database.
    5. Reload instrument data.
    6. Return the updated sample file data.

    :param sample_file_id: The ID of the sample file to update.
    :type sample_file_id: str
    :param sample_file_update_data: New data for updating the sample file.
    :type sample_file_update_data: SampleFileUpdate
    :raises NotFoundException: If the sample file with the given ID is not found.
    :return: The updated sample file data.
    :rtype: dict
    """
    async with async_session() as session:
        initial_instruments = set(
            [i["instrument"] for i in (await get_instruments())["data"]]
        )

        # Step 1: Fetch the sample file
        sample_file = await session.get(SampleFile, sample_file_id)
        if not sample_file:
            raise NotFoundException(f"Sample file with ID '{sample_file_id}' not found")

        # Step 2: Update properties
        for key, value in sample_file_update_data.model_dump(
            exclude_unset=True
        ).items():
            setattr(sample_file, key, value)

        # Step 3: Commit changes
        await session.commit()

        # Step 4: Refresh instance
        await session.refresh(sample_file)

        # Step 5. Trigger instruments reload
        final_instruments = set(
            [i["instrument"] for i in (await get_instruments())["data"]]
        )
        if initial_instruments != final_instruments:
            # instruments changed by update and need reloading
            await sio.emit(
                "instruments_reload",
                namespace="/",
            )

        # Step 6: Return updated sample file
        return {
            "message": f"Sample file '{sample_file.filename}' updated successfully.",
            "data": sample_file.to_dict(),
        }


# ---------------------
# Sample file upload
# ---------------------


# TODO_configuration Default sample file upload params
FILE_UPLOAD_CHUNK_SIZE = 2 * 1024 * 1024  # 2 MB


@api_controller()
async def sample_file_upload(
    file: UploadFile, user: User, user_sid: str = None
) -> dict:
    """
    Handles the upload of a sample file and saves it to the `filestreams` directory.

    The file is read in chunks to avoid high memory usage and stored in the specified
    directory as defined in the runtime configuration.

    :param file: The uploaded file to be processed.
    :type file: UploadFile
    :param user: The authenticated user
    :type user: User
    :param user_sid : Scocket client session ID, used for protecting events received from file-converter service.
    :type user_sid : str, optional
    :return: A dictionary containing the success message.
    :rtype: dict
    """
    path = os.path.join(runtime.config.filestreams, file.filename)

    try:
        with open(path, "wb") as f:
            # read the file in chunks to ensure it doesn't fill memory
            while contents := file.file.read(FILE_UPLOAD_CHUNK_SIZE):
                f.write(contents)

        # Get service token for file converter, check it's valid
        access_token = await get_access_token(user=user, service_name="file-converter")
        # Emit internal event for file upload
        await event_emitter.emit(
            "file-converter.auth",
            {
                "filename": file.filename,
                "user_id": user.id,
                "username": user.username,
                "role_id": user.role_id,
                "access_token": access_token,
            },
        )
    except ApiException:
        raise
    except Exception as e:
        raise RuntimeError(f"Failed to upload file {file.filename}: {e}") from e
    finally:
        file.file.close()

    message = f"Successfully uploaded file {file.filename}"
    runtime.logger.info(message)

    return {"message": message}


# ---------------------
# Sample file peaks controllers
# ---------------------


@api_controller()
async def get_sample_file_peaks(
    sample_file_id: str, areas: bool, heights: bool
) -> dict:
    """
    Retrieves peaks from a specified sample file, with options to include areas and/or heights.

    Steps:
    1. Fetch the sample file details using the provided ID.
    2. Validate whether peak areas and/or heights are requested.
    3. Load the sample file data based on the selected options (areas, heights).
    4. Extract and format the peak data for each requested type.
    5. Return the data in a columnar format with a message.

    :param sample_file_id: The ID of the sample file.
    :type sample_file_id: str
    :param areas: If True, include peak areas in the response.
    :type areas: bool
    :param heights: If True, include peak heights in the response.
    :type heights: bool
    :raises NotFoundException: If the sample file is not found or hasn't been processed (no peak data available).
    :return: A dictionary with the peak data dict in columnar format:
        - "mz": list of mass/charge (m/z) values for each peak.
        - "area": list of peak areas (if requested).
        - "height": list of peak heights (if requested).
    :rtype: dict
    """

    # Step 1: Fetch the sample file details
    sample_file_data = await get_sample_file(sample_file_id)
    filename = sample_file_data.get("data").get("filename")

    # Step 2: Load the appropriate peak data based on the query params
    vars_to_load = []
    if areas:
        vars_to_load.append("peak_areas")
    if heights:
        vars_to_load.append("peak_heights")

    try:
        sample_file_data = load_file(filename, vars=vars_to_load)
    except FileNotFoundError as e:
        raise NotFoundException(
            f"Sample file with name '{filename}' was not found or has not been processed"
        ) from e

    # Step 3: Prepare the data structure for response
    response_data = {}

    # Step 4: Extract and format the data
    if areas:
        if "peak_areas" not in sample_file_data:
            raise NotFoundException(
                f"No peak areas found in sample file '{filename}', file may not have been processed"
            )
        peak_areas = get_peaks(sample_file_data, "area").sum(dim="time")
        response_data["mz"] = peak_areas.mz.values.tolist()
        response_data["area"] = peak_areas.values.tolist()

    if heights:
        if "peak_heights" not in sample_file_data:
            raise NotFoundException(
                f"No peak heights found in sample file '{filename}', file may not have been processed"
            )
        peak_heights = get_peaks(sample_file_data, "height").sum(dim="time")
        # If 'mz' was not populated from areas, populate it from heights
        if "mz" not in response_data:
            response_data["mz"] = peak_heights.mz.values.tolist()
        response_data["height"] = peak_heights.values.tolist()

    # Step 5: Format the response for the case where no peaks were detected
    if not response_data["mz"]:
        message = (
            f"No peaks found in sample file '{filename}'. "
            f"The file was processed, but no peaks were detected in the target m/z range. "
            f"Consider adjusting the targets or computing all peaks."
        )
        return {
            "message": message,
            "results": 0,
            "data": {
                "mz": [],
                "area": [] if areas else None,
                "height": [] if heights else None,
            },
        }

    # Step 6: Remove empty fields from the response (if only one type is requested)
    if not areas:
        response_data.pop("area", None)
    if not heights:
        response_data.pop("height", None)

    message = f"Successfully loaded {len(response_data['mz'])} peaks from sample file '{filename}'"
    return {
        "message": message,
        "results": len(response_data["mz"]),
        "data": response_data,
    }


@api_controller_background_task(
    success_notification_rooms=["sid"],
    error_notification_rooms=["sid"],
)
async def compute_all_sample_file_peaks(
    sample_file_id: str,
    if_exists: Literal["append", "replace"] = "append",
    independent_transaction: bool = False,
    sid: str = None,
    process_id=None,
    parent_id=None,
) -> dict:
    """
    Computes all peak data for a specific sample file, performing the operation as a background task.

    Steps:
    1. Fetch the sample file details using the provided ID.
    2. Load necessary instrument functions based on the filename.
    3. Determine the instrument type and set the appropriate threshold for peak detection.
    4. Execute the peak detection process.

    :param sample_file_id: ID of the sample file for which peaks are to be computed.
    :type sample_file_id: str
    :param independent_transaction: Flag to indicate if the operation should be treated as an independent transaction.
    :type independent_transaction: bool, optional
    :param sid: Session ID for targeting specific clients when emitting events, used for notifications.
    :type sid: str, optional
    :param process_id: Optional identifier for the processing task, used for tracking.
    :type process_id: Optional[str]
    :param parent_id: Optional identifier of the parent task, if this task is part of a larger workflow.
    :type parent_id: Optional[str]
    :return: A dictionary containing a message with the outcome and the data about the peaks detected.
    :rtype: dict
    """
    # Step 1: Fetch the sample file
    sample_file_data = await get_sample_file(sample_file_id)
    filename = sample_file_data.get("data").get("filename")

    # Step 2: Load instrument functions and determine instrument type.
    instrument_functions = await read_instrument_functions(filename=filename)
    instrument_type = get_instrument_type(filename)

    # Step 3: Set threshold based on instrument type.
    if instrument_type == "orbi":
        threshold = 0.8
    if instrument_type == "tof":
        threshold = 0.9

    # Step 4: Detect peaks.
    sample_file, list_of_peaks = await detect_peaks(
        filename,
        instrument_functions,
        threshold,
        u_list=None,
        if_exists=if_exists,
        return_peak_mzs=True,
        instrument_type=instrument_type,
    )

    # Return completion message and peak details.
    message = f"Detected {list_of_peaks.size} peaks for file '{filename}'"
    runtime.logger.info(message)

    await sio.emit("peak_reload", room=sample_file_id, namespace="/")

    return {
        "message": message,
        "_notification_data": {
            "sample_file_id": sample_file_id,
            "filename": filename,
        },
    }


@api_controller()
async def get_sample_file_peak_timeseries(
    sample_file_id: str, peak_mz: float, peak_mz_tolerance_ppm: float
) -> dict:
    """Get timeseries of a given peak in a given sample file.

    Returns the timeseries of a closest peak to a given m/z, if found
    within given m/z tolerance.

    Steps:
    1. Fetch the sample file details using the provided ID.
    2. Load the sample file data from its filename.
    3. Select the nearest peak to the requested m/z within the specified tolerance.
    4. Extract and return the timeseries data of the selected peak.

    :param sample_file_id: Sample file ID
    :type sample_file_id: str
    :param peak_mz: m/z of the peak to get timeseries for
    :type peak_mz: float
    :param peak_mz_tolerance_ppm: Tolerance for m/z difference
        for the requested peak and the nearest one found from data
    :type peak_mz_tolerance_ppm: float
    :raises HTTPException: Raised if sample file is not found
    :return: Dictionary with keys:
        "mz": m/z of the peak in sample file (None if no peak within tolerance)
        "height": peak height at time points (empty if no peak within tolerance)
        "time": time coordinates (empty if no peak within tolerance)
    :rtype: dict
    """
    # Step 1: Fetch the sample file details using the provided ID.
    sample_file_data = await get_sample_file(sample_file_id)
    filename = sample_file_data.get("data").get("filename")
    # Step 2: Load the sample file
    try:
        sample_file = load_file(filename, vars=["peak_heights"])
        peaks = get_peaks(sample_file, "height")
    except FileNotFoundError:
        raise NotFoundException(f"Sample file with name '{filename}' not found")

    # Step 3: From sample file peaks, select nearest to requested peak m/z
    peak_timeseries = peaks.sel(mz=peak_mz, method="nearest")
    peak_mz_data = peak_timeseries.mz.item()
    # Calculate difference of the sample peak m/z to requested peak m/z
    mz_diff = peak_mz_data - peak_mz  # [Th]
    mz_diff_ppm = mz_diff / peak_mz * 1e6  # [ppm]

    # Step 4: Extract and return timeseries data
    if abs(mz_diff_ppm) > peak_mz_tolerance_ppm:
        # No peak found within given m/z tolerance
        return {
            "results": 0,
            "data": {
                "mz": None,
                "height": [],
                "time": [],
            },
        }

    return {
        "message": f"Successfully retrieved timeseries for peak m/z {peak_mz} in '{filename}'.",
        "results": len(peak_timeseries.time.values),
        "data": {
            "mz": peak_mz_data,
            "height": peak_timeseries.values.tolist(),
            "time": peak_timeseries.time.values.tolist(),
        },
    }


# ---------------------
# Sample file spectrum controllers
# ---------------------


@api_controller()
async def get_sample_file_spectrum(
    sample_file_id: str,
    t_min: float = None,
    t_max: float = None,
    mz_min: float = None,
    mz_max: float = None,
) -> dict:
    """
    Retrieves the mass spectrum from a specified sample file within optional time and m/z ranges.

    The function performs the following steps:
    1. Fetch the sample file from the database.
    2. Determines whether to load the full 'sum_signal' dataset or a specific time range from the 'signal' dataset based on provided time range parameters (t_min and t_max).
    3. Sums the data over the time dimension to obtain the spectrum.
    4. If an m/z range is specified, slices the spectrum to this m/z range.
    5. Extracts m/z values and their corresponding intensities from the spectrum.
    6. Returns the spectrum data and the total number of m/z values.

    :param sample_file_id: Unique identifier for the sample file from which to retrieve the spectrum.
    :type sample_file_id: str
    :param t_min: Start of the optional time range, defaults to None.
    :type t_min: float, optional
    :param t_max: End of the optional time range, defaults to None.
    :type t_max: float, optional
    :param mz_min: Start of the optional m/z range, defaults to None.
    :type mz_min: float, optional
    :param mz_max: End of the optional m/z range, defaults to None.
    :type mz_max: float, optional
    :raises process_exception: Handles exceptions and raises an informative error message.
    :return: A dictionary containing the total number of data points, and arrays of m/z values and their corresponding intensities.
    :rtype: dict
    """
    # Step 1: Fetch sample file info from the database
    sample_file_data = await get_sample_file(sample_file_id)
    filename = sample_file_data.get("data").get("filename")
    # Derive intensity units from instrument type
    instrument_type = get_instrument_type(filename)
    intensity_unit = ("ions" if instrument_type == "tof" else "rel.",)

    # Step 2: Load the sample file and determine whether to use the full signal or a time slice and calculate the corresponding spectrum DataArray
    runtime.logger.info(f"Loading file: {filename}")
    time_data_points = None

    # Step 3: Sum over the time dimension
    spectrum = sum_signal_for_time_range(filename, t_min, t_max)

    # Step 4: Apply m/z range if provided
    if mz_min is not None and mz_max is not None:
        spectrum = spectrum.sel(mz=slice(mz_min, mz_max))

    # Compute the final, sliced spectrum results
    spectrum = spectrum.compute()

    # Step 5: Extract m/z values and intensities
    mz_values = spectrum.mz.values.tolist()
    intensity_values = spectrum.values.tolist()

    # Step 6: Return the total count, optional spectrum count, and data
    message = f"Retrieved spectrum data with {len(mz_values)} m/z points from sample file '{filename}'."
    if time_data_points is not None:
        message += f" Time range specified with {time_data_points} data points."

    return {
        "message": message,
        "results": len(mz_values),
        **(
            {"spectrum_count": time_data_points} if time_data_points is not None else {}
        ),
        "data": {
            "mz": mz_values,
            "intensity": intensity_values,
            "intensity_unit": intensity_unit,
        },
    }
