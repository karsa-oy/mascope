from fastapi import HTTPException, status
from sqlalchemy import asc, desc, func, and_, cast, Float
from sqlalchemy.future import select
from datetime import datetime
from backend.db_api_rest import async_session

from backend.socket_events import sio

from backend.db.id import gen_id
from ..models.models import SampleFile
from ..models.pydantic_models.sample_file_pydantic_model import (
    SampleFileCreate,
    SampleFileUpdate,
)

from lib.file_func import load_file
from lib.peak import get_peaks


# ===================================================================
# Helper functions
# ===================================================================


async def get_sample_file_filename_by_id(sample_file_id: str) -> str:
    async with async_session() as session:
        stmt = select(SampleFile.filename).filter(
            SampleFile.sample_file_id == sample_file_id
        )
        result = await session.execute(stmt)
        filename = result.scalars().first()

        if not filename:
            raise HTTPException(
                status_code=404,
                detail=f"SampleFile with ID {sample_file_id} not found",
            )

    return filename


# ===================================================================
# Controller functions
# ===================================================================

# ---------------------
# CRUD functions
# ---------------------


async def get_sample_files(
    sort: str = None,
    order: str = None,
    page: int = 0,
    limit: int = 100,
    minDatetime: datetime = None,
    maxDatetime: datetime = None,
    instrument: str = None,
    filename: str = None,
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


async def get_sample_file_by_id(sample_file_id: str):
    async with async_session() as session:
        stmt = select(SampleFile).filter(SampleFile.sample_file_id == sample_file_id)
        result = await session.execute(stmt)
        sample_file = result.scalars().first()

        if not sample_file:
            raise HTTPException(
                status_code=404,
                detail=f"SampleFile with ID {sample_file_id} not found",
            )

        return sample_file.to_dict()


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
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create sample file",
            )

        await sio.emit(
            "sample_file_created",
            sample_file.filename,
            room=sample_file.instrument,
            namespace="/",
        )
        return new_sample_file


async def delete_sample_file(sample_file_id: str):
    async with async_session() as session:
        result = await session.execute(
            select(SampleFile).filter(SampleFile.sample_file_id == sample_file_id)
        )
        sample_file = result.scalar_one_or_none()
        if not sample_file:
            raise HTTPException(status_code=404, detail="Sample file not found")

        await session.delete(sample_file)
        await session.commit()


async def update_sample_file(sample_file_id: str, sample_file: SampleFileUpdate):
    async with async_session() as session:
        db_sample_file = await session.get(SampleFile, sample_file_id)
        if not db_sample_file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sample file not found",
            )

        for key, value in sample_file.dict(exclude_unset=True).items():
            setattr(db_sample_file, key, value)

        await session.commit()
        await session.refresh(db_sample_file)

        return db_sample_file


# ---------------------
# Peak functions
# ---------------------


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
    filename = await get_sample_file_filename_by_id(sample_file_id)
    try:
        sample_file = load_file(filename, vars=["peak_areas"])
        peaks = get_peaks(sample_file, "area").sum(dim="time")
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Sample file with name {filename} not found",
        )

    return {
        "mz": list(peaks.mz.values.astype(float)),
        "intensity": list(peaks.values.astype(float)),
    }


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
        "mz": m/z of the peak in sample file
        "intensity": peak height at time points
        "time": time coordinates
    :rtype: dict
    """

    filename = await get_sample_file_filename_by_id(sample_file_id)
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
            "mz": None,
            "intensity": [],
            "time": [],
        }

    return {
        "mz": peak_mz_data,
        "intensity": list(peak_timeseries.values),
        "time": list(peak_timeseries.time.values),
    }
