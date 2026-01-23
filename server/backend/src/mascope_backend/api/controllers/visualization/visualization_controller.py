from dataclasses import dataclass, field
from typing import Any

import numpy as np
import xarray as xr
from colorcet import glasbey_hv as colormap
from sqlalchemy import select

import mascope_signal.compute as m_compute
from mascope_backend.api.controllers.samples.lib.samples_fetch import fetch_sample
from mascope_backend.api.lib.api_features import api_controller_background_task
from mascope_backend.api.lib.exceptions.api_exceptions import NotFoundException
from mascope_backend.db import Sample, TargetIsotope, async_session
from mascope_backend.socket import sio
from mascope_file.io import load_peak_data, read_props
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
    min_isotope_abundance: float,
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
    1. Fetches sample filename and target ion data from the database.
    2. Loads the sample file and prepares a data slice for analysis.
    3. Iterates over each target isotope, computing and emitting visualization traces for the sum spectrum and time series.
    4. Constructs and emits the sum timeseries trace if applicable.

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
    :param user_id: Current user triggered operation (for user notifications)
    :type user_id: int | None, optional,
    :param process_id: Process ID for tracking the visualization task.
    :type process_id: str, optional
    :param sid: Socket ID of the requesting client. Passed back to the client
    :type sid: str | None, optional
    :raises NotFoundException: If the sample item or target ion does not exist or does not meet the specified criteria.
    """
    sample = await fetch_sample(sample_item_id)
    instrument_property = InstrumentPropertyResolver(sample)
    target_isotopes = await _fetch_target_isotopes(
        target_ion_id, min_isotope_abundance, instrument_property
    )

    peak_data, averaged_signal = await _load_peaks_and_averaged_signal(
        sample, target_isotopes
    )

    isotope_relative_abundances = [
        isotope.relative_abundance for isotope in target_isotopes
    ]

    scan_timestamps = m_compute.get_scan_timestamps(
        sample.filename, t_min=sample.t0, t_max=sample.t1, polarity=sample.polarity
    )

    match_counter = 0
    sum_timeseries = None
    main_isotope_height = 0
    all_spectrum_traces = []
    all_timeseries_traces = []
    for i, isotope in enumerate(target_isotopes):
        ctx = IsotopeContext(
            index=i,
            isotope=isotope,
            relative_abundances=isotope_relative_abundances,
            averaged_signal=averaged_signal,
            peak_data=peak_data,
            time_scan=scan_timestamps,
            peak_min_intensity=peak_min_intensity,
            mz_tolerance=mz_tolerance,
            main_isotope_height=main_isotope_height,
            instrument_property=instrument_property,
        )
        isotope_result = await _process_isotope(ctx, sum_timeseries)
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


class InstrumentPropertyResolver:
    """Resolves preferred peak data type and resolution"""

    def __init__(self, sample):
        self.instrument_type = get_instrument_type(sample.filename)

    @property
    def peak_data_type(self):
        if self.instrument_type == "tof":
            return "area"
        if self.instrument_type == "orbi":
            return "height"
        raise ValueError(f"Unknown instrument type: {self.instrument_type}")

    @property
    def resolution(self):
        if self.instrument_type == "tof":
            return "LOW"
        if self.instrument_type == "orbi":
            return "HIGH"
        raise ValueError(f"Unknown instrument type: {self.instrument_type}")


@dataclass
class IsotopeContext:
    index: int
    isotope: Any
    relative_abundances: list
    averaged_signal: Any
    peak_data: Any
    time_scan: Any
    peak_min_intensity: float
    mz_tolerance: int
    main_isotope_height: float
    instrument_property: Any
    color_offset: int = COLOR_OFFSET


@dataclass
class IsotopeResult:
    spectrum_traces: list = field(default_factory=list)
    timeseries_traces: list = field(default_factory=list)
    match_count: int = 0
    sum_timeseries: Any = None
    main_isotope_height: float = 0


async def _load_peaks_and_averaged_signal(
    sample: Sample, target_isotopes: list[TargetIsotope]
) -> tuple[xr.DataArray, xr.DataArray]:
    """
    Loads peak data and averaged signal for the specified sample and target isotopes.

    :param sample: The sample object containing filename and time range.
    :type sample: Sample
    :param target_isotopes: List of target isotope objects with m/z values.
    :type target_isotopes: list[TargetIsotope]
    :return: Tuple of (peak_data, averaged_signal) for the specified m/z window.
    :rtype: tuple[xr.DataArray, xr.DataArray]
    """
    peak_data = load_peak_data(sample.filename)
    all_mzs = peak_data.mz.values

    target_mzs = np.array([iso.mz for iso in target_isotopes])
    closest_mzs = peak_data.sel(mz=target_mzs, method="nearest").mz.values
    closest_mzs = np.unique(closest_mzs)

    mz_mask = np.any(np.abs(all_mzs[:, None] - closest_mzs[None, :]) <= DMZ, axis=1)
    mz_to_extract = all_mzs[mz_mask]

    peak_timeseries = await m_compute.load_peak_timeseries(
        sample.filename, mz_to_extract
    )

    # Attach sample file metadata to peak_data
    props = read_props(sample.filename)
    peak_timeseries.attrs.update({"props": props})

    averaged_signal = (
        m_compute.get_sum_signal(
            sample.filename,
            sample.t0,
            sample.t1,
            polarity=sample.polarity,
            average=True,
        )
        .sel(mz=slice(np.min(mz_to_extract) - DMZ, np.max(mz_to_extract) + DMZ))
        .compute()
    )
    return peak_timeseries, averaged_signal


async def _fetch_target_isotopes(
    target_ion_id, min_isotope_abundance, instrument_property
):
    """
    Fetches target isotopes for a given target ion ID, minimum isotope abundance, and instrument property.

    :param target_ion_id: ID of the target ion to fetch isotopes for.
    :type target_ion_id: str
    :param min_isotope_abundance: Minimum relative abundance threshold for isotopes.
    :type min_isotope_abundance: float
    :param instrument_property: Instrument property resolver with resolution information.
    :type instrument_property: InstrumentPropertyResolver
    :raises NotFoundException: If no isotopes are found matching the criteria.
    :return: List of TargetIsotope objects matching the criteria.
    :rtype: list
    """
    async with async_session() as session:
        # Fetch target ion data
        stmt = (
            select(TargetIsotope)
            .where(
                TargetIsotope.target_ion_id == target_ion_id,
                TargetIsotope.relative_abundance >= min_isotope_abundance,
                TargetIsotope.resolution == instrument_property.resolution,
            )
            .order_by(TargetIsotope.relative_abundance.desc())
        )
        result = await session.execute(stmt)
        target_ion_data = result.scalars().all()
        if not target_ion_data:
            raise NotFoundException(
                f"Target ion with ID {target_ion_id} not found or does not meet abundance threshold"
            )
        return target_ion_data


async def _process_isotope(
    ctx: IsotopeContext, sum_timeseries: Any | None
) -> IsotopeResult:
    """
    Processes a single isotope for visualization, generating spectrum and timeseries traces,
    and updating the sum timeseries if peaks match the target isotope.

    :param ctx: The context containing isotope and processing parameters.
    :type ctx: IsotopeContext
    :param sum_timeseries: The current sum timeseries to update, or None.
    :type sum_timeseries: xarray.Dataarray | None
    :return: Result object containing traces, match count, updated sum_timeseries, and main isotope height.
    :rtype: IsotopeResult
    """
    isotope_result = IsotopeResult(
        main_isotope_height=ctx.main_isotope_height, sum_timeseries=sum_timeseries
    )
    mz_range = (ctx.isotope.mz - DMZ, ctx.isotope.mz + DMZ)
    isotope_averaged_spec = ctx.averaged_signal.sel(mz=slice(*mz_range))

    isotope_slice = ctx.peak_data.sel(mz=slice(*mz_range))
    peak_timeseries = get_peaks(isotope_slice, ctx.instrument_property.peak_data_type)
    mean_peak_heights = isotope_slice.peak_heights.sel(
        time=ctx.time_scan, method="nearest"
    ).mean(dim="time")
    mean_peak_heights = filter_peaks(
        mean_peak_heights, intensity=ctx.peak_min_intensity
    )

    if isotope_averaged_spec.size == 0:
        # No spectrum in the given mz range
        averaged_spec_mz = np.array(list(mz_range), dtype=np.float32)
        averaged_spec_y = np.array([0, 0], dtype=np.float32)
        isotope_expected_height = 0
    else:
        averaged_spec_mz = isotope_averaged_spec.mz.values.astype(np.float32)
        averaged_spec_y = isotope_averaged_spec.values.astype(np.float32)
        if ctx.index == 0:
            # Main isotope: determine main isotope height
            try:
                peak = mean_peak_heights.sel(mz=ctx.isotope.mz, method="nearest")
                peak_height = peak.item()
            except KeyError:
                # Fall-back if no peak is found
                peak_height = np.max(averaged_spec_y)
            isotope_result.main_isotope_height = peak_height

        # Calculate expected height based on relative abundance
        isotope_expected_height = isotope_result.main_isotope_height * (
            ctx.isotope.relative_abundance / ctx.relative_abundances[0]
        )

    isotope_result.spectrum_traces.append(
        {
            "name": "{:d}".format(round(ctx.isotope.mz)),
            "target_isotope_id": ctx.isotope.target_isotope_id,
            "type": "scatter",
            "mode": "lines",
            "line": {
                "color": "rgb({},{},{})".format(*colormap[ctx.index + ctx.color_offset])
            },
            "fill": "tozeroy",
            "fillcolor": "rgba({},{},{}, .3)".format(
                *colormap[ctx.index + ctx.color_offset]
            ),
            "x": averaged_spec_mz.tobytes(),
            "y": averaged_spec_y.tobytes(),
            "unit": UNITS,
        }
    )

    for peak in mean_peak_heights:
        peak_result = await _process_peak(
            peak, ctx, peak_timeseries, isotope_result.sum_timeseries
        )
        isotope_result.spectrum_traces.append(peak_result["peak_trace"])
        if peak_result["timeseries_trace"]:
            isotope_result.timeseries_traces.append(peak_result["timeseries_trace"])
        if peak_result["is_match"]:
            isotope_result.match_count += 1
            isotope_result.sum_timeseries = peak_result["sum_timeseries"]

    # Target mz trace (red vertical line)
    isotope_result.spectrum_traces.append(
        {
            "name": "target m/z",
            "type": "scatter",
            "mode": "lines",
            "line": {"color": "red"},
            "x": [float(ctx.isotope.mz), float(ctx.isotope.mz)],
            "y": [0, isotope_expected_height],
            "unit": UNITS,
        }
    )

    return isotope_result


async def _process_peak(peak, ctx: IsotopeContext, peak_timeseries, sum_timeseries):
    """
    Processes a single peak for a given isotope,
    generating visualization traces and updating the sum timeseries if the peak matches.

    :param peak: The peak object to process.
    :type peak: xarray.DataArray or similar
    :param ctx: The context containing isotope and processing parameters.
    :type ctx: IsotopeContext
    :param peak_timeseries: The peak timeseries for the isotope.
    :type peak_timeseries: xarray.DataArray or similar
    :param sum_timeseries: The current sum timeseries to update, or None.
    :type sum_timeseries: xarray.DataArray or None
    :return: Dictionary with peak trace, timeseries trace, match status, and updated sum_timeseries.
    :rtype: dict
    """
    peak_mz = peak.mz.item()
    match = abs((peak_mz - ctx.isotope.mz) / ctx.isotope.mz * 1e6) <= ctx.mz_tolerance
    peak_height = peak.item()
    peak_trace = {
        "name": "{:.4f}".format(peak_mz),
        "type": "scatter",
        "mode": "lines+markers" if match else "lines",
        "line": {"color": "white" if match else "grey"},
        "x": [peak_mz, peak_mz],
        "y": [0, peak_height],
        "unit": UNITS,
    }
    timeseries_trace = None
    if match:
        match_timeseries = peak_timeseries.sel(mz=peak_mz).copy()
        timeseries_time = match_timeseries.time.values.astype(np.float32)

        # Unsure gap in timeseries in case of several polarities within one sample file
        signal_gap_mask = ~np.isin(timeseries_time, ctx.time_scan.astype(np.float32))
        match_timeseries.values[signal_gap_mask] = np.nan
        timeseries_y = match_timeseries.values.astype(np.float32)

        timeseries_rgb = colormap[ctx.index + ctx.color_offset]
        timeseries_trace = {
            "name": "{:.4f}".format(ctx.isotope.mz),
            "type": "scatter",
            "mode": "lines",
            "line": {"color": "rgb({},{},{})".format(*timeseries_rgb)},
            "fill": "tozeroy",
            "fillcolor": "rgba({},{},{},.3)".format(*timeseries_rgb),
            "x": timeseries_time.tobytes(),
            "y": timeseries_y.tobytes(),
            "unit": UNITS,
        }
        if sum_timeseries is None:
            sum_timeseries = match_timeseries.copy()
        else:
            sum_timeseries += match_timeseries
    return {
        "peak_trace": peak_trace,
        "timeseries_trace": timeseries_trace,
        "is_match": match,
        "sum_timeseries": sum_timeseries,
    }
