from fastapi import HTTPException
from sqlalchemy import asc, desc, func, and_, cast, Float
from sqlalchemy.future import select
from datetime import datetime
from backend.db_api_rest import async_session
from backend.socket_events import sio
from backend.db.id import gen_id
from ..utils.api_features import api_controller
from ..exceptions import NotFoundException
from ..models.models import SampleFile
from ..models.pydantic_models.sample_file_pydantic_model import (
    SampleFileCreate,
    SampleFileUpdate,
)

from lib.file_func import load_file
from lib.peak import get_peaks


# ===================================================================
# Controller functions
# ===================================================================

# ---------------------
# CRUD functions
# ---------------------


@api_controller(error_message="Failed to retrieve sample files")
async def get_sample_files(
    minDatetime: datetime = None,
    maxDatetime: datetime = None,
    instrument: str = None,
    filename: str = None,
    sort: str = None,
    order: str = None,
    page: int = 0,
    limit: int = 10000,
):
    async with async_session() as session:
        stmt = select(SampleFile)

        if minDatetime and maxDatetime:
            stmt = stmt.where(
                and_(
                    cast(func.julianday(SampleFile.datetime_utc), Float)
                    >= func.julianday(minDatetime),
                    cast(func.julianday(SampleFile.datetime_utc), Float)
                    <= func.julianday(maxDatetime),
                )
            )

        if instrument:
            stmt = stmt.where(SampleFile.instrument == instrument)

        if filename:
            stmt = stmt.where(SampleFile.filename == filename)

        if sort:
            if order == "desc":
                stmt = stmt.order_by(desc(getattr(SampleFile, sort)))
            else:
                stmt = stmt.order_by(asc(getattr(SampleFile, sort)))

        # Get total count
        count_stmt = select(func.count()).select_from(stmt)
        total = await session.scalar(count_stmt)

        # Get paginated results
        stmt = stmt.offset(page * limit).limit(limit)
        result = await session.execute(stmt)
        sample_files = result.scalars().all()

        return {
            "results": total,
            "data": [sample_file.to_dict() for sample_file in sample_files],
        }


@api_controller(error_message="Failed to get sample file")
async def get_sample_file(sample_file_id: str):
    async with async_session() as session:
        stmt = select(SampleFile).filter(SampleFile.sample_file_id == sample_file_id)
        result = await session.execute(stmt)
        sample_file = result.scalars().first()

        if not sample_file:
            raise NotFoundException(f"Sample file with ID {sample_file_id} not found")

        return sample_file.to_dict()


@api_controller(error_message="Failed to create sample file")
async def create_sample_file(sample_file: SampleFileCreate):
    async with async_session() as session:
        new_sample_file = SampleFile(
            sample_file_id=gen_id(16),
            filename=sample_file.filename,
            instrument=sample_file.instrument,
            datetime=sample_file.datetime,
            datetime_utc=sample_file.datetime_utc,
            length=sample_file.length,
            range=sample_file.range,
            mz_calibration=sample_file.mz_calibration,
            tic=sample_file.tic,
        )
        session.add(new_sample_file)
        await session.commit()
        await session.refresh(new_sample_file)

        if not new_sample_file:
            raise NotFoundException(
                f"Failed to create sample file {sample_file.filename}"
            )

        await sio.emit(
            "sample_file_created",
            sample_file.filename,
            room=sample_file.instrument,
            namespace="/",
        )
        return new_sample_file


@api_controller(error_message="Failed to delete sample file")
async def delete_sample_file(sample_file_id: str):
    async with async_session() as session:
        result = await session.execute(
            select(SampleFile).filter(SampleFile.sample_file_id == sample_file_id)
        )
        sample_file = result.scalar_one_or_none()
        if not sample_file:
            raise NotFoundException(f"Sample file with ID {sample_file_id} not found")

        await session.delete(sample_file)
        await session.commit()


@api_controller(error_message="Failed to update sample file")
async def update_sample_file(
    sample_file_id: str, sample_file_update_data: SampleFileUpdate
):
    async with async_session() as session:
        sample_file = await session.get(SampleFile, sample_file_id)
        if not sample_file:
            raise NotFoundException(f"Sample file with ID {sample_file_id} not found")

        for key, value in sample_file_update_data.dict(exclude_unset=True).items():
            setattr(sample_file, key, value)

        await session.commit()
        await session.refresh(sample_file)

        return sample_file


# ---------------------
# Peak functions
# ---------------------


@api_controller(error_message="Failed to get peaks of given sample file")
async def get_sample_file_peaks(sample_file_id: str) -> dict:
    """Get peaks of given sample file

    :param sample_file_id: Sample file ID
    :type sample_file_id: str
    :raises HTTPException: Raised if sample file is not found
    :return: Dictionary with keys:
        "mz": list of m/z of the peaks in sample file
        "intensity": peak intensity (area)
    :rtype: dict
    """
    sample_file = await get_sample_file(sample_file_id)
    filename = sample_file["filename"]
    try:
        sample_file = load_file(filename, vars=["peak_areas"])
        peaks = get_peaks(sample_file, "area").sum(dim="time")
    except FileNotFoundError:
        raise NotFoundException(f"Sample file with name {filename} not found")

    return {
        "total": len(peaks.mz.values),
        "data": {
            "mz": list(peaks.mz.values.astype(float)),
            "intensity": list(peaks.values.astype(float)),
        },
    }


@api_controller(
    error_message="Failed to get timeseries of a given peak in a given sample file"
)
async def get_sample_file_peak_timeseries(
    sample_file_id: str, peak_mz: float, peak_mz_tolerance_ppm: float
) -> dict:
    """Get timeseries of a given peak in a given sample file.

    Returns the timeseries of a closest peak to a given m/z, if found
    within given m/z tolerance.

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

    sample_file = await get_sample_file(sample_file_id)
    filename = sample_file["filename"]
    try:
        sample_file = load_file(filename, vars=["peak_heights"])
        peaks = get_peaks(sample_file, "height")
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Sample file with name {filename} not found",
        )
    # From sample file peaks, select nearest to requested peak m/z
    peak_timeseries = peaks.sel(mz=peak_mz, method="nearest")
    peak_mz_data = peak_timeseries.mz.item()
    # Calculate difference of the sample peak m/z to requested peak m/z
    mz_diff = peak_mz_data - peak_mz  # [Th]
    mz_diff_ppm = mz_diff / peak_mz * 1e6  # [ppm]
    if abs(mz_diff_ppm) > peak_mz_tolerance_ppm:
        # No peak found within given m/z tolerance
        return {
            "total": 0,
            "data": {
                "mz": None,
                "intensity": [],
            },
            "time": [],
        }

    return {
        "total": len(peak_timeseries.time.values),
        "data": {
            "mz": peak_mz_data,
            "intensity": list(peak_timeseries.values.astype(float)),
            "time": list(peak_timeseries.time.values.astype(float)),
        },
    }


@api_controller(error_message="Failed to get spectrum for sample file")
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
    # Fetch sample file info from the database
    sample_file = await get_sample_file(sample_file_id)
    filename = sample_file["filename"]

    # Load the sample file and determine whether to use the full signal or a time slice and calculate the corresponding spectrum DataArray
    print("Loading file: %s" % filename)
    time_data_points = None
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

        # Compute the sum spectrum over the time range
        spectrum = sample_file_slice.sum(dim="time")["signal"].compute()
    else:
        # Load the 'sum_signal' for the entire time range
        sample_file = load_file(filename, vars=["sum_signal"])
        spectrum = sample_file["sum_signal"].compute()

    # Apply m/z range if provided
    if mz_min is not None and mz_max is not None:
        spectrum = spectrum.sel(mz=slice(mz_min, mz_max))

    # Extract m/z values and intensities
    mz_values = spectrum.mz.values.tolist()
    intensity_values = spectrum.values.tolist()

    # Return the total count, optional spectrum count, and data
    return {
        "total": len(mz_values),
        **(
            {"spectrum_count": time_data_points} if time_data_points is not None else {}
        ),
        "data": {"mz": mz_values, "intensity": intensity_values},
    }
