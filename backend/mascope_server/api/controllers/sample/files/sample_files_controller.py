from datetime import datetime
import numpy as np
from sqlalchemy import (
    select,
    asc,
    desc,
    func,
)
from mascope_lib.file_func import load_file
from mascope_lib.peak import detect_peaks, get_peaks
from mascope_lib.file_func import get_instrument_type
from mascope_server.app import sio
from mascope_server.db import async_session
from mascope_server.db.id import gen_id
from mascope_server.db.models import SampleFile
from mascope_server.api.controllers.instrument_functions.lib.instrument_functions_fetch import (
    read_instrument_functions,
)
from mascope_server.api.lib.api_features import (
    api_controller,
    api_controller_background_task,
)
from mascope_server.api.lib.exceptions.api_exceptions import NotFoundException
from mascope_server.api.models.sample.files.sample_file_pydantic_model import (
    SampleFileCreate,
    SampleFileUpdate,
)
from mascope_server.api.lib.notifications.api_notification import (
    emit_user_notification,
)
from mascope_server.api.lib.notifications.api_notification_pydantic_model import (
    UserNotification,
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
        return sample_file.to_dict()


@api_controller()
async def create_sample_file(sample_file: SampleFileCreate) -> dict:
    """
    Creates a new sample file with the given data.

    Steps:
    1. Construct a new SampleFile object with provided data and add it to the session.
    2. Commit the transaction to persist the new sample file in the database.
    3. Refresh the instance to get the created data from the database.
    4. Emit a 'sample_file_created' event with the filename and instrument.
    5. Return the created sample file data.

    :param sample_file: Data for creating the sample file.
    :type sample_file: SampleFileCreate
    :raises NotFoundException: If the new sample file is not found after creation.
    :return: The created sample file data.
    :rtype: dict
    """
    async with async_session() as session:
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

        # Step 5: Return created sample file
        return new_sample_file.to_dict()


@api_controller()
async def delete_sample_file(sample_file_id: str):
    """
    Deletes a sample file by its unique ID.

    Steps:
    1. Fetch the sample file from the database using the provided ID.
    2. Delete the fetched sample file from the session and commit the changes to the database.

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
    5. Return the updated sample file data.

    :param sample_file_id: The ID of the sample file to update.
    :type sample_file_id: str
    :param sample_file_update_data: New data for updating the sample file.
    :type sample_file_update_data: SampleFileUpdate
    :raises NotFoundException: If the sample file with the given ID is not found.
    :return: The updated sample file data.
    :rtype: dict
    """
    async with async_session() as session:
        # Step 1: Fetch the sample file
        sample_file = await session.get(SampleFile, sample_file_id)
        if not sample_file:
            raise NotFoundException(f"Sample file with ID '{sample_file_id}' not found")

        # Step 2: Update properties
        for key, value in sample_file_update_data.dict(exclude_unset=True).items():
            setattr(sample_file, key, value)

        # Step 3: Commit changes
        await session.commit()

        # Step 4: Refresh instance
        await session.refresh(sample_file)

        # Step 5: Return updated sample file
        return sample_file.to_dict()


# ---------------------
# Sample file peaks controllers
# ---------------------


@api_controller()
async def get_sample_file_peaks(sample_file_id: str) -> dict:
    """
    Retrieves peaks from a specified sample file.

    Steps:
    1. Fetch the sample file details using the provided ID.
    2. Load the sample file data from its filename.
    3. Extract peaks from the sample file.
    4. Format and return the peak data.

    :param sample_file_id: Sample file ID
    :type sample_file_id: str
    :raises NotFoundException: If the instrument sample file with the given filename is not found.
    :return: Dictionary with keys:
        "mz": list of m/z of the peaks in sample file
        "intensity": peak intensity (area)
    :rtype: dict
    """
    # Step 1: Fetch the sample file details using the provided ID.
    sample_file = await get_sample_file(sample_file_id)
    filename = sample_file["filename"]

    # Step 2: Load the sample file
    try:
        sample_file = load_file(filename, vars=["peak_areas"])
    except FileNotFoundError as e:
        raise NotFoundException(f"Sample file with name '{filename}' not found") from e
    # Step 3: Extract peaks
    if "peak_areas" not in sample_file:
        raise NotFoundException(f"No peak areas found in sample file '{filename}'")
    peaks = get_peaks(sample_file, "area").sum(dim="time")
    # Step 4: Format and return data
    return {
        "total": len(peaks.mz.values),
        "data": {
            "mz": list(peaks.mz.values.astype(float)),
            "intensity": list(peaks.values.astype(float)),
        },
    }


@api_controller_background_task(
    success_notification_rooms=["sid"],
    error_notification_rooms=["sid"],
)
async def compute_all_sample_file_peaks(
    sample_file_id: str,
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
    sample_file = await get_sample_file(sample_file_id)
    filename = sample_file["filename"]

    # Step 2: Load instrument functions and determine instrument type.
    instrument_functions = await read_instrument_functions(filename)
    instrument_type = get_instrument_type(filename)

    # Step 3: Set threshold based on instrument type.
    if instrument_type == "orbi":
        threshold = 0.8
    if instrument_type == "tof":
        threshold = 0.9

    # Step 4: Detect peaks.
    sample_file, all_peak_mzs = await detect_peaks(
        filename,
        instrument_functions,
        threshold,
        u_list=None,
        if_exists="append",
        return_peak_mzs=True,
        instrument_type=instrument_type,
    )
    list_of_peaks = all_peak_mzs.astype(np.float32)

    # Return completion message and peak details.
    message = f"Detected {len(list_of_peaks)} peaks for file '{filename}'"
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
        "intensity": peak height at time points (empty if no peak within tolerance)
        "time": time coordinates (empty if no peak within tolerance)
    :rtype: dict
    """
    # Step 1: Fetch the sample file details using the provided ID.
    sample_file = await get_sample_file(sample_file_id)
    filename = sample_file["filename"]
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
            "total": 0,
            "data": {
                "mz": None,
                "intensity": [],
                "time": [],
            },
        }

    return {
        "total": len(peak_timeseries.time.values),
        "data": {
            "mz": peak_mz_data,
            "intensity": list(peak_timeseries.values.astype(float)),
            "time": list(peak_timeseries.time.values.astype(float)),
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
    3. If a time range is specified, finds the closest matching time coordinates in the dataset and slices the dataset to this time range.
    4. Sums the data over the time dimension to obtain the spectrum.
    5. If an m/z range is specified, slices the spectrum to this m/z range.
    6. Extracts m/z values and their corresponding intensities from the spectrum.
    7. Returns the spectrum data and the total number of m/z values.

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
    sample_file = await get_sample_file(sample_file_id)
    filename = sample_file["filename"]

    # Step 2: Load the sample file and determine whether to use the full signal or a time slice and calculate the corresponding spectrum DataArray
    runtime.logger.info(f"Loading file: {filename}")
    time_data_points = None

    # Step 3: If a time range is specified, finds the closest matching time coordinates in the dataset and slices the dataset to this time range.
    if t_min is not None and t_max is not None:
        # Load the 'signal' data for specific time range
        sample_file = load_file(filename, vars=["signal"])

        # Find the closest time points in the data to the provided time range
        closest_t_min = sample_file.time.sel(time=t_min, method="nearest").item()
        closest_t_max = sample_file.time.sel(time=t_max, method="nearest").item()

        # Slice the dataset for the time range
        sample_file_slice = sample_file.sel(time=slice(closest_t_min, closest_t_max))

        # Check the number of data points in the time coordinate
        time_data_points = sample_file_slice.sizes["time"]

        # Step 4: Sum over the time dimension
        spectrum = sample_file_slice.sum(dim="time")["signal"]
    else:
        # Load the 'sum_signal' for the entire time range
        sample_file = load_file(filename, vars=["sum_signal"])
        spectrum = sample_file["sum_signal"]

    # Step 5: Apply m/z range if provided
    if mz_min is not None and mz_max is not None:
        spectrum = spectrum.sel(mz=slice(mz_min, mz_max))

    # Compute the final, sliced spectrum results
    spectrum = spectrum.compute()

    # Step 6: Extract m/z values and intensities
    mz_values = spectrum.mz.values.tolist()
    intensity_values = spectrum.values.tolist()

    # Step 7: Return the total count, optional spectrum count, and data
    return {
        "total": len(mz_values),
        **(
            {"spectrum_count": time_data_points} if time_data_points is not None else {}
        ),
        "data": {"mz": mz_values, "intensity": intensity_values},
    }
