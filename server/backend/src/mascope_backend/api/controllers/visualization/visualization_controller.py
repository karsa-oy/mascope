import asyncio
from dataclasses import dataclass, field
from types import SimpleNamespace

import numpy as np
import xarray as xr
from colorcet import glasbey_hv as colormap
from sqlalchemy import select

import mascope_signal.compute as m_compute
from mascope_backend.api.controllers.samples.lib.samples_fetch import fetch_sample
from mascope_backend.api.lib.api_features import api_controller_background_task
from mascope_backend.api.lib.exceptions.api_exceptions import NotFoundException
from mascope_backend.db import Sample, TargetIsotope, MatchIsotope, async_session
from mascope_backend.socket import sio
import mascope_file.io as m_io
from mascope_file.name import get_instrument_type
from mascope_signal.peak import filter_peaks, get_peaks


# TODO_configuration shift traces color
COLOR_OFFSET = 5
DMZ = 0.3
UNITS = "counts/s"


@api_controller_background_task(
    error_notification_rooms=["user_id"],
)
async def visualize_ion_focus(
    sample_item_id: str,
    target_ion_id: str,
    peak_min_intensity: float,
    mz_tolerance: float,
    independent_transaction: bool = False,
    user_id: int | None = None,
    process_id: str = None,
    sid: str | None = None,
):
    """
    Visualizes the focus on a specific ion for a given sample item by computing and emitting sum spectrum and time series data.

    The function performs the following steps:
    - Fetches sample filename and target ion data from the database.
    - Loads the sample file and prepares a data slice for analysis.
    - Iterates over each target isotope, computing and emitting visualization traces for the sum spectrum and time series.
    - Constructs and emits the sum timeseries trace if applicable.

    :param sample_item_id: ID of the sample item to visualize.
    :type sample_item_id: str
    :param target_ion_id: ID of the target ion to focus on.
    :type target_ion_id: str
    :param peak_min_intensity: Minimum peak intensity threshold for considering a match.
    :type peak_min_intensity: float
    :param mz_tolerance: Tolerance for mass-to-charge ratio (m/z) error, in parts per million (ppm).
    :type mz_tolerance: float
    :param independent_transaction: Indicates if the visualization should be considered an independent transaction, which affects sio event emission.
    :type independent_transaction: bool, optional
    :param user_id: Current user triggered operation (for user notifications)
    :type user_id: int | None, optional,
    :param process_id: Process ID for tracking the visualization task.
    :type process_id: str, optional
    :param sid: Socket ID of the requesting client. Passed back to the client
    :type sid: str | None, optional
    :raises NotFoundException: If the sample item or target ion does not exist or does not meet the specified criteria.
    """
    # --- Fetch sample and match isotope data --- #
    sample_task = fetch_sample(sample_item_id)
    isotope_task = _fetch_isotopes(sample_item_id, target_ion_id)
    sample, isotopes = await asyncio.gather(sample_task, isotope_task)

    # -- Extract data for IsotopeContext --- #
    peak_timeseries, mean_peak_heights, averaged_signal = (
        await _load_peaks_and_averaged_signal(sample, isotopes)
    )
    isotope_relative_abundances = [iso.relative_abundance for iso in isotopes]

    # --- Process each isotope and generate visualization traces --- #
    match_counter = 0
    sum_timeseries = None
    main_isotope_height = 0
    all_spectrum_traces = []
    all_timeseries_traces = []
    for i, iso in enumerate(isotopes):
        ctx = IsotopeContext(
            index=i,
            main_isotope_height=main_isotope_height,
            relative_abundances=isotope_relative_abundances,
            averaged_signal=averaged_signal,
            peak_timeseries=peak_timeseries,
            mean_peak_heights=mean_peak_heights,
            peak_min_intensity=peak_min_intensity,
            mz_tolerance=mz_tolerance,
        )
        isotope_result = _process_isotope(iso, ctx, sum_timeseries)
        match_counter += isotope_result.match_count
        sum_timeseries = isotope_result.sum_timeseries
        main_isotope_height = isotope_result.main_isotope_height

        all_spectrum_traces.extend(isotope_result.spectrum_traces)
        all_timeseries_traces.extend(isotope_result.timeseries_traces)

    if match_counter > 1 and sum_timeseries is not None:
        sum_timeseries_time = sum_timeseries.time.values.astype(np.float32)
        sum_timeseries_y = sum_timeseries.values.astype(np.float32)
        all_timeseries_traces.append(
            {
                "name": "sum",
                "type": "scatter",
                "fill": "tozeroy",
                "fillcolor": "rgba(136, 136, 136, .3)",
                "line": {"color": "rgb(136, 136, 136)"},
                "x": sum_timeseries_time.tobytes(),
                "y": sum_timeseries_y.tobytes(),
                "unit": UNITS,
            },
        )

    # Socket ID is included in the payload, so the client can filter messages
    # in case the same user has multiple sessions open
    await sio.emit(
        "visualization_signal_sum_spectrum",
        {"sid": sid, "data": all_spectrum_traces},
        room=f"user-{user_id}",
    )
    await sio.emit(
        "visualization_signal_timeseries",
        {"sid": sid, "data": all_timeseries_traces},
        room=f"user-{user_id}",
    )


# --- Helpers --- #


@dataclass
class IsotopeContext:
    """Keeps shared data among all isotopes"""

    index: int
    main_isotope_height: float
    relative_abundances: list
    averaged_signal: xr.DataArray
    peak_timeseries: xr.DataArray
    mean_peak_heights: xr.DataArray
    peak_min_intensity: float
    mz_tolerance: float
    color_offset: int = COLOR_OFFSET


@dataclass
class IsotopeResult:
    spectrum_traces: list = field(default_factory=list)
    timeseries_traces: list = field(default_factory=list)
    match_count: int = 0
    sum_timeseries: xr.DataArray | None = None
    main_isotope_height: float = 0


async def _load_peaks_and_averaged_signal(
    sample: Sample,
    isotopes: list[SimpleNamespace],
) -> tuple[xr.DataArray, xr.DataArray]:
    """
    Loads peak data and averaged signal for the specified sample and match isotopes.

    :param sample: The sample object containing filename and time range.
    :type sample: Sample
    :param isotopes: List of match isotope data.
    :type isotopes: list[SimpleNamespace]
    :param instrument_property: The instrument property resolver for determining peak data type.
    :type instrument_property: InstrumentPropertyResolver
    :return: Tuple of (peak_timeseries, mean_peak_heights, averaged_signal) for the specified m/z window.
    :rtype: tuple[xr.DataArray, xr.DataArray, xr.DataArray]
    """

    # --- Get averaged signal around target isotopes (+-DMZ) --- #
    target_mzs = np.array([iso.mz for iso in isotopes])
    target_mz_range = (np.min(target_mzs), np.max(target_mzs))

    all_peak_mzs = m_io.load_coord(sample.filename, "peak_timeseries", "mz")
    closest_indices = np.searchsorted(all_peak_mzs, target_mz_range)
    closest_indices = np.clip(closest_indices, 0, len(all_peak_mzs) - 1)
    closest_mzs = all_peak_mzs[closest_indices]
    mz_min, mz_max = (closest_mzs[0] - DMZ, closest_mzs[1] + DMZ)
    averaged_signal = (
        m_compute.get_sum_signal(
            sample.filename,
            sample.t0,
            sample.t1,
            polarity=sample.polarity,
            average=True,
        )
        .sel(mz=slice(mz_min, mz_max))
        .compute()
    )

    # --- Load peak timeseries for matched isotopes --- #
    match_mzs = [
        iso.sample_peak_mz for iso in isotopes if iso.sample_peak_mz is not None
    ]
    peak_timeseries = await m_compute.load_peak_timeseries(sample.filename, match_mzs)

    # --- Get peak heights to plot isotope expected heights ---
    scan_timestamps = m_compute.get_scan_timestamps(
        sample.filename, t_min=sample.t0, t_max=sample.t1, polarity=sample.polarity
    )
    mean_peak_heights = (
        peak_timeseries.peak_heights.sel(time=scan_timestamps, method="nearest")
        .mean(dim="time")
        .compute()
    )

    # --- Prepare peak timeseries with instrument-specific data type --- #
    # Leave instrument-specific peak data type in the timeseries
    instrument_type = get_instrument_type(sample.filename)
    match instrument_type:
        case "tof":
            peak_data_type = "area"
        case "orbi":
            peak_data_type = "height"
        case _:
            raise ValueError(f"Unknown instrument type: {instrument_type}")
    peak_timeseries = get_peaks(peak_timeseries, peak_data_type).compute()

    # Set Nan for times not in timestamps to ensure gaps in timeseries
    # in case of several polarities within one sample file
    time_scan = peak_timeseries.time.values.astype(np.float32)
    signal_gap_mask = ~np.isin(time_scan, scan_timestamps.astype(np.float32))
    time_axis = peak_timeseries.dims.index("time")
    if time_axis == 0:
        peak_timeseries.values[signal_gap_mask, ...] = np.nan
    else:
        peak_timeseries.values[..., signal_gap_mask] = np.nan

    # Attach sample file metadata to peak_data
    props = m_io.read_props(sample.filename)
    peak_timeseries.attrs.update({"props": props})

    return peak_timeseries, mean_peak_heights, averaged_signal


async def _fetch_isotopes(sample_item_id, target_ion_id):
    """
    Fetches match and target isotopes for a given target ion ID and sample item ID

    :param sample_item_id: ID of the sample item to fetch matched isotopes for.
    :type sample_item_id: str
    :param target_ion_id: ID of the target ion to fetch matched isotopes for.
    :type target_ion_id: str
    :raises NotFoundException: If no isotopes are found matching the criteria.
    :return: List of isotopes merged from TargetIsotope, MatchIsotope matching the criteria.
    :rtype: list
    """
    async with async_session() as session:
        stmt = (
            select(TargetIsotope, MatchIsotope)
            .where(TargetIsotope.target_ion_id == target_ion_id)
            .where(MatchIsotope.sample_item_id == sample_item_id)
            .join(
                TargetIsotope,
                MatchIsotope.target_isotope_id == TargetIsotope.target_isotope_id,
            )
            .order_by(TargetIsotope.relative_abundance.desc())
        )
        result = await session.execute(stmt)
        rows = result.all()

    if not rows:
        raise NotFoundException("No isotopes found for the given target ion ID.")

    def _model_to_dict(obj):
        return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}

    # Merge TargetIsotope and MatchIsotope data into a single list of isotopes
    # use SimpleNamespace for easy attribute access with dot notation
    isotopes = [
        SimpleNamespace(**{**_model_to_dict(t), **_model_to_dict(m)}) for t, m in rows
    ]

    return isotopes


def _process_isotope(
    iso: SimpleNamespace, ctx: IsotopeContext, sum_timeseries: xr.DataArray | None
) -> IsotopeResult:
    """
    Processes a single isotope for visualization, generating spectrum and timeseries traces,
    and updating the sum timeseries if peaks match the target isotope.

    :param iso: The isotope data.
    :type iso: SimpleNamespace
    :param ctx: The context containing isotope and processing parameters.
    :type ctx: IsotopeContext
    :param sum_timeseries: The current sum timeseries to update, or None.
    :type sum_timeseries: xr.DataArray | None
    :return: Result object containing traces, match count, updated sum_timeseries, and main isotope height.
    :rtype: IsotopeResult
    """
    isotope_result = IsotopeResult(
        main_isotope_height=ctx.main_isotope_height, sum_timeseries=sum_timeseries
    )
    mz_min, mz_max = iso.mz - DMZ, iso.mz + DMZ
    isotope_averaged_spec = ctx.averaged_signal.sel(mz=slice(mz_min, mz_max))

    isotope_peak_heights = ctx.mean_peak_heights.sel(mz=slice(mz_min, mz_max))
    isotope_peak_heights = filter_peaks(
        isotope_peak_heights, intensity=ctx.peak_min_intensity
    )

    if isotope_averaged_spec.size == 0:
        # No spectrum in the given mz range
        averaged_spec_mz = np.array([mz_min, mz_max], dtype=np.float32)
        averaged_spec_y = np.array([0, 0], dtype=np.float32)
        isotope_expected_height = 0
    else:
        averaged_spec_mz = isotope_averaged_spec.mz.values.astype(np.float32)
        averaged_spec_y = isotope_averaged_spec.values.astype(np.float32)
        if ctx.index == 0:
            # Main isotope: determine main isotope height
            try:
                peak = isotope_peak_heights.sel(mz=iso.mz, method="nearest")
                isotope_result.main_isotope_height = peak.item()
            except KeyError:
                # Fall-back if no peak is found
                isotope_result.main_isotope_height = np.max(averaged_spec_y)

        # Calculate expected height based on relative abundance
        isotope_expected_height = isotope_result.main_isotope_height * (
            iso.relative_abundance / ctx.relative_abundances[0]
        )

    # Add spectrum trace for the isotope
    iso_color = colormap[ctx.index + ctx.color_offset]
    isotope_result.spectrum_traces.append(
        {
            "name": "{:d}".format(round(iso.mz)),
            "target_isotope_id": iso.target_isotope_id,
            "type": "scatter",
            "mode": "lines",
            "line": {"color": "rgb({},{},{})".format(*iso_color)},
            "fill": "tozeroy",
            "fillcolor": "rgba({},{},{}, .3)".format(*iso_color),
            "x": averaged_spec_mz.tobytes(),
            "y": averaged_spec_y.tobytes(),
            "unit": UNITS,
        }
    )

    # Derive match criteria
    is_match = iso.match_score > 0.0

    # Add peak trace for the sample peak matching the isotope, if exists
    if is_match:
        peak_trace_mode = "lines+markers"
        peak_line_color = "white"
    else:
        peak_trace_mode = "lines"
        peak_line_color = "grey"

    peak_trace = {
        "name": "{:.6f}".format(iso.sample_peak_mz),
        "type": "scatter",
        "mode": peak_trace_mode,
        "line": {"color": peak_line_color},
        "x": [iso.sample_peak_mz, iso.sample_peak_mz],
        "y": [0, iso.sample_peak_intensity],
        "unit": UNITS,
    }
    isotope_result.spectrum_traces.append(peak_trace)

    # Add isotope expected trace
    isotope_result.spectrum_traces.append(
        {
            "name": "target m/z",
            "type": "scatter",
            "mode": "lines",
            "line": {"color": "red"},
            "x": [float(iso.mz), float(iso.mz)],
            "y": [0, isotope_expected_height],
            "unit": UNITS,
        }
    )

    # If there is a matching peak, add timeseries trace and update sum timeseries
    if is_match:
        isotope_result.match_count += 1
        match_timeseries = ctx.peak_timeseries.sel(mz=iso.sample_peak_mz)
        timeseries_time = match_timeseries.time.values.astype(np.float32)
        timeseries_y = match_timeseries.values.astype(np.float32)

        timeseries_rgb = colormap[ctx.index + ctx.color_offset]
        timeseries_trace = {
            "name": "{:.6f}".format(iso.mz),
            "type": "scatter",
            "mode": "lines",
            "line": {"color": "rgb({},{},{})".format(*timeseries_rgb)},
            "fill": "tozeroy",
            "fillcolor": "rgba({},{},{},.3)".format(*timeseries_rgb),
            "x": timeseries_time.tobytes(),
            "y": timeseries_y.tobytes(),
            "unit": UNITS,
        }
        isotope_result.timeseries_traces.append(timeseries_trace)
        if isotope_result.sum_timeseries is None:
            isotope_result.sum_timeseries = match_timeseries.copy()
        else:
            isotope_result.sum_timeseries += match_timeseries

    return isotope_result
