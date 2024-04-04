"""
Calibration Controller
-----------------------

This module contains all the functionalities related to the calibration processes. It provides endpoints and
background tasks to process calibration and related operations.

"""

# -------------------------------------------------------------------
# Imports
# -------------------------------------------------------------------
import numpy as np
import pandas as pd

from hardware.tofwerk.calibration import mz_calibrate
from hardware.tofwerk.lib.TwTool import TwTof2Mass

from backend.db import async_session
from backend.api_sio import sio

from lib.file_func import (
    get_zarr_var_shape,
    load_coord,
    update_props,
    update_zarr_array_coord,
)
from lib.peak import calculate_tic

from zarr.errors import PathNotFoundError

from fastapi import BackgroundTasks, HTTPException
from sqlalchemy import select, func, and_

from ..exceptions import process_exception, ApiException, NotFoundException
from .match_controller import match_sample_remove, compute_matches
from .sample_files_controller import (
    update_sample_file,
    get_sample_files,
)
from .sample_items_controller import get_sample_items
from .target_isotopes_controller import get_target_isotopes
from .target_compound_in_target_collection_controller import (
    get_target_compound_in_target_collection,
)


from ..models.pydantic_models.sample_file_pydantic_model import (
    SampleFileUpdate,
)
from ..models.pydantic_models.calibration_pydantic_model import CalibrationMzFitParams
from ..models.models import Sample, SampleBatch


# -------------------------------------------------------------------
# Utility Functions
# -------------------------------------------------------------------
async def emit_progress_update(progress_properties, increment):
    """
    Emit progress updates to the given sample item room.

    :param progress_properties: Dictionary containing information about the current item being processed.
    :param increment: Float representing the progress percentage increment.
    """

    if not progress_properties:
        return

    sample_item_id = progress_properties.get("sample_item_id")
    progress_percentage = increment * 100

    await sio.emit(
        "calibration_mz_fit_progress",
        {
            "action": "m/z Fit",
            "progress_percentage": progress_percentage,
        },
        room=sample_item_id,
        namespace="/",
    )


# -------------------------------------------------------------------
# Main Logic Functions
# -------------------------------------------------------------------


async def mz_fit(
    filename,
    calibration_collection_id,
    ionization_mechanism_ids,
    peak_intensity_min,
    isotope_abundance_min,
    match_score_min,
    refine_window,
    sample_item_id,
):
    """
    Main function to fit m/z. Fits the mass-to-charge ratio (m/z) for a given sample file.

    :param ...:  parameters.
    :return: fit, stats, error.
    """

    fit = None
    stats = None
    error = None
    progress_properties = {"sample_item_id": sample_item_id}

    # calculate tic
    await emit_progress_update(progress_properties, 0.25)

    tic = calculate_tic(filename)
    if tic < 1e6:
        error = "TIC is too low! Check ionization device."
        return fit, stats, error

    await emit_progress_update(progress_properties, 0.35)

    # Compute matches for calibration compounds
    # Fetch target compounds in the calibration collection
    target_compounds_result = await get_target_compound_in_target_collection(
        target_collection_id=calibration_collection_id,
    )
    target_compound_ids = [
        item["target_compound_id"] for item in target_compounds_result["data"]
    ]

    # Fetch target isotopes for specific filters
    target_isotopes_result = await get_target_isotopes(
        target_compound_ids=target_compound_ids,
        ionization_mechanism_ids=ionization_mechanism_ids,
    )
    target_isotopes_df = pd.DataFrame(target_isotopes_result["data"])
    match_isotope_df = await compute_matches(
        filename, target_isotopes_df, min_isotope_abundance=isotope_abundance_min
    )

    # Filter matches
    good_matches_df = match_isotope_df[
        (match_isotope_df.relative_abundance >= isotope_abundance_min)
        & (match_isotope_df.sample_peak_area >= peak_intensity_min)
        & (abs(match_isotope_df.match_mz_error) <= refine_window)
        & (match_isotope_df.match_score >= match_score_min)
    ]
    n_relevant_isotopes = len(
        match_isotope_df[(match_isotope_df.relative_abundance >= isotope_abundance_min)]
    )
    calibrant_signal_intensity = good_matches_df["sample_peak_area"]
    calibrant_to_tic = calibrant_signal_intensity / tic
    await emit_progress_update(progress_properties, 0.75)

    if (
        n_relevant_isotopes > 3
        and len(good_matches_df) > 3
        and (n_relevant_isotopes - len(good_matches_df) <= 2)
    ):
        # Fit mz calibration
        fit, stats = mz_calibrate(
            good_matches_df["sample_peak_tof"],
            good_matches_df["sample_peak_mz"],
            good_matches_df["mz"],
        )
        calibration_df = good_matches_df.copy().assign(
            calibration_mz=stats["new_mz"],
            calibration_mz_error=stats["post_dmz"],
            mz_error_diff=abs(stats["post_dmz"]) - abs(stats["pre_dmz"]),
            calibrant_to_tic=calibrant_to_tic,
        )
        mz_error_tolerance = 10
        calibration_inaccurate = (
            abs(calibration_df["calibration_mz_error"]) > mz_error_tolerance
        ).any()
        if calibration_inaccurate:
            error = "Calibration inaccurate"
        stats = calibration_df.to_dict("records")
        summary_row = {
            "match_mz_error": abs(calibration_df["match_mz_error"]).mean(),
            "calibration_mz_error": abs(calibration_df["calibration_mz_error"]).mean(),
            "mz_error_diff": sum(calibration_df["mz_error_diff"]),
            "calibrant_to_tic": sum(calibration_df["calibrant_to_tic"]),
        }
        stats.append(summary_row)

        await emit_progress_update(progress_properties, 1)
    else:
        # Not enough calibration peaks
        fit = None
        stats = good_matches_df.to_dict("records")
        error = "Not enough calibration peaks"

    return fit, stats, error


async def mz_calibrate_sample(
    sample_item,
    params,
    filename,
    autosampler_mode: bool = None,
):
    """
    Calibrates a single sample. It first fits the sample and then applies the calibration.
    Notifications are sent based on the progress using socket IO.

    :param sample_item: The sample item to calibrate.
    :param params: Calibration parameters defined by the CalibrationMzFitParams pydantic model.
    :param filename: Name of the file corresponding to the sample item.
    :param autosampler_mode: Indicates whether the calibration is in autosampler mode or not.
    :return: The calibration result for the given sample.
    """
    print(f"...m/z calibrating sample: {sample_item['sample_item_name']} ...")

    # Initializing the result dictionary.
    result = {
        "status": "",
        "index": "",
        "sample_item_name": sample_item["sample_item_name"],
        "filename": sample_item["filename"],
        "error": "",
    }

    fit, stats, error = await calibration_mz_fit(
        sample_item["sample_item_id"],
        params,
    )

    if fit:
        print(
            f"Calibration m/z Fit finished successfully. Sample - {sample_item['sample_item_name']}, filename - {sample_item['filename']}"
        )
        await sio.emit(
            "calibration_mz_fit_finished",
            {
                "fit": fit,
                "stats": stats,
                "error": error,
            },
            room=sample_item["sample_item_id"],
        )

        await calibration_mz_apply(fit, sample_item["filename"], autosampler_mode)

        print(
            f"Calibration m/z calibrate sample finished successfully. Sample - {sample_item['sample_item_name']}, filename - {sample_item['filename']}"
        )
        await sio.emit(
            "calibration_mz_calibrate_sample_finished",
            {
                "filename": filename,
                "progress": 100,
            },
            room=sample_item["sample_item_id"],
            namespace="/",
        )
        result["status"] = "calibrated"
    else:
        print(
            f"Calibration m/z Fit failed: {error}. Sample - {sample_item['sample_item_name']}, filename - {sample_item['filename']}"
        )
        await sio.emit(
            "calibration_mz_fit_failed",
            {
                "fit": fit,
                "stats": stats,
                "error": error,
            },
            room=sample_item["sample_item_id"],
        )
        print(
            f"Calibration m/z calibrate sample failed: {error}. Sample - {sample_item['sample_item_name']}, filename - {sample_item['filename']}"
        )
        await sio.emit(
            "calibration_mz_calibrate_sample_failed",
            {
                "filename": filename,
                "progress": 100,
                "error": error,
            },
            room=sample_item["sample_item_id"],
            namespace="/",
        )

        result["status"] = "calibration failed"
        result["error"] = error

    return result


def remove_duplicate_mz_values(mz):
    # Sometimes TOF signal mz coordinate contains multiple zeros at the beginning
    # This may cause duplicate coordinate value error in some functions
    # This function fixes the coordinate vector by setting arbitrary small values for
    # the zero coordinates
    mz_unique = mz
    mz_below_10_mask = mz < 10
    if (np.diff(mz[mz_below_10_mask]) == 0).any():
        mz_below_10_maxi = mz_below_10_mask.sum()
        mz_unique[mz_below_10_mask] = np.linspace(
            0, mz[mz_below_10_maxi], mz_below_10_maxi, endpoint=False
        )
    return mz_unique


def signal_mz_calibration_update(fit, filename):
    mode = fit["mode"]
    par = fit["par"]
    # Calculate new mz axis
    nbr_samples = get_zarr_var_shape(filename, "signal")[0]
    par = np.array(par, dtype=np.double)
    new_mz = np.array([TwTof2Mass(tof, mode, par) for tof in range(nbr_samples)])
    new_mz = remove_duplicate_mz_values(new_mz)
    new_range = [new_mz[0], new_mz[-1]]

    # Update zarr file coordinates and props
    print("Calibrating file: %s" % filename)
    if nbr_samples != get_zarr_var_shape(filename, "signal")[0]:
        raise Exception("Number of TOF samples does not match")
    update_props(filename, {"range": new_range, "mz_calibration": fit})
    # Write new mz coordinates to zarr file
    update_zarr_array_coord(filename, "signal", "mz", new_mz)
    try:
        update_zarr_array_coord(filename, "sum_signal", "mz", new_mz)
    except PathNotFoundError:
        pass
    try:
        peak_tofs = load_coord(filename, "peak_areas", "tof")
        new_peak_mzs = new_mz[peak_tofs.astype(int)]
        update_zarr_array_coord(filename, "peak_areas", "mz", new_peak_mzs)
        update_zarr_array_coord(filename, "peak_heights", "mz", new_peak_mzs)
    except PathNotFoundError:
        pass
    return new_mz


# -------------------------------------------------------------------
# Background Tasks
# -------------------------------------------------------------------


async def background_mz_fit(
    filename,
    calibration_collection_id,
    ionization_mechanism_ids,
    peak_intensity_min,
    isotope_abundance_min,
    match_score_min,
    refine_window,
    sample_item_id,
):
    """
    Run mz_fit as a background task asynchronously.

    :param ...: parameters.
    """
    fit, stats, error = await mz_fit(
        filename,
        calibration_collection_id,
        ionization_mechanism_ids,
        peak_intensity_min,
        isotope_abundance_min,
        match_score_min,
        refine_window,
        sample_item_id,
    )

    if fit:
        await sio.emit(
            "calibration_mz_fit_finished",
            {
                "action": "m/z Fit",
                "progress_percentage": 100,
                "fit": fit,
                "stats": stats,
                "error": error,
            },
            room=sample_item_id,
        )
    else:
        await sio.emit(
            "calibration_mz_fit_failed",
            {
                "action": "m/z Fit",
                "progress_percentage": 100,
                "fit": fit,
                "stats": stats,
                "error": error,
            },
            room=sample_item_id,
        )


# -------------------------------------------------------------------
# Controller or Route Handlers
# -------------------------------------------------------------------


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

        return mz_calibration


async def calibration_mz_fit(
    sample_item_id: str,
    params: CalibrationMzFitParams,
    background_tasks: BackgroundTasks = None,
):
    """
    Start m/z fit calibration for a given sample item based on the calibration parameters. It also manages
    background tasks and communicates the progress using socket IO.

    :param sample_item_id: ID of the sample item.
    :param params: Calibration parameters.
    :param background_tasks: Optional background task parameter.
    :return: Status message if called from route endpoint or fit, stats, error if called during automatica sample calibration from the mz_calibrate_sample.
    """
    await sio.emit(
        "calibration_mz_fit_started",
        {
            "action": "m/z Fit",
            "progress_percentage": 0,
        },
        room=sample_item_id,
        namespace="/",
    )

    async with async_session() as session:
        result = await session.execute(
            select(Sample.filename, Sample.sample_batch_id).where(
                Sample.sample_item_id == sample_item_id
            )
        )
        sample = result.one_or_none()

        if not sample:
            # if called from the route function
            if background_tasks:
                raise HTTPException(
                    status_code=404,
                    detail=f"Sample with ID {sample_item_id} not found",
                )
            # if called from the mz_calibrate_sample
            else:
                raise ValueError(f"Sample with ID {sample_item_id} not found")

        filename, sample_batch_id = sample.filename, sample.sample_batch_id

    # unpack parameters
    peak_intensity_min = params.peak_intensity_min
    isotope_abundance_min = params.isotope_abundance_min
    match_score_min = params.match_score_min
    refine_window = params.refine_window

    async with async_session() as session:
        result = await session.execute(
            select(SampleBatch.build_params).where(
                SampleBatch.sample_batch_id == sample_batch_id
            )
        )
        sample_batch = result.one()

    # get m/z calibration parameters
    build_params = sample_batch.build_params
    calibration_collection_id = build_params["calibration_collection"]
    ionization_mechanism_ids = build_params["ion_mechanisms"]

    if background_tasks:
        background_tasks.add_task(
            background_mz_fit,
            filename,
            calibration_collection_id,
            ionization_mechanism_ids,
            peak_intensity_min,
            isotope_abundance_min,
            match_score_min,
            refine_window,
            sample_item_id,
        )

        return {"message": "m/z Fit Calibration started"}
    else:
        fit, stats, error = await mz_fit(
            filename,
            calibration_collection_id,
            ionization_mechanism_ids,
            peak_intensity_min,
            isotope_abundance_min,
            match_score_min,
            refine_window,
            sample_item_id,
        )
        return fit, stats, error


async def calibration_mz_apply(
    fit: dict, sample_filename: str, autosampler_mode: bool = None
):
    """
    Apply m/z calibration to a sample file.

    :param fit: Fit dictionary.
    :param sample_filename: Name of the sample file.
    :param autosampler_mode: Optional flag for autosampler mode. In the calibration.js store affects if the batch will be reloaded onCalibrationMzApplyFinished
    :return: List of calibrated sample item IDs.
    """

    # Read affected sample items
    sample_items = await get_sample_items(filename=sample_filename)
    sample_item_ids = [item["sample_item_id"] for item in sample_items["data"]]

    for sample_item_id in sample_item_ids:
        await sio.emit(
            "calibration_mz_apply_started",
            {
                "action": "m/z Apply",
                "sample_item_id": sample_item_id,
                "progress": 0,
            },
            room=sample_item_id,
            namespace="/",
        )

    # Retrieve the sample file directly using filename
    sample_file_data = await get_sample_files(filename=sample_filename)

    if not sample_file_data["data"]:
        raise HTTPException(
            status_code=404,
            detail=f"Sample file with filename {sample_filename} not found",
        )

    sample_file = sample_file_data["data"][0]

    # Update zarr files
    new_mz = signal_mz_calibration_update(fit, sample_file["filename"])
    new_range = [new_mz[0], new_mz[-1]]

    fit.update({"verified": True})

    # Update database record
    sample_file["mz_calibration"] = fit
    sample_file["range"] = new_range
    await update_sample_file(
        sample_file["sample_file_id"], SampleFileUpdate(**sample_file)
    )
    for sample_item_id in sample_item_ids:
        # FAQ_match removes mathces in all samples assosiated with filename
        #  TODO shoud we rematch the non active samples?

        # Delete outdated matches
        await match_sample_remove(sample_item_id)

        await sio.emit(
            "calibration_mz_apply_finished",
            {
                "action": "m/z Apply",
                "sample_item_id": sample_item_id,
                "progress": 100,
                "autosampler_mode": autosampler_mode,
            },
            room=sample_item_id,
            namespace="/",
        )

    return sample_item_ids


async def calibration_mz_calibrate_sample(
    sample_item_id: str,
    params: CalibrationMzFitParams,
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
    :param params: The calibration parameters to be used for the calibration process.
    :type params: CalibrationMzFitParams
    :raises NotFoundException: If the sample with the given ID is not found in the database.
    :raises ValueError: If the sample does not have a valid filename associated with it.
    :raises ApiException: For any exceptions that occur during the calibration process.
    """
    try:
        # Step 1: Fetch sample data
        async with async_session() as session:
            # Fetch samples
            result = await session.execute(
                select(Sample).filter(Sample.sample_item_id == sample_item_id)
            )

            sample = result.scalars().first()

        if not sample:
            raise NotFoundException(f"Sample with ID {sample_item_id} not found")

        filename = sample.filename
        if not filename:
            raise ValueError(f"Invalid sample item: {sample.sample_item_name}")

        # Step 2: Notify the start of calibration
        await sio.emit(
            "calibration_mz_calibrate_sample_started",
            {
                "filename": filename,
                "progress": 0,
            },
            room=sample_item_id,
            namespace="/",
        )

        await sio.emit(
            "calibration_mz_calibrate_sample_progress",
            {},
            room=sample_item_id,
            namespace="/",
        )

        # Step 3: Calibrate sample using specified parameters
        await mz_calibrate_sample(
            sample.to_dict(),
            params,
            filename,
        )
    except Exception as e:
        # TODO_error_handling construct some common backfround task fail notification
        # Emit an error message indicating calibration failure
        await sio.emit(
            "calibration_mz_calibrate_sample_failed",
            {
                "action": "m/z Calibrate Sample",
                "filename": filename,
                "error": str(e),
                "progress": 100,
                "sample_item_id": sample_item_id,
            },
            room=sample_item_id,
            namespace="/",
        )
        raise process_exception(
            e, f"Failed to m/z calibrate samples '{sample_item_id}'."
        )


async def calibration_mz_calibrate_batch(
    sample_batch_id: str,
    params: CalibrationMzFitParams,
    independent_transaction: bool = False,
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
    :param params: Calibration parameters to be used for the calibration process.
    :type params: CalibrationMzFitParams
    :param independent_transaction: Flag indicating if the operation is an independent transaction, default to False.
    :type independent_transaction: bool
    :raises NotFoundException: Raised if the sample batch or any samples within it are not found.
    :raises ApiException: Raised for any exceptions that occur during the calibration process.
    :return: A list of calibration results for each sample in the batch.
    :rtype: list
    """
    try:
        calibration_results = []

        # Step 1: Notify the start of calibration

        print(f"...m/z calibrating batch: {sample_batch_id} ...")
        await sio.emit(
            "calibration_mz_calibrate_batch_started",
            {
                "action": "m/z Calibrate Batch",
                "sample_batch_id": sample_batch_id,
                "progress": 0,
            },
            room=sample_batch_id,
            namespace="/",
        )

        # Step 2: Fetch all samples in the batch
        async with async_session() as session:
            # Fetch samples
            result = await session.execute(
                select(Sample).where(Sample.sample_batch_id == sample_batch_id)
            )

            samples = result.scalars().all()

        if not samples:
            raise NotFoundException(f"Sample batch has no samples")

        # Step 3: Calibrate each sample and collect results
        for index, sample in enumerate(samples):
            filename = sample.filename
            if not filename:
                raise ValueError(f"Invalid sample: {sample.sample_item_name}")

            # Calibrate sample using specified parameters
            result = await mz_calibrate_sample(
                sample.to_dict(),
                params,
                filename,
                autosampler_mode=True,
            )
            result["index"] = index
            calibration_results.append(result)

        # Step 4: Notify the completion of calibration
        await sio.emit(
            "calibration_mz_calibrate_batch_finished",
            {
                "action": "m/z Calibrate Batch",
                "sample_batch_id": sample_batch_id,
                "progress": 100,
                "calibration_results": calibration_results,
            },
            room=sample_batch_id,
            namespace="/",
        )
        # Step 5: Emit a reload event for the sample batch if this is an independent transaction.
        # Reload affected sample batch if called by http request
        if independent_transaction:
            await sio.emit("sample_batch_reload", room=sample_batch_id, namespace="/")
    except Exception as e:
        # Step 5: Handle exceptions and notify calibration failure
        error_message = f"Failed to m/z calibrate batch '{sample_batch_id}'. {str(e)}"

        await sio.emit(
            "calibration_mz_calibrate_batch_failed",
            {
                "action": "m/z Calibrate Batch",
                "sample_batch_id": sample_batch_id,
                "progress": 100,
                "calibration_results": calibration_results,
                "error": error_message,
            },
            room=sample_batch_id,
            namespace="/",
        )

        # reise the error if called internally, from import_sample_items
        if independent_transaction:
            print(error_message)
        else:
            raise process_exception(
                e, f"Failed to m/z calibrate batch '{sample_batch_id}'."
            )

    return calibration_results
