import asyncio

import numpy as np
import pandas as pd
from colorcet import glasbey_hv as colormap

from backend.db.conn import conn
from backend.lib.file import load_file
from backend.lib.peak import filter_peaks, get_peaks
from backend.server import sio


@sio.event(namespace="/")
async def visualization_ion_focus(
    sid,
    sample_item_id,
    target_ion_id,
    min_isotope_abundance,
    peak_min_intensity,
    mz_tolerance,
):
    t_range = None
    with conn:
        # Get filename
        filename = pd.read_sql(
            f"""--sql
            SELECT filename
            FROM sample_item
            WHERE sample_item_id == ?
        """,
            conn,
            params=[sample_item_id],
        )["filename"].tolist()[0]
        # Get ion data
        target_ion_df = pd.read_sql(
            f"""--sql
            SELECT mz, relative_abundance
            FROM target_isotope
            WHERE target_ion_id == ?
            AND relative_abundance >= ?
            """,
            conn,
            params=[target_ion_id, min_isotope_abundance],
        )
        mzs = target_ion_df["mz"].tolist()
        rel_abus = target_ion_df["relative_abundance"].tolist()

    # Load file
    print("Loading file: %s" % filename)
    sample_file = load_file(filename, vars=["signal", "peak_heights"])

    if t_range is None or t_range == [None, None]:
        # Full time range
        t_range = [0, sample_file.props["length"]]

    sample_file_slice = sample_file.sel(time=slice(*t_range))
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
        await sio.emit("visualization_signal_sum_spectrum", spectrum_traces, room=sid)

        await sio.emit("visualization_signal_timeseries", timeseries_traces, room=sid)
        # Sleep 0 to let other tasks be scheduled before next iteration
        await asyncio.sleep(0)

    if not len(timeseries_traces):
        return
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
