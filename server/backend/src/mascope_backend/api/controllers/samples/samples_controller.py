# pylint: disable=line-too-long
from dataclasses import dataclass
from datetime import datetime
import asyncio
from mascope_file.io import load_file
import mascope_signal.compute as m_compute
from mascope_signal.peak import get_peaks
from sqlalchemy import and_, select, func, cast, Float
from mascope_backend.db import async_session
from mascope_backend.db.models import (
    Sample,
    MatchSample,
    MatchCollection,
    TargetCollection,
)
from mascope_backend.api.lib.api_features import api_controller
from mascope_backend.api.lib.exceptions.api_exceptions import NotFoundException
from mascope_backend.api.models.target.collections.config import (
    target_collection_config,
)
from mascope_backend.runtime import runtime


@api_controller()
async def get_samples(
    sample_item_id: str | None = None,
    sample_file_id: str | None = None,
    sample_batch_id: str | None = None,
    filename: str | None = None,
    instrument: str | None = None,
    sample_item_type: list[str] | None = None,
    datetime_min: datetime | None = None,
    datetime_max: datetime | None = None,
    polarity: list[str] | None = None,
    match_category_min: int | None = None,
) -> dict:
    """
    Retrieves samples with nested match data and alarming status.

    Includes match information if available, including alarming flag based
    on target collection types.

    :param sample_item_id: Filter by sample item ID, defaults to None
    :type sample_item_id: str | None
    :param sample_file_id: Filter by sample file ID, defaults to None
    :type sample_file_id: str | None
    :param sample_batch_id: Filter by sample batch ID, defaults to None
    :type sample_batch_id: str | None
    :param filename: Filter by filename, defaults to None
    :type filename: str | None
    :param instrument: Filter by instrument name, defaults to None
    :type instrument: str | None
    :param sample_item_type: Filter by sample item types, defaults to None
    :type sample_item_type: list[str] | None
    :param datetime_min: Filter samples after this datetime, defaults to None
    :type datetime_min: datetime | None
    :param datetime_max: Filter samples before this datetime, defaults to None
    :type datetime_max: datetime | None
    :param polarity: Filter by ion polarity modes, defaults to None
    :type polarity: list[str] | None
    :param match_category_min: Filter by minimum match category, defaults to None
    :type match_category_min: int | None
    :return: Dictionary with status, message, results count, and sample data with nested match information
    :rtype: dict
    """
    async with async_session() as session:
        stmt = (
            select(
                Sample,
                MatchSample,
                TargetCollection.target_collection_type.in_(
                    target_collection_config.APP_ALARMING_COLLECTION_TYPES
                ).label("alarming"),
            )
            .outerjoin(MatchSample, Sample.sample_item_id == MatchSample.sample_item_id)
            .outerjoin(
                MatchCollection,
                MatchCollection.sample_item_id == Sample.sample_item_id,
            )
            .outerjoin(
                TargetCollection,
                TargetCollection.target_collection_id
                == MatchCollection.target_collection_id,
            )
            .group_by(Sample.sample_item_id, MatchSample.sample_item_id)
        )

        if sample_item_id:
            stmt = stmt.filter(Sample.sample_item_id == sample_item_id)

        if sample_file_id:
            stmt = stmt.filter(Sample.sample_file_id == sample_file_id)

        if sample_batch_id:
            stmt = stmt.filter(Sample.sample_batch_id == sample_batch_id)

        if filename:
            stmt = stmt.filter(Sample.filename == filename)

        if instrument:
            stmt = stmt.filter(Sample.instrument == instrument)

        if sample_item_type:
            stmt = stmt.filter(Sample.sample_item_type.in_(sample_item_type))

        if datetime_min and datetime_max:
            stmt = stmt.where(
                and_(
                    cast(func.julianday(Sample.datetime_utc), Float)
                    >= func.julianday(datetime_min),
                    cast(func.julianday(Sample.datetime_utc), Float)
                    <= func.julianday(datetime_max),
                )
            )

        if polarity is not None:
            stmt = stmt.filter(Sample.polarity.in_(polarity))

        if match_category_min is not None:
            stmt = stmt.filter(MatchSample.match_category >= match_category_min)

        result = await session.execute(stmt)
        rows = result.all()

        data = []
        for row in rows:
            sample_data = {
                column.name: getattr(row.Sample, column.name)
                for column in Sample.__table__.columns
            }

            if row.MatchSample:
                match_data = {
                    column.name: getattr(row.MatchSample, column.name)
                    for column in MatchSample.__table__.columns
                }
                # Add alarming as extra field (not part of MatchSample model)
                match_data["alarming"] = (
                    row.alarming if row.alarming is not None else False
                )
            else:
                match_data = {
                    "match_sample_id": None,
                    "sample_item_id": row.Sample.sample_item_id,
                    "match_score": None,
                    "match_category": None,
                    "sample_peak_intensity_sum": None,
                    "match_sample_utc_created": None,
                    "match_sample_utc_modified": None,
                    "alarming": False,
                }

            sample_data["match"] = match_data
            data.append(sample_data)

        return {
            "status": "success",
            "message": f"{len(data)} samples retrieved successfully",
            "results": len(data),
            "data": data,
        }


@api_controller()
async def get_sample(
    sample_item_id: str,
) -> dict:
    """
    Retrieves detailed information for a specific sample with nested match data and alarming status.

    :param sample_item_id: Unique identifier for the sample.
    :type sample_item_id: str
    :return: A dictionary containing detailed sample information, match data (if available), and match collection types (if available).
    :rtype: dict
    :raises NotFoundException: If the sample with the specified item ID is not found.
    """
    async with async_session() as session:
        # Verify sample exists
        if not (sample := await session.get(Sample, sample_item_id)):
            raise NotFoundException(f"Sample with ID '{sample_item_id}' not found")

        stmt = (
            select(
                Sample,
                MatchSample,
                # max to check if ANY collection is alarming
                func.max(
                    TargetCollection.target_collection_type.in_(
                        target_collection_config.APP_ALARMING_COLLECTION_TYPES
                    ).cast(Integer)
                ).label("alarming"),
            )
            .outerjoin(MatchSample, Sample.sample_item_id == MatchSample.sample_item_id)
            .outerjoin(
                MatchCollection,
                MatchCollection.sample_item_id == Sample.sample_item_id,
            )
            .outerjoin(
                TargetCollection,
                TargetCollection.target_collection_id
                == MatchCollection.target_collection_id,
            )
            .where(Sample.sample_item_id == sample_item_id)
            .group_by(Sample.sample_item_id, MatchSample.sample_item_id)
        )

        result = await session.execute(stmt)

    row = result.first()

    sample_data = {
        column.name: getattr(row.Sample, column.name)
        for column in Sample.__table__.columns
    }
    if row.MatchSample:
        match_data = {
            column.name: getattr(row.MatchSample, column.name)
            for column in MatchSample.__table__.columns
        }
        # Convert aggregated 1/0 to boolean
        match_data["alarming"] = (
            bool(row.alarming) if row.alarming is not None else False
        )
    else:
        match_data = {
            "match_sample_id": None,
            "sample_item_id": row.Sample.sample_item_id,
            "match_score": None,
            "match_category": None,
            "sample_peak_intensity_sum": None,
            "match_sample_utc_created": None,
            "match_sample_utc_modified": None,
            "alarming": False,
        }

    sample_data["match"] = match_data

    return {
        "status": "success",
        "message": f"Sample '{sample.sample_item_name}' retrieved successfully",
        "data": sample_data,
    }


@api_controller()
async def get_sample_peaks(
    sample_item_id: str,
    areas: bool = True,
    heights: bool = True,
    average: bool = True,
    t_min: float | None = None,
    t_max: float | None = None,
    mz_min: float | None = None,
    mz_max: float | None = None,
) -> dict:
    """
    Retrieve peak data from a sample.
    Retrieve peak data from a sample with automatic sample's polarity filtering and optional time and m/z range filtering.

    This controller extracts peak areas and/or heights for a sample, automatically filtered
    by the sample's polarity. It supports optional time range filtering within the sample's
    acquisition window (t0/t1) and m/z range filtering

    Steps:
    1. Get sample data and extract polarity/time metadata
    2. Validate and set effective time limits with auto-correction
    3. Get polarity-filtered scan timestamps for the specified time range
    4. Load peak data from the sample file
    5. Apply time filtering using polarity-specific timestamps
    6. Apply m/z range filtering if specified
    7. Aggregate peak data across the filtered time dimension
    8. Return formatted peak data

    :param sample_item_id: Unique identifier for the sample
    :type sample_item_id: str
    :param areas: If True, include peak areas in the response
    :type areas: bool
    :param heights: If True, include peak heights in the response
    :type heights: bool
    :param average: If True, return averaged peak data; if False, return summed peak data
    :type average: bool
    :param t_min: Minimum time limit in seconds, defaults to sample's t0 if not provided
    :type t_min: float | None
    :param t_max: Maximum time limit in seconds, defaults to sample's t1 if not provided
    :type t_max: float | None
    :param mz_min: Start of the optional m/z range, defaults to None
    :type mz_min: float | None
    :param mz_max: End of the optional m/z range, defaults to None
    :type mz_max: float | None
    :raises ValueError: If time limits are invalid or m/z range is invalid
    :raises NotFoundException: If sample or sample file is not found or hasn't been processed
    :return: Dictionary containing filtered peak data with m/z values and areas/heights
    :rtype: dict
    """

    # Step 1: Get sample data and extract required fields
    sample = await _load_sample_data(sample_item_id)

    # Step 2: Validate and set effective time limits with auto-correction
    t_min_eff, t_max_eff, time_adjustment_info = _validate_time_range(
        t_min, t_max, sample.t0, sample.t1
    )

    # Step 3: Get filtered scan timestamps using sample's polarity and time range
    time_array = m_compute.get_scan_timestamps(
        base_filename=sample.filename,
        t_min=t_min_eff,
        t_max=t_max_eff,
        polarity=sample.polarity,
    )

    if len(time_array) == 0:
        return {
            "message": f"No scans found for sample '{sample.sample_item_name}' with polarity '{sample.polarity}' in time range [{t_min_eff:.2f}s, {t_max_eff:.2f}s].",
            "results": 0,
            "data": {
                "mz": [],
                "area": [] if areas else None,
                "height": [] if heights else None,
            },
        }

    # Step 4: Load appropriate sample file peak data based on the query params
    vars_to_load = []
    if areas:
        vars_to_load.append("peak_areas")
    if heights:
        vars_to_load.append("peak_heights")

    try:
        sample_file_data = load_file(sample.filename, vars=vars_to_load)
    except FileNotFoundError as e:
        raise NotFoundException(
            f"Sample file with name '{sample.filename}' was not found or has not been processed"
        ) from e

    # Step 5: Extract and format the data with polarity filtering
    response_data = {}

    if areas:
        if "peak_areas" not in sample_file_data:
            raise NotFoundException(
                f"No peak areas found in sample file '{sample.filename}', file may not have been processed"
            )

        peak_areas = get_peaks(sample_file_data, "area")

        # Filter by polarity-specific scan timestamps
        peak_areas = peak_areas.sel(time=time_array, method="nearest")

        # Step 6: Apply m/z range filtering if specified
        if mz_min is not None and mz_max is not None:
            peak_areas = peak_areas.sel(mz=slice(mz_min, mz_max))

        # Step 7: Aggregate over filtered time dimension
        peak_areas = (
            peak_areas.mean(dim="time") if average else peak_areas.sum(dim="time")
        )
        response_data["mz"] = peak_areas.mz.values.tolist()
        response_data["area"] = peak_areas.values.tolist()

    if heights:
        if "peak_heights" not in sample_file_data:
            raise NotFoundException(
                f"No peak heights found in sample file '{sample.filename}', file may not have been processed"
            )
        peak_heights = get_peaks(sample_file_data, "height")

        # Filter by polarity-specific scan timestamps
        peak_heights = peak_heights.sel(time=time_array, method="nearest")

        # Step 6: Apply m/z range filtering if specified
        if mz_min is not None and mz_max is not None:
            peak_heights = peak_heights.sel(mz=slice(mz_min, mz_max))

        # Step 7: Aggregate over filtered time dimension
        peak_heights = (
            peak_heights.mean(dim="time") if average else peak_heights.sum(dim="time")
        )

        # If 'mz' was not populated from areas, populate it from heights
        if "mz" not in response_data:
            response_data["mz"] = peak_heights.mz.values.tolist()
        response_data["height"] = peak_heights.values.tolist()

    # Step 8: Format the response for the case where no peaks were detected
    if not response_data.get("mz", []):
        message = (
            f"No peaks found in sample '{sample.sample_item_name}' with polarity '{sample.polarity}'. "
            f"The file was processed, but no peaks were detected in the target m/z range."
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

    # Step 7: Remove empty fields from the response
    if not areas:
        response_data.pop("area", None)
    if not heights:
        response_data.pop("height", None)

    # Step 8: Return success response
    message = f"Successfully loaded {len(response_data['mz'])} peaks from sample '{sample.sample_item_name}' with polarity '{sample.polarity}'"

    if time_adjustment_info:
        message += time_adjustment_info

    return {
        "message": message,
        "results": len(response_data["mz"]),
        "data": response_data,
    }


@api_controller()
async def get_sample_peak_timeseries(
    sample_item_id: str,
    peak_mz: float,
    peak_mz_tolerance_ppm: float,
    t_min: float | None = None,
    t_max: float | None = None,
) -> dict:
    """
    Get timeseries of a given peak in a specified sample.

    Returns the timeseries of the closest peak to a given m/z, filtered by the sample's
    polarity and time range, if found within given m/z tolerance.

    Steps:
    1. Get sample data and extract required fields.
    2. Validate and set time limits based on sample's t0/t1 values.
    3. Get filtered scan timestamps using the sample's polarity and time range.
    4. Load the sample file data and get peaks.
    5. Filter sample file peaks by the scan timestamps and select the nearest peak
        to the requested m/z within the specified tolerance.
    6. Validate m/z tolerance and return timeseries data of the selected peak.

    :param sample_item_id: Sample item ID
    :type sample_item_id: str
    :param peak_mz: m/z of the peak to get timeseries for
    :type peak_mz: float
    :param peak_mz_tolerance_ppm: Tolerance for m/z difference
        for the requested peak and the nearest one found from data
    :type peak_mz_tolerance_ppm: float
    :param t_min: Minimum time limit in seconds, must be within sample's acquisition time range
    :type t_min: float | None
    :param t_max: Maximum time limit in seconds, must be within sample's acquisition time range
    :type t_max: float | None
    :raises HTTPException: Raised if sample is not found or time limits are invalid
    :return: Dictionary with keys:
        "mz": m/z of the peak in sample (None if no peak within tolerance)
        "height": peak height at time points (empty if no peak within tolerance)
        "time": time coordinates (empty if no peak within tolerance)
    :rtype: dict
    """
    # Step 1: Get sample data and extract required fields
    sample = await _load_sample_data(sample_item_id)

    # Step 2: Validate and set effective time limits with auto-correction
    t_min_eff, t_max_eff, time_adjustment_info = _validate_time_range(
        t_min, t_max, sample.t0, sample.t1
    )

    # Step 3: Get filtered scan timestamps using sample's polarity and time range (adjusted values)
    time_array = m_compute.get_scan_timestamps(
        base_filename=sample.filename,
        t_min=t_min_eff,
        t_max=t_max_eff,
        polarity=sample.polarity,
    )

    if len(time_array) == 0:
        return {
            "message": f"No scans found for sample '{sample.filename}' with polarity '{sample.polarity}' in time range [{t_min_eff}, {t_max_eff}] seconds.",
            "results": 0,
            "data": {
                "mz": None,
                "height": [],
                "time": [],
            },
        }

    # Step 4: Load sample file data
    try:
        sample_file = load_file(sample.filename, vars=["peak_heights"])
        peaks = get_peaks(sample_file, "height")
    except FileNotFoundError:
        raise NotFoundException(f"Sample file '{sample.filename}' not found")

    # Step 5: Filter sample file peaks to include times in filtered time_array and
    # select nearest to requested peak m/z
    peak_timeseries = peaks.sel(time=time_array, method="nearest").sel(
        mz=peak_mz, method="nearest"
    )

    # Step 6: Validate m/z tolerance and return timeseries data
    peak_mz_data = peak_timeseries.mz.item()

    # Calculate difference of the sample peak m/z to requested peak m/z
    mz_diff = peak_mz_data - peak_mz  # [Th]
    mz_diff_ppm = mz_diff / peak_mz * 1e6  # [ppm]

    # No peak found within given m/z tolerance
    if abs(mz_diff_ppm) > peak_mz_tolerance_ppm:
        message = (
            f"No peak found within given m/z tolerance {peak_mz_tolerance_ppm} ppm "
            f"of requested m/z {peak_mz} in sample '{sample.sample_item_name}' "
            f"with '{sample.polarity}' polarity."
        )
        return {
            "message": message,
            "results": 0,
            "data": {"mz": None, "height": [], "time": []},
        }

    message = (
        f"Retrieved timeseries with {len(peak_timeseries.time.values)} data points "
        f"for peak m/z {peak_mz} in sample '{sample.sample_item_name}' "
        f"with '{sample.polarity}' polarity."
    )
    if time_adjustment_info:
        message += time_adjustment_info

    return {
        "message": message,
        "results": len(peak_timeseries.time.values),
        "data": {
            "mz": peak_mz_data,
            "height": peak_timeseries.values.tolist(),
            "time": peak_timeseries.time.values.tolist(),
        },
    }


@api_controller()
async def get_sample_spectrum(
    sample_item_id: str,
    t_min: float | None = None,
    t_max: float | None = None,
    mz_min: float | None = None,
    mz_max: float | None = None,
) -> dict:
    """
    Retrieves the spectrum data from a sample.

    This endpoint extracts averaged spectrum data for a sample, automatically filtered
    by the sample's polarity and optional time and/or m/z ranges.

    Steps:
    1. Get sample data and extract required fields (t0, t1, polarity).
    2. Set effective time limits with validation and auto-correction.
    3. Compute averaged spectrum in the time range with polarity filtering.
    4. Filter by m/z range if provided.
    5. Extract m/z values and their corresponding intensities from the spectrum.
    6. Return the spectrum data, including the total number of m/z points and optional metadata.

    :param sample_item_id: Unique identifier for the sample from which to retrieve the spectrum
    :type sample_item_id: str
    :param t_min: Minimum time limit in seconds, defaults to sample's t0 if not provided
    :type t_min: float | None
    :param t_max: Maximum time limit in seconds, defaults to sample's t1 if not provided
    :type t_max: float | None
    :param mz_min: Start of the optional m/z range, defaults to None
    :type mz_min: float | None
    :param mz_max: End of the optional m/z range, defaults to None
    :type mz_max: float | None
    :return: A dictionary containing spectrum data with m/z values, intensities, and metadata
    :rtype: dict
    """
    # Step 1: Get sample data
    sample = await _load_sample_data(sample_item_id)

    # Step 2: Validate and set effective time limits with auto-correction
    t_min_eff, t_max_eff, time_adjustment_info = _validate_time_range(
        t_min, t_max, sample.t0, sample.t1
    )

    # Step 3: Compute averaged spectrum in the time range with polarity filtering
    intensity_unit = "counts/s"

    # Use specific time range with polarity filtering
    spectrum = m_compute.get_sum_signal(
        sample.filename, t_min_eff, t_max_eff, polarity=sample.polarity, average=True
    )

    # Check if spectrum computation returned None (no data found)
    if spectrum is None:
        message = (
            f"No spectrum data found for sample '{sample.sample_item_name}' "
            f"with '{sample.polarity}' polarity in time range "
            f"[{t_min_eff:.2f}s, {t_max_eff:.2f}s]. The sample file may not "
            f"contain scans of this polarity in the specified time window."
        )
        return {
            "message": message,
            "results": 0,
            "data": {
                "mz": [],
                "intensity": [],
                "intensity_unit": intensity_unit,
            },
        }

    # Step 4: Filter by m/z range if provided
    if mz_min is not None and mz_max is not None:
        spectrum = spectrum.sel(mz=slice(mz_min, mz_max)).compute()

    # Step 5: Extract m/z values and intensities
    mz_values = spectrum.mz.values.tolist()
    intensity_values = spectrum.values.tolist()

    # Step 6: Return the spectrum data with metadata
    message = f"Retrieved spectrum data with {len(mz_values)} m/z points from sample '{sample.sample_item_name}' with '{sample.polarity}' polarity."

    if time_adjustment_info:
        message += time_adjustment_info

    return {
        "message": message,
        "results": len(mz_values),
        "data": {
            "mz": mz_values,
            "intensity": intensity_values,
            "intensity_unit": intensity_unit,
        },
    }


@api_controller()
async def get_samples_centroids(
    sample_item_ids: list[str],
    independent_transaction: bool = False,
    sid=None,
    process_id=None,
    parent_id=None,
) -> dict:
    """Extracts centroids for a list of sample items by their IDs.

    :param sample_item_ids: List of sample item IDs for which to extract centroids.
    :type sample_item_ids: list[str]
    :param independent_transaction: Flag to indicate if the operation should be treated as an independent transaction, defaults to False.
    :type independent_transaction: bool, optional
    :param sid: Session ID for targeting specific clients when emitting events, defaults to None.
    :type sid: optional
    :param process_id: Process identifier for tracking background operations, defaults to None.
    :type process_id: optional
    :param parent_id: Parent process identifier for tracking background operations, defaults to None.
    :type parent_id: optional
    :return: A dictionary containing the extracted centroids for each sample item ID.
    :rtype: dict
    """
    if not sample_item_ids:
        return {
            "message": "No sample items provided for centroid extraction.",
            "data": [],
        }

    runtime.logger.info(
        f"Extracting centroids for {len(sample_item_ids)} sample items: {sample_item_ids}"
    )

    # Step 1: Fetch sample items from the database in one go
    async with async_session() as session:
        stmt = select(Sample)
        stmt = stmt.where(Sample.sample_item_id.in_(sample_item_ids))
        result = await session.execute(stmt)
        sample_items = result.scalars().all()

    # Step 2: Extract centroids for each sample item
    centroids = dict()
    for sample in sample_items:
        sample_item_centroids = m_compute.get_orbi_centroids_per_scan(
            base_filename=sample.filename,
            t_min=sample.t0,
            t_max=sample.t1,
            polarity=sample.polarity,
        )
        mzs = [cen["masses"].tolist() for cen in sample_item_centroids]
        intensities = [cen["intensities"].tolist() for cen in sample_item_centroids]
        resolutions = [cen["resolutions"].tolist() for cen in sample_item_centroids]
        signal_to_noise = [
            cen["signal_to_noise"].tolist() for cen in sample_item_centroids
        ]
        timestamps = [cen["timestamp"] for cen in sample_item_centroids]

        centroids[sample.sample_item_id] = {
            "masses": mzs,
            "intensities": intensities,
            "resolutions": resolutions,
            "signal_to_noise": signal_to_noise,
            "timestamp": timestamps,
        }

    # Step 3: Return the extracted centroids
    return {
        "message": f"Extracted centroids for {len(sample_item_ids)} sample items.",
        "data": centroids,
    }


@api_controller()
async def get_samples_spectra(
    sample_item_ids: list[str],
    t_min: float | None = None,
    t_max: float | None = None,
    mz_min: float | None = None,
    mz_max: float | None = None,
) -> dict:
    """Retrieves the spectrum data from several sample items

    :param sample_item_ids: List of unique identifiers for the sample items from which to retrieve the spectra
    :type sample_item_ids: list[str]
    :param t_min: Minimum time limit in seconds, defaults to None
    :type t_min: float | None, optional
    :param t_max: Maximum time limit in seconds, defaults to None
    :type t_max: float | None, optional
    :param mz_min: Start of the optional m/z range, defaults to None
    :type mz_min: float | None, optional
    :param mz_max: End of the optional m/z range, defaults to None
    :type mz_max: float | None, optional
    :raises ValueError: If no sample_item_ids are provided or if more than 100 sample_item_ids are provided
    :raises ValueError: If the time limits are invalid or if the m/z range is invalid
    :return: A dictionary containing the spectra data for each sample item, including m/z values and intensities.
    :rtype: dict
    """
    if not sample_item_ids:
        raise ValueError("At least one sample_item_id must be provided")

    if len(sample_item_ids) > 100:
        raise ValueError("Cannot retrieve spectra for more than 100 samples at once")

    # Load all sample data in parallel
    sample_data_list = await asyncio.gather(
        *[_load_sample_data(sample_id) for sample_id in sample_item_ids]
    )

    # Prepare the response data
    spectra_data = []
    for sample in sample_data_list:
        spectrum_response = await get_sample_spectrum(
            sample.sample_item_id, t_min, t_max, mz_min, mz_max
        )
        spectra_data.append(spectrum_response["data"])

    return {
        "message": "Spectra retrieved successfully.",
        "results": len(spectra_data),
        "data": spectra_data,
    }


@dataclass
class SampleData:
    """
    Data class to hold sample information.
    """

    sample_item_id: str
    sample_item_name: str
    filename: str
    t0: float
    t1: float
    polarity: str


async def _load_sample_data(sample_item_id: str) -> SampleData:
    """Load sample data from the database by sample item ID.

    :param sample_item_id: Unique identifier for the sample item
    :type sample_item_id: str
    :return: SampleData object containing sample information
    :rtype: SampleData
    """
    sample = await get_sample(sample_item_id)
    sample = sample["data"]
    sample_data = SampleData(
        sample_item_id=sample["sample_item_id"],
        sample_item_name=sample["sample_item_name"],
        filename=sample["filename"],
        t0=sample["t0"],
        t1=sample["t1"],
        polarity=sample["polarity"],
    )
    return sample_data


def _validate_time_range(
    t_min: float | None, t_max: float | None, sample_t0: float, sample_t1: float
) -> tuple[float, float, str]:
    """
    Validate and set effective time limits based on sample's acquisition window.

    :param t_min: Minimum time limit in seconds
    :type t_min: float | None
    :param t_max: Maximum time limit in seconds
    :type t_max: float | None
    :param sample_t0: Sample acquisition start time in seconds
    :type sample_t0: float
    :param sample_t1: Sample acquisition end time in seconds
    :type sample_t1: float
    :return: Tuple of effective minimum and maximum time limits
    :rtype: tuple[float, float, str]
    """
    t_min_eff = t_min if t_min is not None else sample_t0
    t_max_eff = t_max if t_max is not None else sample_t1

    # Check for completely invalid ranges (user provided values outside sample window)
    if t_min is not None and t_min > sample_t1:
        raise ValueError(
            f"Requested minimum time ({t_min:.2f}s) is after sample's acquisition end time ({sample_t1:.2f}s)"
        )
    if t_max is not None and t_max < sample_t0:
        raise ValueError(
            f"Requested maximum time ({t_max:.2f}s) is before sample's acquisition start time ({sample_t0:.2f}s)"
        )

    # Auto-correct slight overshoots and track what was adjusted
    adjustments = []
    if t_min is not None and t_min < sample_t0:
        t_min_eff = max(sample_t0, t_min_eff)
        adjustments.append(f"minimum time from {t_min:.2f}s to {sample_t0:.2f}s")
    if t_max is not None and t_max > sample_t1:
        t_max_eff = min(sample_t1, t_max_eff)
        adjustments.append(f"maximum time from {t_max:.2f}s to {sample_t1:.2f}s")

    # Build user message if adjustments were made
    time_adjustment_info = ""
    if adjustments:
        adjustment_text = " and ".join(adjustments)
        warning_msg = f"Time range adjusted: {adjustment_text} to fit sample acquisition window [{sample_t0:.2f}s, {sample_t1:.2f}s]"
        runtime.logger.warning(warning_msg)
        time_adjustment_info = f" {warning_msg}."
    else:
        time_adjustment_info = ""
    return t_min_eff, t_max_eff, time_adjustment_info
