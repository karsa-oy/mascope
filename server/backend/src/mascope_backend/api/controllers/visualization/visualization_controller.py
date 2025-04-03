import asyncio
import numpy as np
import pandas as pd
from sqlalchemy import select
from colorcet import glasbey_hv as colormap

from mascope_file.io import load_file
from mascope_file.name import get_instrument_type

from mascope_signal.compute import get_sum_signal
from mascope_signal.peak import filter_peaks, get_peaks

from mascope_backend.db import async_session
from mascope_backend.db.models import Sample, TargetIsotope
from mascope_backend.socket import sio
from mascope_backend.api.lib.exceptions.api_exceptions import NotFoundException
from mascope_backend.api.lib.api_features import api_controller_background_task

from mascope_backend.runtime import runtime

# TODO_configuration shift traces color
COLOR_OFFSET = 5


@api_controller_background_task(
    error_notification_rooms=["sid"],
)
async def visualize_ion_focus(
    sample_item_id: str,
    target_ion_id: str,
    min_isotope_abundance: float,
    peak_min_intensity: float,
    mz_tolerance: int,
    independent_transaction: bool = False,
    sid: str = None,
    process_id: str = None,
):
    """
    Visualizes the focus on a specific ion for a given sample item by computing and emitting sum spectrum and time series data.

    The function performs the following steps:
    1. Fetches sample filename and target ion data from the database.
    2. Loads the sample file and prepares a data slice for analysis.
    3. Converts target ion data to a DataFrame and prepares m/z values, relative abundances, and target isotope IDs for processing.
    4. Iterates over each target isotope, computing and emitting visualization traces for the sum spectrum and time series.
    5. Constructs and emits the sum timeseries trace if applicable.

    :param sample_item_id: ID of the sample item to visualize.
    :type sample_item_id: str
    :param target_ion_id: ID of the target ion to focus on.
    :type target_ion_id: str
    :param min_isotope_abundance: Minimum relative abundance threshold for isotopes.
    :type min_isotope_abundance: float
    :param peak_min_intensity: Minimum peak intensity threshold for considering a match.
    :type peak_min_intensity: float
    :param mz_tolerance: Tolerance for mass-to-charge ratio (m/z) error, in parts per million (ppm).
    :type mz_tolerance: float
    :param independent_transaction: Indicates if the visualization should be considered an independent transaction, which affects sio event emission.
    :type independent_transaction: bool, optional
    :param sid: Session ID, used for targeting specific clients when emitting events.
    :type sid: str, optional
    :raises NotFoundException: If the sample item or target ion does not exist or does not meet the specified criteria.
    """
    # Step 1: Fetch sample filename and target ion data from the database
    async with async_session() as session:
        # Fetch sample filename
        stmt = select(Sample.filename).where(Sample.sample_item_id == sample_item_id)
        result = await session.execute(stmt)
        filename = result.scalar_one_or_none()
        if not filename:
            raise NotFoundException(f"Sample with ID {sample_item_id} not found")
        instrument_type = get_instrument_type(filename)
        isotope_resolution = "LOW" if instrument_type == "tof" else "HIGH"

        # Fetch target ion data
        stmt = select(TargetIsotope).where(
            TargetIsotope.target_ion_id == target_ion_id,
            TargetIsotope.relative_abundance >= min_isotope_abundance,
            TargetIsotope.resolution == isotope_resolution,
        )
        result = await session.execute(stmt)
        target_ion_data = result.scalars().all()
        if not target_ion_data:
            raise NotFoundException(
                f"Target ion with ID {target_ion_id} not found or does not meet abundance threshold"
            )
    # Set units and peak data type based on instrument type
    units = "counts/s"
    peak_profile_type = "area" if instrument_type == "tof" else "height"

    # Step 2: Load the sample file and prepare data slice
    runtime.logger.info(f"Loading file: {filename}")
    sample_file = load_file(filename, vars=["peak_areas", "peak_heights"])
    averaged_signal = get_sum_signal(filename, average=True)

    # Step 3: Convert target ion data to DataFrame and prepare data
    target_ion_list = [ion.to_dict() for ion in target_ion_data]
    target_ion_df = pd.DataFrame(target_ion_list)
    mzs = target_ion_df["mz"].tolist()
    rel_abus = target_ion_df["relative_abundance"].tolist()
    target_isotope_ids = target_ion_df["target_isotope_id"].tolist()

    # Step 4: Iterate over each target isotope to process visualization data
    # Initialize variables for sum timeseries trace
    main_isotope_i = 0
    main_isotope_height = 0
    sum_timeseries = None
    match_isotope_counter = 0
    for i, mz in enumerate(mzs):
        runtime.logger.info("{:d}/{:d}: {:3f}".format(i + 1, len(mzs), mz))
        spectrum_traces = []
        timeseries_traces = []
        dmz = 0.5
        mz_range = (mz - dmz, mz + dmz)
        rel_abu = rel_abus[i]
        current_target_isotope_id = target_isotope_ids[i]

        # Extract the specific isotope slice and compute the sum spectrum
        isotope_slice = sample_file.sel(mz=slice(*mz_range)).compute()
        isotope_averaged_spec = averaged_signal.sel(mz=slice(*mz_range)).compute()
        # Check if the spectrum slice is empty
        if isotope_averaged_spec.size == 0:
            # No signal in the requested range, plot 0-line still
            runtime.logger.warning(
                f"No data found in the mz range {mz_range} for requested mz {mz}"
            )
            averaged_spec_mz = np.array(list(mz_range), dtype=np.float32)
            averaged_spec_y = np.array([0, 0], dtype=np.float32)
            isotope_expected_height = 0
        else:
            # Prepare signal to be plotted
            isotope_height = isotope_averaged_spec.dropna(dim="mz").sel(
                mz=mz, method="nearest"
            )
            # Sum spectrum traces
            averaged_spec_mz = isotope_averaged_spec.mz.values.astype(np.float32)
            averaged_spec_y = isotope_averaged_spec.values.astype(np.float32)
            if i == 0:
                # Set signal normalization constant
                main_isotope_height = float(isotope_height)
            isotope_expected_height = main_isotope_height * (
                rel_abu / rel_abus[main_isotope_i]
            )
        # MS signal trace
        spectrum_traces.append(
            {
                "name": "{:d}".format(round(mz)),
                "target_isotope_id": current_target_isotope_id,
                "type": "scatter",
                "mode": "lines",
                "line": {"color": "rgb({},{},{})".format(*colormap[i + COLOR_OFFSET])},
                "fill": "tozeroy",
                "fillcolor": "rgba({},{},{}, .3)".format(*colormap[i + COLOR_OFFSET]),
                "x": averaged_spec_mz.tobytes(),
                "y": averaged_spec_y.tobytes(),
                "unit": units,
            }
        )
        peak_profiles = get_peaks(isotope_slice, peak_profile_type)
        # Peak traces (vertical lines)
        peaks = isotope_slice.peak_heights.mean(dim="time").compute()
        runtime.logger.debug(f"Peaks in the range {mz_range}: {peaks.mz.values}")
        peaks = filter_peaks(peaks, intensity=peak_min_intensity)
        runtime.logger.debug(
            f"Peaks above threshold {peak_min_intensity}: {peaks.mz.values}"
        )
        # Get peak profiles/timeseries
        for peak in peaks:
            peak_mz = peak.mz.item()
            match = True if abs((peak_mz - mz) / mz * 1e6) <= mz_tolerance else False
            peak_height = peak.values.item()
            spectrum_traces.append(
                {
                    "name": "{:.4f}".format(peak_mz),
                    "type": "scatter",
                    "mode": "lines+markers" if match else "lines",
                    "line": {
                        "color": "white" if match else "grey",
                    },
                    "x": [peak_mz, peak_mz],
                    "y": [0, peak_height],
                    "unit": units,
                }
            )
            if match:
                # Timeseries trace
                match_timeseries = peak_profiles.sel(mz=peak_mz)
                timeseries_time = match_timeseries.time.values.astype(np.float32)
                timeseries_y = match_timeseries.values.astype(np.float32)
                timeseries_rgb = colormap[i + COLOR_OFFSET]
                timeseries_traces.append(
                    {
                        "name": "{:.4f}".format(mz),
                        "type": "scatter",
                        "mode": "lines",
                        "line": {"color": "rgb({},{},{})".format(*timeseries_rgb)},
                        "fill": "tozeroy",
                        "fillcolor": "rgba({},{},{},.3)".format(*timeseries_rgb),
                        "x": timeseries_time.tobytes(),
                        "y": timeseries_y.tobytes(),
                        "unit": units,
                    }
                )
                if i == 0 and sum_timeseries is None:
                    sum_timeseries = match_timeseries
                elif i > 0 and sum_timeseries is not None:
                    sum_timeseries += match_timeseries
                match_isotope_counter += 1

        # Target mz trace (red vertical line)
        spectrum_traces.append(
            {
                "name": "target m/z",
                "type": "scatter",
                "mode": "lines",
                "line": {
                    "color": "red",
                },
                "x": [float(mz), float(mz)],
                "y": [0, isotope_expected_height],
                "unit": units,
            }
        )

        await sio.emit("visualization_signal_sum_spectrum", spectrum_traces, room=sid)

        await sio.emit("visualization_signal_timeseries", timeseries_traces, room=sid)
        # Sleep 0 to let other tasks be scheduled before next iteration
        await asyncio.sleep(0)

    # Step 5: Constructs and emits the sum timeseries trace if applicable.
    # If no data to visualize, return early
    if match_isotope_counter <= 1 or sum_timeseries is None:
        return
    # Sum timeseries trace
    timeseries_time = sum_timeseries.time.values.astype(np.float32)
    timeseries_y = sum_timeseries.values.astype(np.float32)
    timeseries_traces = [
        {
            "name": "sum",
            "type": "scatter",
            "fill": "tozeroy",
            "fillcolor": "rgba(136, 136, 136, .3)",
            "line": {"color": "rgb(136, 136, 136)"},
            "x": timeseries_time.tobytes(),
            "y": timeseries_y.tobytes(),
            "unit": units,
        },
    ]
    await sio.emit("visualization_signal_timeseries", timeseries_traces, room=sid)
