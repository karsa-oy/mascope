"""
This module provides functions to read and process Thermo Fisher raw files.
"""

import re
from typing import Iterable, Literal

import dask.array as da
import numpy as np
import pandas as pd
import xarray as xr
from System import NullReferenceException
from System.Collections.Generic import List
from ThermoFisher.CommonCore.Data import Extensions, ToleranceUnits
from ThermoFisher.CommonCore.Data.Business import (
    ChromatogramSignal,
    ChromatogramTraceSettings,
    Device,
    MassOptions,
    Range,
    TraceType,
)
from ThermoFisher.CommonCore.RawFileReader import RawFileReaderAdapter

from mascope_thermo.runtime import runtime


SECONDS_PER_MINUTE = 60


class InvalidRangeError(ValueError):
    pass


class PolarityError(ValueError):
    pass


class ScanTypeError(ValueError):
    pass


class NoScansFoundError(ValueError):
    pass


def _validate_mz_range(
    RawFile, mz_min: float | None, mz_max: float | None
) -> tuple[float, float]:
    low = RawFile.RunHeaderEx.LowMass if mz_min is None else mz_min
    high = RawFile.RunHeaderEx.HighMass if mz_max is None else mz_max
    if low > high:
        raise InvalidRangeError(
            f"Invalid m/z range: mz_min={low}, mz_max={high}, where mz_min > mz_max"
        )
    return low, high


class RawFileManager:
    """Handles safe open/close operations on raw file at datafile_path"""

    def __init__(self, datafile_path: str):
        self.path = datafile_path
        self.RawFile = None

    def __enter__(self):
        try:
            self.RawFile = RawFileReaderAdapter.FileFactory(self.path)
            self.RawFile.SelectInstrument(Device.MS, 1)
            # This includes the base peak into the spectrum
            self.RawFile.IncludeReferenceAndExceptionData = True
        except NullReferenceException:
            raise FileNotFoundError(f"Could not open raw file: {self.path}")
        return self.RawFile

    def __exit__(self, *args):
        if self.RawFile:
            self.RawFile.Dispose()


class ScanSelector:
    """Class to select scans and their indices based on polarity,
    time range, and scan type filters.
    """

    def __init__(
        self,
        RawFile: RawFileReaderAdapter,
        polarity: Literal["+", "-"] | None = None,
        t_min: float | None = None,
        t_max: float | None = None,
        ms_type: Literal["Ms", "Ms2"] | None = "Ms",
    ):
        self._RawFile = RawFile
        self._polarity = polarity
        self._t_min = t_min
        self._t_max = t_max
        self._ms_type = ms_type

        self.raw_scan_filters = [
            self._RawFile.GetFilterForScanNumber(i) for i in self.all_scan_indices
        ]
        self.raw_scan_stats = [
            self._RawFile.GetScanStatsForScanNumber(i) for i in self.all_scan_indices
        ]

    @property
    def all_scan_indices(self) -> list[int]:
        """Returns all scan indices in the raw file."""
        num_of_scans = self._RawFile.RunHeaderEx.SpectraCount
        return list(range(1, num_of_scans + 1))

    def _polarity_mask(self) -> np.ndarray:
        """Creates a boolean mask for the specified polarity."""
        if self._polarity not in ["-", "+"]:
            raise PolarityError(
                f"Invalid polarity '{self._polarity}' provided. "
                "Polarity must be '+' or '-'."
            )
        polarity_verbose = "Negative" if self._polarity == "-" else "Positive"
        return np.array(
            [
                filter.Polarity.ToString() == polarity_verbose
                for filter in self.raw_scan_filters
            ]
        )

    def _time_mask(self) -> np.ndarray:
        """Creates a boolean mask for the specified time range."""
        t_min = (
            self._RawFile.RunHeaderEx.StartTime * SECONDS_PER_MINUTE
            if self._t_min is None
            else self._t_min
        )
        t_max = (
            self._RawFile.RunHeaderEx.EndTime * SECONDS_PER_MINUTE
            if self._t_max is None
            else self._t_max
        )

        if t_min > t_max:
            raise InvalidRangeError(
                f"Invalid time range: t_min={t_min} s > t_max={t_max} s"
            )

        # Adjust time range as `abs_eps(x) ~ |x∣ * eps` where eps is machine epsilon
        # to account for floating point precision issues
        epsilon = np.finfo(np.float64).eps * t_max
        t_min_adj = t_min - epsilon
        t_max_adj = t_max + epsilon

        start_times_min = np.array([stats.StartTime for stats in self.raw_scan_stats])
        start_times_s = start_times_min * SECONDS_PER_MINUTE

        return np.logical_and(t_min_adj < start_times_s, start_times_s < t_max_adj)

    def _ms_type_mask(self) -> np.ndarray:
        """Creates a boolean mask for the specified MS scan type."""
        if self._ms_type not in ["Ms", "Ms2"]:
            raise ScanTypeError(
                f"Invalid scan type '{self._ms_type}' provided. "
                "MS scan type must be 'Ms' or 'Ms2'."
            )
        return np.array(
            [
                filter.MSOrder.ToString() == self._ms_type
                for filter in self.raw_scan_filters
            ]
        )

    @property
    def scan_indices_1based(self) -> list[int]:
        """Returns the list of scan indices that match the specified polarity,
        time range, and scan type.
        The scans are 1-based indexed, as per the Thermo library convention.
        """
        mask = np.ones(len(self.all_scan_indices), dtype=bool)

        if self._polarity:
            mask &= self._polarity_mask()

        if self._t_min is not None or self._t_max is not None:
            mask &= self._time_mask()

        if self._ms_type:
            mask &= self._ms_type_mask()

        filtered_indices = np.array(self.all_scan_indices)[mask]

        if len(filtered_indices) == 0:
            raise NoScansFoundError(
                "No scans found matching the specified filters: "
                f"polarity='{self._polarity}', "
                f"time_range=({self._t_min}, {self._t_max}), "
                f"ms_type='{self._ms_type}'"
            )

        return filtered_indices.tolist()

    @property
    def scan_indices_0based(self) -> list[int]:
        """Returns the list of scan indices converted to 0-based indexing for Python."""
        return [i - 1 for i in self.scan_indices_1based]

    @property
    def scan_indices_dotnet(self) -> List[int]:
        """Returns the list of scan indices as a .NET List[int] for use with
        Thermo library functions."""
        net_list = List[int]()
        for index in self.scan_indices_1based:
            net_list.Add(index)
        return net_list

    @property
    def scan_times(self) -> np.ndarray:
        """Returns the scan times [s] for the filtered scan indices."""
        return np.array(
            [
                self.raw_scan_stats[i].StartTime * SECONDS_PER_MINUTE
                for i in self.scan_indices_0based
            ]
        )

    @property
    def scans(self) -> tuple:
        """Returns the scan objects for the filtered scan indices."""
        return tuple(Extensions.GetScans(self._RawFile, self.scan_indices_dotnet))


def get_polarity_options(datafile_path: str) -> str:
    """Reads the polarities present in a raw file.

    :param datafile_path: Path to the Thermo Fisher raw file (.raw) containing the data.
    :type datafile_path: str
    :return: "-" if only negative polarities are present, "+" if only positive, "+-" if
            both are present.
    :rtype: str
    """
    with RawFileManager(datafile_path) as RawFile:
        scan_selector = ScanSelector(RawFile, ms_type=None)

        polarities = set(
            filter.Polarity.ToString() for filter in scan_selector.raw_scan_filters
        )

        has_positive = "Positive" in polarities
        has_negative = "Negative" in polarities

        if has_positive and has_negative:
            return "+-"
        elif has_positive:
            return "+"
        elif has_negative:
            return "-"
        else:
            raise PolarityError("No valid polarities found in the raw file.")


def get_signal(
    datafile_path: str,
    t_min: float | None = None,
    t_max: float | None = None,
    mz_min: float | None = None,
    mz_max: float | None = None,
    polarity: Literal["+", "-"] | None = None,
) -> xr.Dataset:
    """This function uses the Thermo Fisher libraries to read the raw file and extract
    the scan data. It then merges the scans to have a common m/z scale and converts
    the data to an xarray Dataset.
    Allows slicing by time and m/z range.

    t_min=None is equal to min scan time, t_max=None is equal to max scan time.
    mz_min=None is equal to min m/z, mz_max=None is equal to max m/z.

    :param datafile_path: Path to the Thermo Fisher raw file (.raw) containing the data.
    :type datafile_path: str
    :param t_min: Minimum time [s], optional, defaults to None
    :type t_min: float
    :param t_max: Maximum time [s], optional, defaults to None
    :type t_max: float
    :param mz_min: Minimum m/z, optional, defaults to None
    :type mz_min: float
    :param mz_max: Maximum m/z, optional, defaults to None
    :type mz_max: float
    :param polarity: + or -, Polarity of the scans to be retrieved, optional,
                    defaults to None
    :type polarity: str
    :return: An xarray Dataset containing the signal data
    :rtype: xr.Dataset
    """
    with RawFileManager(datafile_path) as RawFile:
        mz_min, mz_max = _validate_mz_range(RawFile, mz_min, mz_max)
        scan_selector = ScanSelector(RawFile, polarity, t_min, t_max)
        scan_time = scan_selector.scan_times

        scan_mzs, scan_specs = [], []
        for scan in scan_selector.scans:
            intensities = np.frombuffer(scan.SegmentedScan.Intensities)
            positions = np.frombuffer(scan.SegmentedScan.Positions)

            # Filter by m/z range
            mz_mask = np.logical_and(mz_min <= positions, positions <= mz_max)
            scan_mzs.append(positions[mz_mask])
            scan_specs.append(intensities[mz_mask])

        if not scan_mzs:
            low_mass = RawFile.RunHeaderEx.LowMass
            high_mass = RawFile.RunHeaderEx.HighMass

            raise InvalidRangeError(
                f"""No data found in the specified m/z range.
                M/z range of the raw file: {low_mass} - {high_mass}
                """
            )

        # Create a sorted union of all unique m/z values
        all_mzs = np.unique(np.concatenate(scan_mzs))

        # Initialize output array
        signal_array = np.zeros((len(all_mzs), len(scan_time)), dtype=np.float64)

        # Fill the 2D array using exact mz matching
        for scan_idx, (mz, intensity) in enumerate(zip(scan_mzs, scan_specs)):
            # Find indices where the current scan mz values appear in all_mzs
            indices = np.searchsorted(all_mzs, mz)
            # Only fill values that exist in this scan
            signal_array[indices, scan_idx] = intensity

        signal_dask = da.from_array(signal_array, chunks="auto")

        return xr.Dataset(
            {"signal": (("mz", "time"), signal_dask)},
            coords={"mz": all_mzs, "time": scan_time},
        )


def compute_sum_signal(
    datafile_path: str,
    t_min: float | None = None,
    t_max: float | None = None,
    ppm: int = 1,
    polarity: Literal["+", "-"] | None = None,
) -> tuple[xr.DataArray, int]:
    """Computes sum signal, binning counts within ``ppm`` value.
    Polarity and time filters may be optionally provided.

    :param datafile_path: Path to the Thermo Fisher raw file (.raw) containing the data.
    :type datafile_path: str
    :param t_min: Start time [s]
    :type t_min: float, optional
    :param t_max: End time [s]
    :type t_max: float, optional
    :param ppm: ppm precision for binning, defaults to 1. This value determines the mass
                tolerance for grouping m/z values, where a smaller ppm value results in
                finer binning and higher precision.
    :type ppm: int, optional
    :param polarity: + or -, Polarity of the scans to be retrieved, optional,
                    defaults to None
    :type polarity: str, optional
    :raises ValueError: If the specified time range is invalid, or if no data is found
                        in the specified filters, or the specified polarity is not found
                        in the raw file.
    :return: The sum signal and the number of combined scans
    :rtype: tuple[xr.DataArray, float]
    """
    with RawFileManager(datafile_path) as RawFile:
        # Setup mz tolerance - counts within ppm are binned
        mass_option = MassOptions(ppm, ToleranceUnits.ppm)

        scan_selector = ScanSelector(RawFile, polarity, t_min, t_max)
        runtime.logger.debug(
            f"Selected {len(scan_selector.scan_indices_1based)} scans "
            "for sum signal computation. "
            f"Polarity: {polarity}, binning ppm: {ppm}."
        )
        average_scan = Extensions.AverageScans(
            RawFile, scan_selector.scan_indices_dotnet, mass_option
        )
        averaged_spec = average_scan.SegmentedScan

        # Extract averaged signal, multiply by number of combined scans
        # to restore sum signal.
        num_of_combined_scans = average_scan.ScansCombined
        mz = np.frombuffer(averaged_spec.Positions)
        sum_signal = np.frombuffer(averaged_spec.Intensities) * num_of_combined_scans

        sum_signal_dask = da.from_array(sum_signal, chunks="auto")
        sum_signal = xr.DataArray(
            data=sum_signal_dask, dims=["mz"], coords={"mz": mz}, name="sum_signal"
        )

        return sum_signal, num_of_combined_scans


def get_tic_per_scan(
    datafile_path: str,
    timestamps: Iterable[float] | None = None,
    polarity: Literal["+", "-"] | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Allows filtering by timestamps and polarity.
    If timestamps are provided, the function will return the TIC
    values for the closest scan to each timestamp.

    :param datafile_path: Path to the Thermo Fisher raw file (.raw) containing the data.
    :type datafile_path: str
    :param timestamps: Optional iterable of timestamps [s] to
                       extract TIC values for, defaults to None
    :type timestamps: Iterable[float], optional
    :param polarity: + or -, Polarity of the scans to be retrieved,
                     optional, defaults to None
    :type polarity: str, optional
    :return: Tuple containing the scan timestamps [s] and TIC values as numpy arrays
    :rtype: tuple
    """
    with RawFileManager(datafile_path) as RawFile:
        scan_selector = ScanSelector(RawFile, polarity=polarity)
        scan_timestamp = scan_selector.scan_times  # already in seconds

        scan_tic = np.asarray(
            [
                RawFile.GetScanStatsForScanNumber(i).TIC
                for i in scan_selector.scan_indices_1based
            ],
            dtype=np.float64,
        )

        if timestamps is not None:
            requested_timestamps = np.asarray(list(timestamps), dtype=np.float64)

            if requested_timestamps.size == 0:
                return requested_timestamps, requested_timestamps

            # Find nearest scan index for each requested timestamp
            right_idx = np.searchsorted(scan_timestamp, requested_timestamps)
            right_idx = np.clip(right_idx, 0, len(scan_timestamp) - 1)
            left_idx = np.clip(right_idx - 1, 0, len(scan_timestamp) - 1)

            left_distance = np.abs(requested_timestamps - scan_timestamp[left_idx])
            right_distance = np.abs(scan_timestamp[right_idx] - requested_timestamps)
            nearest_idx = np.where(left_distance <= right_distance, left_idx, right_idx)

            scan_timestamp = scan_timestamp[nearest_idx]
            scan_tic = scan_tic[nearest_idx]

        return scan_timestamp, scan_tic


def get_scan_timestamps(
    datafile_path: str,
    t_min: float | None = None,
    t_max: float | None = None,
    polarity: Literal["+", "-"] | None = None,
) -> np.ndarray:
    """Extracts the scan timestamps [s] from the raw file,
    with optional polarity and time filtering.

    :param datafile_path: Path to the Thermo Fisher raw file (.raw) containing the data.
    :type datafile_path: str
    :param t_min: Minimum time [s], optional, defaults to None
    :type t_min: float
    :param t_max: Maximum time [s], optional, defaults to None
    :type t_max: float
    :param polarity: Polarity of the scans to be retrieved,
                     either '+' or '-', optional, defaults to None
    :type polarity: str
    :return: Array of filtered scan timestamps [s]
    :rtype: np.ndarray
    """
    with RawFileManager(datafile_path) as RawFile:
        return ScanSelector(
            RawFile, polarity=polarity, t_min=t_min, t_max=t_max
        ).scan_times


def get_peak_timeseries(
    datafile_path: str,
    mzs: Iterable[float],
    t_min: float | None = None,
    t_max: float | None = None,
    polarity: Literal["+", "-"] | None = None,
    ppm: float = 5,
) -> xr.DataArray:
    """Extracts the peak timeseries for the specified m/z values
    in the time range (t_min, t_max).

    :param datafile_path: Path to the Thermo Fisher raw file (.raw) containing the data.
    :type datafile_path: str
    :param mzs: array of m/z values for which peak timeseries are required.
    :type mzs: float
    :param t_min: Start time [s], optional, defaults to None
    :type t_min: float
    :param t_max: End time [s], optional, defaults to None
    :type t_max: float
    :param polarity: + or -, Polarity of the scans to be retrieved,
                     optional, defaults to None
    :type polarity: str
    :param ppm: Mass tolerance in parts-per-million for centroid binning, defaults to 5.
    :type ppm: float, optional
    :return: An xarray DataArray containing the peak timeseries
    :rtype: xr.DataArray
    """
    mzs = np.asarray(mzs, dtype=float)

    with RawFileManager(datafile_path) as RawFile:
        scan_selector = ScanSelector(
            RawFile, polarity=polarity, t_min=t_min, t_max=t_max
        )
        indices_0based = scan_selector.scan_indices_0based

        # Preallocate the array for intensities
        intensities_for_mz_values = np.zeros(
            (len(mzs), len(indices_0based)), dtype=np.float64
        )

        # Precompute the mass ranges for each m/z value
        mz_lows = mzs - (mzs * ppm / 1e6)
        mz_highs = mzs + (mzs * ppm / 1e6)

        settings = []
        for i, (mz_low, mz_high) in enumerate(zip(mz_lows, mz_highs)):
            mz_range = Range()
            mz_range.Low = mz_low
            mz_range.High = mz_high

            setting = ChromatogramTraceSettings(TraceType.MassRange)
            setting.MassRanges = [mz_range]
            settings.append(setting)

        # Get timeseries for the m/z values, -1 for all scans
        chromatogram = RawFile.GetChromatogramData(settings, -1, -1)
        traces = ChromatogramSignal.FromChromatogramData(chromatogram)

        for i, trace in enumerate(traces):
            intensities_for_mz_values[i] = np.fromiter(
                trace.Intensities, dtype=np.float64, count=len(trace.Intensities)
            )[indices_0based]

        peak_timeseries_dask = da.from_array(intensities_for_mz_values, chunks="auto")

        return xr.DataArray(
            peak_timeseries_dask,
            dims=("mz", "time"),
            coords={"mz": mzs, "time": np.array(scan_selector.scan_times)},
            name="signal",
        )


def _average_scans_centroids(
    RawFile: RawFileReaderAdapter,
    scan_indices_1based: list[int],
    ppm: int = 1,
    average: bool = False,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Average scans and extract centroid data.

    A helper that averages the given scans using Thermo's
    ppm-based binning and returns the centroided peaks. Does not perform
    file I/O or scan selection - the caller is responsible for providing an
    already-open RawFile and the desired scan indices.

    :param RawFile: An already-open RawFileReaderAdapter instance.
    :type RawFile: RawFileReaderAdapter
    :param scan_indices_1based: 1-based scan indices to average.
    :type scan_indices_1based: list[int]
    :param ppm: Mass tolerance in parts-per-million for centroid binning, defaults to 1.
    :type ppm: int, optional
    :param average: If True, return averaged intensities; if False,
                    scale by number of scans.
    :type average: bool, optional
    :return: Tuple of (masses, intensities, resolutions, signal_to_noise) arrays.
    :rtype: tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]
    """
    if ppm <= 0:
        raise ValueError(f"Invalid ppm value: {ppm}. ppm must be > 0.")

    dotnet_indices = List[int]()
    for index in scan_indices_1based:
        dotnet_indices.Add(index)

    mass_option = MassOptions(ppm, ToleranceUnits.ppm)
    average_scan = Extensions.AverageScans(RawFile, dotnet_indices, mass_option)
    averaged_centroids = average_scan.CentroidScan.GetLabelPeaks()
    n_centroids = len(averaged_centroids)

    masses = np.fromiter(
        (c.Mass for c in averaged_centroids),
        dtype=np.float64,
        count=n_centroids,
    )
    intensities = np.fromiter(
        (c.Intensity for c in averaged_centroids),
        dtype=np.float64,
        count=n_centroids,
    )
    resolutions = np.fromiter(
        (c.Resolution for c in averaged_centroids),
        dtype=np.float64,
        count=n_centroids,
    )
    signal_to_noise = np.fromiter(
        (c.SignalToNoise for c in averaged_centroids),
        dtype=np.float64,
        count=n_centroids,
    )

    if not average:
        intensities *= average_scan.ScansCombined

    return masses, intensities, resolutions, signal_to_noise


def get_centroids(
    datafile_path: str,
    t_min: float | None = None,
    t_max: float | None = None,
    average: bool = False,
    ppm: int = 1,
    polarity: Literal["+", "-"] | None = None,
) -> tuple:
    """
    Extract centroided peaks from a Thermo Fisher raw file
    within a specified time range and for specified m/z values.

    This function reads the centroided spectrum by averaging
    scans in the given time window and optionally filtering
    by polarity. The function returns the filtered centroid
    m/z values, their intensities, and resolutions.

    :param datafile_path: Path to the Thermo Fisher raw file (.raw) containing the data.
    :type datafile_path: str
    :param t_min: Minimum time [s] for scan selection,
                  optional, defaults to None (start of run).
    :type t_min: float | None, optional
    :param t_max: Maximum time [s] for scan selection,
                  optional, defaults to None (end of run).
    :type t_max: float | None, optional
    :param average: If True, return averaged intensities; if False,
                    scale intensities by number of scans.
    :type average: bool, optional
    :param ppm: Mass tolerance in parts-per-million for centroid binning, defaults to 1.
    :type ppm: int, optional
    :param polarity: Polarity of scans to use ('+' or '-'),
                     optional, defaults to None (all polarities).
    :type polarity: Literal['+', '-'], optional
    :return: Tuple of (masses, intensities, resolutions,
             signal-to-noise ratios) for centroid peaks matching
             the criteria.
    :rtype: tuple of np.ndarray
    """
    with RawFileManager(datafile_path) as RawFile:
        scan_selector = ScanSelector(
            RawFile,
            polarity=polarity,
            t_min=t_min,
            t_max=t_max,
        )
        return _average_scans_centroids(
            RawFile, scan_selector.scan_indices_1based, ppm=ppm, average=average
        )


def get_centroids_per_scan(
    datafile_path: str,
    t_min: float | None = None,
    t_max: float | None = None,
    mz_min: float | None = None,
    mz_max: float | None = None,
    polarity: Literal["+", "-"] | None = None,
    scan_type: Literal["Ms", "Ms2"] | None = None,
) -> list[dict[str, np.ndarray]]:
    """Reads centroided peaks from a Thermo Fisher raw file
    within a specified time range and m/z range.

    t_min=None is equal to min scan time, t_max=None is equal to max scan time.
    mz_min=None is equal to min m/z, mz_max=None is equal to max m/z.

    :param datafile_path: Path to the Thermo Fisher raw file (.raw) containing the data.
    :type datafile_path: str
    :param t_min: Minimum time [s], optional, defaults to None
    :type t_min: float
    :param t_max: Maximum time [s], optional, defaults to None
    :type t_max: float
    :param mz_min: Minimum m/z, optional, defaults to None
    :type mz_min: float
    :param mz_max: Maximum m/z, optional, defaults to None
    :type mz_max: float
    :param polarity: + or -, Polarity of the scans to be retrieved,
                     optional, defaults to None
    :type polarity: str
    :param scan_type: Filter by scan type ('Ms' or 'Ms2'),
                      optional, defaults to None (all scans)
    :type scan_type: str
    :return: List of dictionaries, each containing per-scan
             centroid masses, intensities, resolutions,
             signal-to-noise ratios, and timestamps.
    :rtype: list[dict[str, np.ndarray]]
    """
    with RawFileManager(datafile_path) as RawFile:
        mz_min, mz_max = _validate_mz_range(RawFile, mz_min, mz_max)
        scan_selector = ScanSelector(
            RawFile,
            polarity=polarity,
            t_min=t_min,
            t_max=t_max,
            ms_type=scan_type,
        )

        centroids = []
        for scan, timestamp in zip(scan_selector.scans, scan_selector.scan_times):
            centroid_scan = scan.CentroidScan

            if centroid_scan is None or centroid_scan.Length == 0:
                masses = np.array([], dtype=np.float64)
                intensities = np.array([], dtype=np.float64)
                resolutions = np.array([], dtype=np.float64)
                signal_to_noise = np.array([], dtype=np.float64)
            else:
                scan_centroids = centroid_scan.GetLabelPeaks()
                n_centroids = len(scan_centroids)

                masses = np.fromiter(
                    (c.Mass for c in scan_centroids),
                    dtype=np.float64,
                    count=n_centroids,
                )
                intensities = np.fromiter(
                    (c.Intensity for c in scan_centroids),
                    dtype=np.float64,
                    count=n_centroids,
                )
                resolutions = np.fromiter(
                    (c.Resolution for c in scan_centroids),
                    dtype=np.float64,
                    count=n_centroids,
                )
                signal_to_noise = np.fromiter(
                    (c.SignalToNoise for c in scan_centroids),
                    dtype=np.float64,
                    count=n_centroids,
                )

                mz_mask = np.logical_and(mz_min <= masses, masses <= mz_max)
                masses = masses[mz_mask]
                intensities = intensities[mz_mask]
                resolutions = resolutions[mz_mask]
                signal_to_noise = signal_to_noise[mz_mask]

            centroids.append(
                {
                    "masses": masses,
                    "intensities": intensities,
                    "resolutions": resolutions,
                    "signal_to_noise": signal_to_noise,
                    "timestamp": timestamp,
                }
            )

        return centroids


def _group_ms2_scans_by_parent(
    scan_selector: ScanSelector,
    parent_peak_tolerance: float = 0.001,
) -> dict[float, list[int]]:
    """Group MS2 scans by their parent peak m/z.

    Parses each MS2 scan filter to extract the precursor m/z, clusters
    near-duplicate values within tolerance, and returns a mapping of
    canonical parent peak m/z to 1-based scan indices.

    :param scan_selector: A ScanSelector already filtered for MS2 scans.
    :type scan_selector: ScanSelector
    :param parent_peak_tolerance: Tolerance in Da for merging
                                  near-duplicate parent peaks.
    :type parent_peak_tolerance: float
    :return: Mapping of canonical parent peak m/z to list of 1-based scan indices.
    :rtype: dict[float, list[int]]
    """
    scan_parent_peaks: list[tuple[int, float]] = []
    for scan_idx, scan_filter in zip(
        scan_selector.scan_indices_1based, scan_selector.raw_scan_filters
    ):
        match = re.search(r"ms2 ([\d.]+)@", scan_filter.ToString())
        if match:
            scan_parent_peaks.append((scan_idx, float(match.group(1))))

    if not scan_parent_peaks:
        return {}

    raw_parent_peaks = np.array([pp for _, pp in scan_parent_peaks])
    sorted_unique = np.sort(np.unique(raw_parent_peaks))

    clusters: list[list[float]] = []
    for value in sorted_unique:
        if clusters and (value - clusters[-1][-1]) <= parent_peak_tolerance:
            clusters[-1].append(value)
        else:
            clusters.append([value])

    clustered_parent_peaks = [round(float(np.median(c)), 4) for c in clusters]

    parent_peak_mapping: dict[float, list[int]] = {
        pp: [] for pp in clustered_parent_peaks
    }
    for scan_idx, raw_pp in scan_parent_peaks:
        for clustered_pp in clustered_parent_peaks:
            if abs(raw_pp - clustered_pp) <= parent_peak_tolerance:
                parent_peak_mapping[clustered_pp].append(scan_idx)
                break

    return parent_peak_mapping


def get_ms2_centroids_by_parent(
    datafile_path: str,
    t_min: float | None = None,
    t_max: float | None = None,
    polarity: Literal["+", "-"] | None = None,
    parent_peak_tolerance: float = 0.001,
    ppm: int = 1,
    average: bool = True,
) -> dict[float, tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]]:
    """Extract averaged centroids for each parent peak in an MS2 raw file.

    Opens the raw file once, groups MS2 scans by parent peak, and averages
    each group using Thermo's native ppm-based binning.

    :param datafile_path: Path to the Thermo Fisher raw file (.raw).
    :type datafile_path: str
    :param t_min: Minimum time [s], optional.
    :type t_min: float | None, optional
    :param t_max: Maximum time [s], optional.
    :type t_max: float | None, optional
    :param polarity: Polarity filter ('+' or '-'), optional.
    :type polarity: Literal['+', '-'] | None, optional
    :param parent_peak_tolerance: Tolerance in Da for merging parent peaks.
    :type parent_peak_tolerance: float
    :param ppm: Mass tolerance in ppm for centroid binning, defaults to 1.
    :type ppm: int, optional
    :param average: If True, return averaged intensities; if False,
                    scale by scan count.
    :type average: bool, optional
    :return: Mapping of parent peak m/z to
             (masses, intensities, resolutions, signal_to_noise).
    :rtype: dict[float, tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]]
    """
    with RawFileManager(datafile_path) as RawFile:
        scan_selector = ScanSelector(
            RawFile, polarity=polarity, t_min=t_min, t_max=t_max, ms_type="Ms2"
        )

        parent_peak_mapping = _group_ms2_scans_by_parent(
            scan_selector, parent_peak_tolerance
        )
        if not parent_peak_mapping:
            return {}

        centroid_mapping: dict[
            float, tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]
        ] = {}
        for pp, scan_indices in parent_peak_mapping.items():
            if not scan_indices:
                centroid_mapping[pp] = (
                    np.array([], dtype=np.float64),
                    np.array([], dtype=np.float64),
                    np.array([], dtype=np.float64),
                    np.array([], dtype=np.float64),
                )
                continue
            centroid_mapping[pp] = _average_scans_centroids(
                RawFile, scan_indices, ppm=ppm, average=average
            )

        return centroid_mapping


class RawFileMetadata:
    """Class to access metadata of a Thermo Fisher raw file."""

    def __init__(
        self,
        datafile_path: str,
        t_min: float | None = None,
        t_max: float | None = None,
        polarity: Literal["+", "-"] | None = None,
        scan_type: Literal["Ms", "Ms2"] | None = "Ms",
        **kwargs,
    ):
        self.datafile_path = datafile_path
        self.t_min = t_min
        self.t_max = t_max
        self.polarity = polarity
        self.scan_type = scan_type

    @property
    def instrument_details(self) -> dict:
        """Information about the instrument used for the acquisition.
        ChannelLabels and Units are not included as they are not serializable.
        """
        with RawFileManager(self.datafile_path) as RawFile:
            instrument_data = RawFile.GetInstrumentData()

            instrument_data_list = [
                "Name",
                "Model",
                "SerialNumber",
                "SoftwareVersion",
                "HardwareVersion",
                "Flags",
                "AxisLabelX",
                "AxisLabelY",
                "IsValid",
                "HasAccurateMassPrecursors",
            ]

            return {row: getattr(instrument_data, row) for row in instrument_data_list}

    @property
    def scan_acquisition_settings(self) -> dict:
        """Acquisition settings for each scan (injection time, AGC target,
        isolation width, HCD energy, lock-mass info, etc.)
        """
        with RawFileManager(self.datafile_path) as RawFile:
            scan_selector = ScanSelector(
                RawFile, self.polarity, self.t_min, self.t_max, self.scan_type
            )
            settings_dict = {}
            header_labels = None
            for i in scan_selector.scan_indices_1based:
                header = RawFile.GetTrailerExtraInformation(i)
                if header_labels is None:
                    header_labels = list(header.Labels)
                settings_dict[i] = list(header.Values)

            return {
                "header_labels": header_labels,
                "settings": settings_dict,
            }

    @property
    def scan_statistics(self) -> dict:
        """Get per scan statistics"""
        with RawFileManager(self.datafile_path) as RawFile:
            scan_selector = ScanSelector(
                RawFile, self.polarity, self.t_min, self.t_max, self.scan_type
            )
            stat_names = [
                "HighMass",
                "LowMass",
                "LongWavelength",
                "ShortWavelength",
                "BasePeakIntensity",
                "BasePeakMass",
                "TIC",
                "StartTime",
                "PacketCount",
                "NumberOfChannels",
                "ScanNumber",
                "ScanEventNumber",
                "SegmentNumber",
                "IsCentroidScan",
                "Frequency",
                "IsUniformTime",
                "AbsorbanceUnitScale",
                "WavelengthStep",
                "ScanType",
                "CycleNumber",
            ]
            # The scan type is not included in the scan statistics,
            # so we need to get it from the raw scan filters
            return {
                scan_index: {
                    **{
                        name: getattr(
                            scan_selector.raw_scan_stats[scan_index - 1], name
                        )
                        for name in stat_names
                    },
                    "MsType": scan_selector.raw_scan_filters[
                        scan_index - 1
                    ].MSOrder.ToString(),
                }
                for scan_index in scan_selector.scan_indices_1based
            }


class RawFileMetadataLegacy(RawFileMetadata):
    """Class to access metadata of a Thermo Fisher raw file."""

    @property
    def num_of_scans(self):
        """Number of scans in the raw file."""
        with RawFileManager(self.datafile_path) as RawFile:
            return RawFile.RunHeaderEx.SpectraCount

    @property
    def instrument(self):
        instrument_dict = self.instrument_details
        instrument_df = pd.DataFrame.from_dict(
            instrument_dict, orient="index", columns=["Value"]
        )
        return instrument_df

    @property
    def trailer(self):
        """Trailer information of the raw file"""
        trailer_data = self.scan_acquisition_settings
        trailer_dict = trailer_data["settings"]
        header_labels = trailer_data["header_labels"]

        trailer_df = pd.DataFrame.from_dict(trailer_dict, orient="columns")
        trailer_df.set_index(pd.Index(header_labels), inplace=True)
        return trailer_df

    @property
    def statistics(self):
        """Scan statistics of the raw file"""
        scan_stats = self.scan_statistics
        return pd.DataFrame.from_dict(scan_stats, orient="columns")

    @property
    def centroids_meta(self):
        """
        Returns a dictionary with centroided peak data for each scan.

        Structure:
        {
            "time": [...],  # list of scan times [s]
            "data": [
                {
                    "intensities": ...,
                    "mzs": ...,
                    "resolutions": ...,
                    "noises": ...
                    }
                    ...
                ],
                ...
            }
        }
        """
        result = {"time": [], "data": []}
        with RawFileManager(self.datafile_path) as RawFile:
            scan_selector = ScanSelector(RawFile, ms_type=None)
            scans = scan_selector.scans
            scan_times = scan_selector.scan_times
            for timestamp, scan in zip(scan_times, scans):
                centroid_scan = scan.CentroidScan
                if centroid_scan is not None and centroid_scan.Length > 0:
                    mzs = np.frombuffer(centroid_scan.Masses)
                    intensities = np.frombuffer(centroid_scan.Intensities)
                    resolutions = np.frombuffer(centroid_scan.Resolutions)
                    noises = np.frombuffer(centroid_scan.Noises)

                    valid_resolution_mask = np.isfinite(resolutions) & (resolutions > 0)
                    valid_intensity_mask = np.isfinite(intensities) & (intensities > 0)
                    valid_mask = valid_resolution_mask & valid_intensity_mask

                    mzs = mzs[valid_mask].tolist()
                    intensities = intensities[valid_mask].tolist()
                    resolutions = resolutions[valid_mask].tolist()
                    noises = noises[valid_mask].tolist()
                else:
                    mzs = []
                    intensities = []
                    resolutions = []
                    noises = []
                result["time"].append(timestamp)
                result["data"].append(
                    {
                        "intensities": intensities,
                        "mzs": mzs,
                        "resolutions": resolutions,
                        "noises": noises,
                    }
                )
        return result

    def to_dict(self):
        """Convert the metadata to a dictionary.

        The dictionary contains the number of scans, statistics per scan, and statistics
        per file. The statistics per scan and per file are represented as dictionaries.
        """
        # Concat scan-related data into a single dataframe
        per_scan_df = pd.concat([self.statistics, self.trailer], axis=0)
        # Merge per file data into a single dataframe (we currently have only one file)
        per_file_df = self.instrument

        return {
            "num_of_scans": self.num_of_scans,
            "stats_per_scan": per_scan_df.to_dict(),
            "stats_per_file": per_file_df.to_dict(),
            "centroids_meta": self.centroids_meta,
        }
