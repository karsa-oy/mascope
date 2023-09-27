from hardware.tofwerk.calibration import mz_calibrate

from backend.db_api_rest import async_session
from backend.lib.signal import calculate_tic, signal_mz_calibration_update
from backend.socket_events import sio

from fastapi import BackgroundTasks, HTTPException
from sqlalchemy import select, func, and_

from .match_controller import match_item_remove
from .sample_files_controller import (
    update_sample_file,
    get_sample_files,
)
from .sample_items_controller import get_sample_items
from .match_controller import compute_matches


from ..models.pydantic_models.sample_file_pydantic_model import (
    SampleFileUpdate,
)
from ..models.pydantic_models.calibration_pydantic_model import CalibrationMzFitParams
from ..models.models import Sample, SampleBatch


async def get_mz_calibration(
    instrument: str = None,
    sample_item_id: str = None,
):
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


async def calibration_mz_apply(
    fit: dict, sample_filename: str, autosampler_mode: bool = None
):
    # Read affected sample items
    sample_items = await get_sample_items(filename=sample_filename)
    sample_item_ids = [item["sample_item_id"] for item in sample_items["data"]]

    for sample_item_id in sample_item_ids:
        await sio.emit(
            "calibration_mz_apply_started",
            {
                "action": "MZ Apply",
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

        # Delete outdated matches
        await match_item_remove(sample_item_id, True)

        await sio.emit(
            "calibration_mz_apply_finished",
            {
                "action": "MZ Apply",
                "sample_item_id": sample_item_id,
                "progress": 100,
                "autosampler_mode": autosampler_mode,
            },
            room=sample_item_id,
            namespace="/",
        )

    return sample_item_ids


async def emit_progress_update(progress_properties, increment):
    if not progress_properties:
        return

    sample_item_id = progress_properties.get("sample_item_id")
    progress_percentage = increment * 100

    await sio.emit(
        "calibration_mz_fit_progress",
        {
            "action": "MZ Fit",
            "progress_percentage": progress_percentage,
        },
        room=sample_item_id,
        namespace="/",
    )


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
    match_isotope_df = await compute_matches(
        filename, [calibration_collection_id], ionization_mechanism_ids
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

    if n_relevant_isotopes > 3 and len(good_matches_df) == n_relevant_isotopes:
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


async def calibration_mz_fit(
    sample_item_id: str,
    params: CalibrationMzFitParams,
    background_tasks: BackgroundTasks = None,
):
    await sio.emit(
        "calibration_mz_fit_started",
        {
            "action": "MZ Fit",
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
        sample = result.one()
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

    # get mz calibration parameters
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

        return {"message": "MZ Fit Calibration started"}
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
                "action": "MZ Fit",
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
                "action": "MZ Fit",
                "progress_percentage": 100,
                "fit": fit,
                "stats": stats,
                "error": error,
            },
            room=sample_item_id,
        )


async def calibration_mz_calibrate_sample(
    sample_item,
    params: CalibrationMzFitParams,
    background_tasks,
):
    filename = sample_item.get("filename")
    if not filename:
        raise ValueError(f"Invalid sample item: {sample_item}")

    async with async_session() as session:
        result = await session.execute(
            select(Sample.instrument).where(Sample.filename == filename).distinct()
        )
        instrument = result.one_or_none()

    await sio.emit(
        "calibration_mz_calibrate_sample_started",
        {
            "filename": filename,
            "progress": 0,
        },
        room=sample_item["sample_item_id"],
        namespace="/",
    )
    await sio.emit(
        "calibration_mz_calibrate_sample_progress",
        {},
        room=sample_item["sample_item_id"],
        namespace="/",
    )

    background_tasks.add_task(
        mz_calibrate_sample,
        sample_item,
        params,
        filename,
    )

    return {"message": "MZ sample calibration started, please wait for completion"}


async def mz_calibrate_sample(
    sample_item,
    params,
    filename,
    autosampler_mode: bool = None,
):
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
            f"Calibration MZ Fit finished successfully. Sample - {sample_item['sample_item_name']}, filename - {sample_item['filename']}"
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
            f"Calibration MZ calibrate sample finished successfully. Sample - {sample_item['sample_item_name']}, filename - {sample_item['filename']}"
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
            f"Calibration MZ Fit failed: {error}. Sample - {sample_item['sample_item_name']}, filename - {sample_item['filename']}"
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
            f"Calibration MZ calibrate sample failed: {error}. Sample - {sample_item['sample_item_name']}, filename - {sample_item['filename']}"
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


async def calibration_mz_calibrate_batch(
    sample_batch, sample_items, params: CalibrationMzFitParams
):
    calibration_results = []
    sample_batch_id = sample_batch.get("sample_batch_id")

    await sio.emit(
        "calibration_mz_calibrate_batch_started",
        {
            "action": "Auto Sampler",
            "sample_batch_id": sample_batch_id,
            "progress": 0,
        },
        room=sample_batch_id,
        namespace="/",
    )

    try:
        for index, sample_item in enumerate(sample_items):
            filename = sample_item.get("filename")
            if not filename:
                raise ValueError(f"Invalid sample item: {sample_item}")

            result = await mz_calibrate_sample(
                sample_item,
                params,
                filename,
                autosampler_mode=True,
            )
            result["index"] = index
            calibration_results.append(result)

        await sio.emit(
            "calibration_mz_calibrate_batch_finished",
            {
                "action": "Auto Sampler",
                "sample_batch_id": sample_batch_id,
                "progress": 100,
                "calibration_results": calibration_results,
            },
            room=sample_batch_id,
            namespace="/",
        )
    except Exception as e:
        print("Failed to calibrate batch %s" % sample_batch["sample_batch_name"])
        print(e)

        await sio.emit(
            "calibration_mz_calibrate_batch_failed",
            {
                "action": "Auto Sampler",
                "sample_batch_id": sample_batch_id,
                "progress": 100,
                "calibration_results": calibration_results,
                "error": e,
            },
            room=sample_batch["sample_batch_id"],
            namespace="/",
        )

    return calibration_results
