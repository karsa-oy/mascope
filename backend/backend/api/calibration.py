import asyncio
import json

import pandas as pd
from hardware.tofwerk.calibration import mz_calibrate

from backend.api.match import compute_matches
from backend.api.match import item_remove as match_item_remove
import importlib

from backend.api.signal import calculate_tic, signal_mz_calibration_update
from backend.db.conn import conn
from backend.server import sio

from ..api_rest.controllers.calibration_controller import calibration_mz_apply
from ..api_rest.models.pydantic_models.sample_batch_pydantic_model import (
    SampleBatchUpdate,
)

# TODO check the circular import error after creating match rest api
# from ..api_rest.controllers.sample_batches_controller import update_sample_batch


async def mz_calibrate_sample(sid, sample_item, params):
    fit, stats, error = await calibration_mz_fit(
        sid,
        sample_item["sample_item_id"],
        params,
    )
    if fit:
        await calibration_mz_apply(fit, [sample_item["filename"]])
    return fit, stats, error


async def mz_fit(
    filename,
    calibration_collection_id,
    ionization_mechanism_ids,
    peak_intensity_min,
    isotope_abundance_min,
    match_score_min,
    refine_window,
):
    fit = None
    stats = None
    error = None

    # calculate tic
    tic = calculate_tic(filename)
    if tic < 1e6:
        error = "TIC is too low! Check ionization device."
        return fit, stats, error
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
    else:
        # Not enough calibration peaks
        fit = None
        stats = good_matches_df.to_dict("records")
        error = "Not enough calibration peaks"
    return fit, stats, error


@sio.event(namespace="/")
async def calibration_mz_calibrate_batch(sid, sample_batch_id, filename):
    with conn:
        # Read sample batch
        sample_batch_df = pd.read_sql(
            """
            SELECT
                *
            FROM sample_batch
            WHERE sample_batch_id == ?
            """,
            conn,
            params=[sample_batch_id],
        )
        target_collection_ids = pd.read_sql(
            f"""--sql
            SELECT target_collection_id
            FROM target_collection_in_sample_batch
            WHERE sample_batch_id == ?
            """,
            conn,
            params=[sample_batch_id],
        )["target_collection_id"].tolist()
    sample_batch_df = sample_batch_df.assign(
        target_collection_id=[target_collection_ids]
    )
    sample_batch_df = sample_batch_df.assign(
        build_params=sample_batch_df[["build_params"]].applymap(
            lambda x: json.loads(x)
        ),
        filter_params=sample_batch_df[["filter_params"]].applymap(
            lambda x: json.loads(x)
        ),
    )
    build_params = sample_batch_df["build_params"].tolist()[0]
    calibration_collection_id = build_params["calibration_collection"]
    ionization_mechanism_ids = build_params["ion_mechanisms"]

    # Compute matches for calibration compounds
    match_isotope_df = compute_matches(
        filename, [calibration_collection_id], ionization_mechanism_ids
    )

    # Fit mz calibration
    fit, stats = mz_calibrate(
        match_isotope_df["sample_peak_tof"],
        match_isotope_df["sample_peak_mz"],
        match_isotope_df["mz"],
    )

    # TODO: Check calibration is ok

    # Apply to file
    await calibration_mz_apply(fit, [filename])

    # Update sample batch
    # sample_batch_df["calibration_sample_filename"] = filename
    # await sample_batch_update(sid, sample_batch_df.to_dict("records"))

    # TODO fix the circular import error
    sample_batches_controller = importlib.import_module(
        "..api_rest.controllers.sample_batches_controller", package="backend"
    )
    update_sample_batch = getattr(sample_batches_controller, "update_sample_batch")

    sample_batch_df["calibration_sample_filename"] = filename
    sample_batch_update_dict = sample_batch_df.to_dict("records")[0]

    sample_batch_update = SampleBatchUpdate(**sample_batch_update_dict)

    await update_sample_batch(sample_batch_id, sample_batch_update)


@sio.event(namespace="/")
async def calibration_mz_calibrate_sample(sid, sample_item, params):
    try:
        filename = sample_item["filename"]
    except KeyError:
        print("calibration_mz_calibrate_sample: Invalid sample item %s" % sample_item)
    [instrument] = pd.read_sql(
        f"""--sql
        SELECT instrument
        FROM sample_file
        WHERE filename = ?
        """,
        conn,
        params=[filename],
    )["instrument"].tolist()
    await sio.emit(
        "calibration_mz_calibrate_started",
        {
            "filename": filename,
            "progress": 0,
        },
        room=instrument,
        namespace="/",
    )
    await sio.emit(
        "calibration_mz_calibrate_progress", {}, room=instrument, namespace="/"
    )
    task = sio.start_background_task(mz_calibrate_sample, sid, sample_item, params)
    results = await asyncio.gather(task)
    fit, stats, error = results[0]
    if fit:
        await sio.emit(
            "calibration_mz_calibrate_finished",
            {
                "filename": filename,
                "progress": 100,
            },
            room=instrument,
            namespace="/",
        )
    else:
        await sio.emit(
            "calibration_mz_calibrate_failed",
            {
                "filename": filename,
                "progress": 100,
            },
            room=instrument,
            namespace="/",
        )


@sio.event(namespace="/")
async def calibration_mz_fit(
    sid,
    sample_item_id,
    params,
):
    with conn:
        [filename] = pd.read_sql(
            f"""
            SELECT filename
            FROM sample_item
            WHERE sample_item_id == ?
            """,
            conn,
            params=[sample_item_id],
        )["filename"].tolist()
        [sample_batch_id] = pd.read_sql(
            f"""
            SELECT sample_batch_id
            FROM sample_item
            WHERE sample_item_id == ?
            """,
            conn,
            params=[sample_item_id],
        )["sample_batch_id"].tolist()
    # unpack parameters
    peak_intensity_min = params.get("peak_intensity_min", 3000.0)
    isotope_abundance_min = params.get("isotope_abundance_min", 0.1)
    match_score_min = params.get("match_score_min", 0)
    refine_window = params.get("refine_window", 100)

    # read sample batch
    with conn:
        [sample_batch] = pd.read_sql(
            f"""
            SELECT build_params
            FROM sample_batch
            WHERE sample_batch_id == ?
            """,
            conn,
            params=[sample_batch_id],
        ).to_dict("records")
    # get mz calibration parameters
    build_params = json.loads(sample_batch["build_params"])
    calibration_collection_id = build_params["calibration_collection"]
    ionization_mechanism_ids = build_params["ion_mechanisms"]

    fit, stats, error = await mz_fit(
        filename,
        calibration_collection_id,
        ionization_mechanism_ids,
        peak_intensity_min,
        isotope_abundance_min,
        match_score_min,
        refine_window,
    )
    if sid:
        await sio.emit(
            "calibration_mz_fit_stats",
            {
                "fit": fit,
                "stats": stats,
                "error": error,
            },
            room=sid,
        )
    return fit, stats, error
