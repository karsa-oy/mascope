import asyncio

from sqlalchemy.future import select
from backend.db import async_session
from backend.api_sio import sio
from ..models.models import Sample, TargetIsotope
from ..exceptions import process_exception, NotFoundException
import numpy as np
import pandas as pd
from colorcet import glasbey_hv as colormap
from lib.file_func import load_file
from lib.peak import filter_peaks, get_peaks


async def visualize_ion_focus(
    sid,
    sample_item_id,
    target_ion_id,
    min_isotope_abundance,
    peak_min_intensity,
    mz_tolerance,
):
    """
    Visualizes the focus on a specific ion for a given sample item by computing and emitting sum spectrum and time series data.

    The function performs the following steps:
    1. Fetches sample filename and target ion data from the database.
    2. Loads the sample file and prepares a data slice for analysis.
    3. Converts target ion data to a DataFrame and prepares m/z values, relative abundances, and target isotope IDs for processing.
    4. Iterates over each target isotope, computing and emitting visualization traces for the sum spectrum and time series.
    5. Constructs and emits the sum timeseries trace if applicable.

    :param sid: Session ID for emitting data to the specific client.
    :type sid: str
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
    :raises NotFoundException: If the sample item or target ion does not exist or does not meet the specified criteria.
    :raises process_exception: For handling any exceptions that occur during visualization.
    """
    try:
        # Step 1: Fetch sample filename and target ion data from the database
        async with async_session() as session:
            # Fetch sample filename
            stmt = select(Sample.filename).where(
                Sample.sample_item_id == sample_item_id
            )
            result = await session.execute(stmt)
            filename = result.scalar_one_or_none()
            if not filename:
                raise NotFoundException(f"Sample with ID {sample_item_id} not found")

            # Fetch target ion data
            stmt = select(TargetIsotope).where(
                TargetIsotope.target_ion_id == target_ion_id,
                TargetIsotope.relative_abundance >= min_isotope_abundance,
            )
            result = await session.execute(stmt)
            target_ion_data = result.scalars().all()
            if not target_ion_data:
                raise NotFoundException(
                    f"Target ion with ID {target_ion_id} not found or does not meet abundance threshold"
                )

        # Step 2: Load the sample file and prepare data slice
        print("Loading file: %s" % filename)
        sample_file = load_file(filename, vars=["signal", "peak_heights"])
        t_range = [0, sample_file.props["length"]]  # Full time range
        sample_file_slice = sample_file.sel(time=slice(*t_range))

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
        for i, mz in enumerate(mzs):
            print("{:d}/{:d}: {:3f}".format(i + 1, len(mzs), mz))
            spectrum_traces = []
            timeseries_traces = []
            dmz = 0.5
            mz_range = (mz - dmz, mz + dmz)
            rel_abu = rel_abus[i]
            current_target_isotope_id = target_isotope_ids[i]

            isotope_slice = sample_file_slice.sel(mz=slice(*mz_range)).compute()
            isotope_sum_spectrum = isotope_slice.sum(dim="time").compute()
            isotope_height = isotope_sum_spectrum.signal.sel(mz=mz, method="nearest")
            # Sum spectrum traces
            sum_spectrum_mz = isotope_sum_spectrum.mz.values.astype(np.float32)
            sum_spectrum_y = isotope_sum_spectrum.signal.values.astype(np.float32)
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
                    "line": {"color": "rgb({},{},{})".format(*colormap[i])},
                    "fill": "tozeroy",
                    "fillcolor": "rgba({},{},{}, .3)".format(*colormap[i]),
                    "x": sum_spectrum_mz.tobytes(),
                    "y": sum_spectrum_y.tobytes(),
                    "xaxis": "x{:d}".format(i + 1),
                    "yaxis": "y{:d}".format(i + 1),
                }
            )
            # Peak traces (vertical lines)
            peaks = get_peaks(isotope_sum_spectrum, "height")
            peaks = filter_peaks(peaks, intensity=peak_min_intensity)
            for peak in peaks:
                peak_mz = peak.mz.item()
                match = (
                    True if abs((peak_mz - mz) / mz * 1e6) <= mz_tolerance else False
                )
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
                        "xaxis": "x{:d}".format(i + 1),
                        "yaxis": "y{:d}".format(i + 1),
                    }
                )
                if match:
                    # Timeseries trace
                    match_timeseries = isotope_slice.signal.sel(
                        mz=peak_mz, method="nearest"
                    )
                    timeseries_time = match_timeseries.time.values.astype(np.float32)
                    timeseries_y = match_timeseries.values.astype(np.float32)
                    timeseries_traces.append(
                        {
                            "name": "{:.4f}".format(mz),
                            "type": "scatter",
                            "mode": "lines",
                            "line": {"color": "rgb({},{},{})".format(*colormap[i])},
                            "x": timeseries_time.tobytes(),
                            "y": timeseries_y.tobytes(),
                        }
                    )
                    if i == 0 and sum_timeseries is None:
                        sum_timeseries = match_timeseries
                    elif i > 0 and sum_timeseries is not None:
                        sum_timeseries += match_timeseries
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
                    "xaxis": "x{:d}".format(i + 1),
                    "yaxis": "y{:d}".format(i + 1),
                }
            )

            await sio.emit(
                "visualization_signal_sum_spectrum", spectrum_traces, room=sid
            )

            await sio.emit(
                "visualization_signal_timeseries", timeseries_traces, room=sid
            )
            # Sleep 0 to let other tasks be scheduled before next iteration
            await asyncio.sleep(0)

        # Step 5: Constructs and emits the sum timeseries trace if applicable.
        # If no data to visualize, return early
        if sum_timeseries is None:
            return
        # Sum timeseries trace
        timeseries_time = sum_timeseries.time.values.astype(np.float32)
        timeseries_y = sum_timeseries.values.astype(np.float32)
        timeseries_traces = [
            {
                "name": "sum",
                "type": "scatter",
                "fill": "tozeroy",
                "fillcolor": "rgba(255, 255, 255, .3)",
                "line": {"color": "white"},
                "x": timeseries_time.tobytes(),
                "y": timeseries_y.tobytes(),
            },
        ]
        await sio.emit("visualization_signal_timeseries", timeseries_traces, room=sid)

    except Exception as e:
        # TODO_error_handling construct some common backfround task fail notification
        raise process_exception(
            e,
            f"Failed to visualize ion '{target_ion_id}' focus for sample '{sample_item_id}'.",
        )
