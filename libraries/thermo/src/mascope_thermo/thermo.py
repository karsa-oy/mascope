"""
This module provides functions to read and process Thermo Fisher raw files.

Where it's applicable, the scans are first filtered by polarity then by time range.

There may be a confusion with indices since the Thermo library uses 1-based indexing,
while Python uses 0-based indexing. scan_indices are 1-based, while scan_indices_python are 0-based.
"""

from pathlib import Path
from itertools import compress
from contextlib import contextmanager
from typing import Iterable, Literal

import pandas as pd
import numpy as np
import xarray as xr
import dask.array as da

from ThermoFisher.CommonCore.RawFileReader import RawFileReaderAdapter
from ThermoFisher.CommonCore.Data.Business import (
    Device,
    MassOptions,
    ChromatogramSignal,
    ChromatogramTraceSettings,
    TraceType,
    Range,
)
from ThermoFisher.CommonCore.Data import ToleranceUnits, Extensions

from System.Collections.Generic import List

from mascope_thermo.runtime import runtime


@contextmanager
def open_raw_file(datafile_path: str):
    """Context manager for safely opening and closing Thermo raw-files.

    :param datafile_path: Path to the Thermo Fisher raw file (.raw) containing the data.
    :type datafile_path: str
    :yield: RawFile object
    :rtype: ThermoFisher.CommonCore.Data.Interfaces.IRawDataExtended
    """
    try:
        raw_file = RawFileReaderAdapter.FileFactory(datafile_path)
        try:
            # Default configurations
            raw_file.SelectInstrument(Device.MS, 1)
            raw_file.IncludeReferenceAndExceptionData = True

            yield raw_file
        finally:
            # Ensure file is always closed
            if raw_file is not None:
                raw_file.Dispose()
    except Exception as e:
        runtime.logger.error(f"Failed to open the file {Path(datafile_path).name}: {e}")


def get_polarity_options(datafile_path: str) -> str:
    """Reads the polarities present in a raw file.

    :param datafile_path: Path to the Thermo Fisher raw file (.raw) containing the data.
    :type datafile_path: str
    :return: "-" if only negative polarities are present, "+" if only positive, "+-" if both are present.
    :rtype: str
    """
    with open_raw_file(datafile_path) as raw_file:
        num_of_scans = raw_file.RunHeaderEx.SpectraCount
        scan_indices = list(range(1, num_of_scans + 1))

        polarities = set(
            raw_file.GetFilterForScanNumber(i).Polarity.ToString() for i in scan_indices
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
            raise ValueError("No valid polarities found in the raw file.")


def filter_by_polarity(
    raw_file, scan_indices: list, polarity: Literal["+", "-"]
) -> list:
    """Filter scan indices by polarity. Can be used to verify if the specified polarity is available in the raw file.

    :param raw_file: The raw file object containing scan data.
    :type raw_file: ThermoFisher.CommonCore.Data.Interfaces.IRawDataExtended
    :param scan_indices: List of scan indices to filter.
    :type scan_indices: list
    :param polarity: Polarity of the scans to be retrieved, either '+' or '-'.
    :type polarity: str
    :return: List of scan indices that match the specified polarity.
    :rtype: list
    """
    if polarity not in ["-", "+"]:
        raise ValueError(
            f"Invalid polarity '{polarity}' provided. Polarity must be '+' or '-'."
        )
    # Convert polarity to the format used in the raw file
    polarity = "Negative" if polarity == "-" else "Positive"

    polarity_mask = [
        raw_file.GetFilterForScanNumber(i).Polarity.ToString() == polarity
        for i in scan_indices
    ]
    scan_indices = list(compress(scan_indices, polarity_mask))

    if not scan_indices:
        raise ValueError(f"{polarity} polarity not found in the raw file.")

    return scan_indices


def filter_by_time(raw_file, scan_indices: list, t_min: float, t_max: float) -> tuple:
    """Filter scan indices by time range.

    :param raw_file: The raw file object containing scan data.
    :type raw_file: ThermoFisher.CommonCore.Data.Interfaces.IRawDataExtended
    :param scan_indices: List of scan indices to filter.
    :type scan_indices: list
    :param t_min: Minimum time [s].
    :type t_min: float
    :param t_max: Maximum time [s].
    :type t_max: float
    :return: Tuple of filtered scan indices and corresponding scan times.
    :rtype: tuple
    """
    # Set default time range if not provided
    t_min = raw_file.RunHeaderEx.StartTime * 60 if t_min is None else t_min
    t_max = raw_file.RunHeaderEx.EndTime * 60 if t_max is None else t_max

    if t_min > t_max:
        raise ValueError(f"Invalid time range: {t_min:.1f} s > {t_max:.1f} s")

    scan_time = [
        raw_file.GetScanStatsForScanNumber(i).StartTime * 60 for i in scan_indices
    ]  # [s]

    # Create a mask for scan times within the specified range
    # Using epsilon to avoid floating point precision issues
    epsilon = np.finfo(np.float64).eps * max(scan_time)
    time_mask = [(t_min - epsilon) <= t <= (t_max + epsilon) for t in scan_time]
    # Filter scan indices
    scan_indices = list(compress(scan_indices, time_mask))

    if not scan_indices:
        raise ValueError(
            f"""No data found in the specified time range for the chosen polarity.
                Accepted time range: {min(scan_time):.1f} - {max(scan_time):.1f} s.
                """
        )

    # Update time scale
    scan_time = list(compress(scan_time, time_mask))
    return scan_indices, scan_time


def get_signal(
    datafile_path: str,
    t_min: float | None = None,
    t_max: float | None = None,
    mz_min: float | None = None,
    mz_max: float | None = None,
    polarity: Literal["+", "-"] | None = None,
) -> xr.Dataset:
    """This function uses the Thermo Fisher libraries to read the raw file and extract the scan data.
    It then merges the scans to have a common m/z scale and converts the data to an xarray Dataset.
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
    :param polarity: + or -, Polarity of the scans to be retrieved, optional, defaults to None
    :type polarity: str
    :return: An xarray Dataset containing the signal data
    :rtype: xr.Dataset
    """
    with open_raw_file(datafile_path) as raw_file:
        mz_min = raw_file.RunHeaderEx.LowMass if mz_min is None else mz_min
        mz_max = raw_file.RunHeaderEx.HighMass if mz_max is None else mz_max
        if mz_min > mz_max:
            raise ValueError(
                f"Invalid m/z range: mz_min={mz_min}, mz_max={mz_max}, where mz_min > mz_max"
            )

        num_of_scans = raw_file.RunHeaderEx.SpectraCount
        scan_indices = list(range(1, num_of_scans + 1))
        scans = tuple(Extensions.GetScans(raw_file, 1, num_of_scans))

        if polarity:
            scan_indices = filter_by_polarity(raw_file, scan_indices, polarity)

        scan_indices, scan_time = filter_by_time(raw_file, scan_indices, t_min, t_max)

        # Extract scan spectra and m/z values
        scan_mzs, scan_specs = [], []
        for i in scan_indices:
            intensities = np.frombuffer(scans[i - 1].SegmentedScan.Intensities)
            positions = np.frombuffer(scans[i - 1].SegmentedScan.Positions)

            # Filter by m/z range
            mz_mask = np.logical_and(mz_min <= positions, positions <= mz_max)
            scan_specs.append(intensities[mz_mask])
            scan_mzs.append(positions[mz_mask])

        if not scan_mzs:
            raise ValueError(
                f"""No data found in the specified m/z range.
                M/z range of the raw file: {raw_file.RunHeaderEx.LowMass} - {raw_file.RunHeaderEx.HighMass}
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


def compute_sum_signal_in_time_range(
    datafile_path: str,
    t_min: float | None = None,
    t_max: float | None = None,
    average: bool = False,
    ppm: int = 1,
    polarity: Literal["+", "-"] | None = None,
) -> xr.core.dataarray.DataArray:
    """Computes sum signal in (t_min, t_max) time range, binning counts within "ppm" value.
    Polarity filter may be optionally provided.

    :param datafile_path: Path to the Thermo Fisher raw file (.raw) containing the data.
    :type datafile_path: str
    :param t_min: Start time [s]
    :type t_min: float, optional
    :param t_max: End time [s]
    :type t_max: float, optional
    :param average: If spectrum should be averaged, defaults to False
    :type average: bool, optional
    :param ppm: ppm precision for binning, defaults to 1. This value determines the mass tolerance for grouping m/z values,
                where a smaller ppm value results in finer binning and higher precision.
    :type ppm: int, optional
    :param polarity: + or -, Polarity of the scans to be retrieved, optional, defaults to None
    :type polarity: str, optional
    :raises ValueError: If the specified time range is invalid, or if no data is found in the specified filters,
                        or the specified polarity is not found in the raw file.
    :return: Sum signal in the specified time range for specified polarity as an xarray DataArray.
    :rtype: xr.core.dataarray.DataArray
    """
    with open_raw_file(datafile_path) as raw_file:
        num_of_scans = raw_file.RunHeaderEx.SpectraCount
        scan_indices = list(range(1, num_of_scans + 1))

        if polarity:
            scan_indices = filter_by_polarity(raw_file, scan_indices, polarity)

        scan_indices, _ = filter_by_time(raw_file, scan_indices, t_min, t_max)
        runtime.logger.debug(
            f"Computing sum signal for {len(scan_indices)} scans in time range ({t_min}, {t_max}) s"
        )

        # Setup mz tolerance - counts within ppm are binned
        mass_option = MassOptions(ppm, ToleranceUnits.ppm)

        # Get averaged spectrum in time range (t_max, t_max)
        net_scan_indices = List[int]()
        for index in scan_indices:
            net_scan_indices.Add(index)
        average_scan = Extensions.AverageScans(raw_file, net_scan_indices, mass_option)
        averaged_spec = average_scan.SegmentedScan

        # Extract averaged signal, multiply by num_of_scans to restore sum signal
        mz = np.frombuffer(averaged_spec.Positions)
        sum_signal = np.frombuffer(averaged_spec.Intensities)

        if not average:
            # Multiply by number of averaged scans
            sum_signal *= average_scan.ScansCombined

        # Convert sum signal to dask array
        sum_signal_dask = da.from_array(sum_signal, chunks="auto")

        # Convert to xarray.DataArray
        return xr.DataArray(
            data=sum_signal_dask, dims=["mz"], coords={"mz": mz}, name="sum_signal"
        )


def get_tic_per_scan(
    datafile_path: str,
    timestamps: Iterable[float] | None = None,
    polarity: Literal["+", "-"] | None = None,
) -> tuple:
    """
    Allows filtering by timestamps and polarity.
    If timestamps are provided, the function will return the TIC values for the closest scan to each timestamp.

    :param datafile_path: Path to the Thermo Fisher raw file (.raw) containing the data.
    :type datafile_path: str
    :param timestamps: Optional iterable of timestamps [s] to extract TIC values for, defaults to None
    :type timestamps: Iterable[float], optional
    :param polarity: + or -, Polarity of the scans to be retrieved, optional, defaults to None
    :type polarity: str, optional
    :return: Tuple containing the scan timestamps [s] and TIC values as numpy arrays
    :rtype: tuple
    """
    with open_raw_file(datafile_path) as raw_file:
        num_of_scans = raw_file.RunHeaderEx.SpectraCount
        scan_indices = list(range(1, num_of_scans + 1))

        scan_statistics = [raw_file.GetScanStatsForScanNumber(i) for i in scan_indices]
        scan_tic = np.asarray([scan_stat.TIC for scan_stat in scan_statistics])
        scan_timestamp = np.asarray(
            [scan_stat.StartTime for scan_stat in scan_statistics]
        )

        if polarity:
            scan_indices = filter_by_polarity(raw_file, scan_indices, polarity)
            scan_indices_python = [i - 1 for i in scan_indices]
            scan_tic = scan_tic[scan_indices_python]
            scan_timestamp = scan_timestamp[scan_indices_python]

        if timestamps:
            # Filter TIC values by timestamps
            timestamps = np.asarray(timestamps)
            # Find closest scan index for each timestamp
            scan_indices_python = np.searchsorted(scan_timestamp, timestamps)
            # Ensure indices are within valid range
            scan_indices_python = np.clip(
                scan_indices_python, 0, len(scan_timestamp) - 1
            )
            # Extract scan TIC and scan timestamps values for the closest scan index
            scan_tic = scan_tic[scan_indices_python]
            scan_timestamp = scan_timestamp[scan_indices_python]

        # Convert timestamp from minutes to seconds
        scan_timestamp = scan_timestamp * 60

        return scan_timestamp, scan_tic


def get_scan_timestamps(
    datafile_path: str,
    t_min: float | None = None,
    t_max: float | None = None,
    polarity: Literal["+", "-"] | None = None,
) -> np.ndarray:
    """Extracts the scan timestamps [s] from the raw file, with optional polarity and time filtering.

    :param datafile_path: Path to the Thermo Fisher raw file (.raw) containing the data.
    :type datafile_path: str
    :param t_min: Minimum time [s], optional, defaults to None
    :type t_min: float
    :param t_max: Maximum time [s], optional, defaults to None
    :type t_max: float
    :param polarity: Polarity of the scans to be retrieved, either '+' or '-', optional, defaults to None
    :type polarity: str
    :return: Array of filtered scan timestamps [s]
    :rtype: np.ndarray
    """
    with open_raw_file(datafile_path) as raw_file:
        num_of_scans = raw_file.RunHeaderEx.SpectraCount
        scan_indices = list(range(1, num_of_scans + 1))

        if polarity:
            scan_indices = filter_by_polarity(raw_file, scan_indices, polarity)

        _, scan_time = filter_by_time(raw_file, scan_indices, t_min, t_max)

        return np.asarray(scan_time)


def get_peak_profiles(
    datafile_path: str,
    mzs: Iterable[float],
    t_min: float | None = None,
    t_max: float | None = None,
    polarity: Literal["+", "-"] | None = None,
    ppm: float = 5,
) -> xr.Dataset:
    """Extracts the peak profiles for the specified m/z values in the time range (t_min, t_max).

    :param datafile_path: Path to the Thermo Fisher raw file (.raw) containing the data.
    :type datafile_path: str
    :param mzs: array of m/z values for which peak profiles are required.
    :type mzs: float
    :param t_min: Start time [s], optional, defaults to None
    :type t_min: float
    :param t_max: End time [s], optional, defaults to None
    :type t_max: float
    :param polarity: + or -, Polarity of the scans to be retrieved, optional, defaults to None
    :type polarity: str
    :param ppm: Mass tolerance in parts-per-million for centroid binning, defaults to 10.
    :type ppm: float, optional
    :return: An xarray Dataset containing the peak profiles
    :rtype: xr.Dataset
    """
    mzs = np.asarray(mzs, dtype=float)

    with open_raw_file(datafile_path) as raw_file:
        num_of_scans = raw_file.RunHeaderEx.SpectraCount
        scan_indices = list(range(1, num_of_scans + 1))

        if polarity:
            scan_indices = filter_by_polarity(raw_file, scan_indices, polarity)

        scan_indices, scan_time = filter_by_time(
            raw_file, scan_indices, t_min, t_max
        )  # [s]

        # Convert scan indices to 0-based for Python
        py_scan_indices = [i - 1 for i in scan_indices]

        # Preallocate the array for intensities
        intensities_for_mz_values = np.zeros(
            (len(mzs), len(py_scan_indices)), dtype=np.float64
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

        # Get profiles for the m/z values, -1 for all scans
        chromatogram = raw_file.GetChromatogramData(settings, -1, -1)
        traces = ChromatogramSignal.FromChromatogramData(chromatogram)

        for i, trace in enumerate(traces):
            # Save the intensities from required scans
            intensities_for_mz_values[i] = np.fromiter(
                trace.Intensities, dtype=np.float64, count=len(trace.Intensities)
            )[py_scan_indices]

        peak_profiles_dask = da.from_array(intensities_for_mz_values, chunks="auto")

        # Export xarray array with time and mz coordinates
        result = xr.DataArray(
            peak_profiles_dask,
            dims=("mz", "time"),
            coords={"mz": mzs, "time": np.array(scan_time)},
            name="signal",
        )

    return result


def get_centroids(
    datafile_path: str,
    u_list: Iterable[float],
    t_min: float | None = None,
    t_max: float | None = None,
    average: bool = False,
    ppm: int = 1,
    polarity: Literal["+", "-"] | None = None,
) -> tuple:
    """
    Extract centroided peaks from a Thermo Fisher raw file within a specified time range and for specified m/z values.

    This function reads the centroided spectrum by averaging scans in the given time window and (optionally) polarity.
    It then selects centroid peaks whose m/z values are within ±0.5 of any value in `u_list`.
    The function returns the filtered centroid m/z values, their intensities, and resolutions.

    :param datafile_path: Path to the Thermo Fisher raw file (.raw) containing the data.
    :type datafile_path: str
    :param u_list: Iterable of m/z values to select centroid peaks near (within ±0.5).
    :type u_list: Iterable[float]
    :param t_min: Minimum time [s] for scan selection, optional, defaults to None (start of run).
    :type t_min: float | None, optional
    :param t_max: Maximum time [s] for scan selection, optional, defaults to None (end of run).
    :type t_max: float | None, optional
    :param average: If True, return averaged intensities; if False, scale intensities by number of scans.
    :type average: bool, optional
    :param ppm: Mass tolerance in parts-per-million for centroid binning, defaults to 1.
    :type ppm: int, optional
    :param polarity: Polarity of scans to use ('+' or '-'), optional, defaults to None (all polarities).
    :type polarity: Literal['+', '-'], optional
    :return: Tuple of (masses, intensities, resolutions, signal-to-noise ratios) for centroid peaks matching the criteria.
    :rtype: tuple of np.ndarray
    """
    with open_raw_file(datafile_path) as raw_file:
        num_of_scans = raw_file.RunHeaderEx.SpectraCount
        scan_indices = list(range(1, num_of_scans + 1))

        if polarity:
            scan_indices = filter_by_polarity(raw_file, scan_indices, polarity)

        scan_indices, _ = filter_by_time(raw_file, scan_indices, t_min, t_max)

        # Setup mz tolerance - counts within ppm are binned
        mass_option = MassOptions(ppm, ToleranceUnits.ppm)

        # Get averaged spectrum in time range (t_max, t_max)
        net_scan_indices = List[int]()
        for index in scan_indices:
            net_scan_indices.Add(index)
        average_scan = Extensions.AverageScans(raw_file, net_scan_indices, mass_option)
        averaged_centroids = average_scan.CentroidScan.GetLabelPeaks()

        masses = np.fromiter(
            (c.Mass for c in averaged_centroids),
            dtype=np.float64,
            count=len(averaged_centroids),
        )
        intensities = np.fromiter(
            (c.Intensity for c in averaged_centroids),
            dtype=np.float64,
            count=len(averaged_centroids),
        )
        resolutions = np.fromiter(
            (c.Resolution for c in averaged_centroids),
            dtype=np.float64,
            count=len(averaged_centroids),
        )
        signal_to_noise = np.fromiter(
            (c.SignalToNoise for c in averaged_centroids),
            dtype=np.float64,
            count=len(averaged_centroids),
        )

        if not average:
            # Multiply by number of averaged scans
            intensities *= average_scan.ScansCombined

        # Create a mask for the masses that are within 0.5 of any value in u_list
        mz_mask = np.zeros_like(masses, dtype=bool)
        for mz in u_list:
            mz_mask |= (masses >= mz - 0.5) & (masses <= mz + 0.5)
        masses = masses[mz_mask]
        intensities = intensities[mz_mask]
        resolutions = resolutions[mz_mask]
        signal_to_noise = signal_to_noise[mz_mask]

        return masses, intensities, resolutions, signal_to_noise


class RawFileMetadata:
    """Class to access metadata of a Thermo Fisher raw file."""

    def __init__(self, datafile_path: str):
        self.datafile_path = datafile_path

    @property
    def num_of_scans(self):
        """Number of scans in the raw file."""
        with open_raw_file(self.datafile_path) as raw_file:
            return raw_file.RunHeaderEx.SpectraCount

    @property
    def instrument(self):
        """Instrument metadata. The following information is available:
        Name
        Model
        SerialNumber
        SoftwareVersion
        HardwareVersion
        Flags
        AxisLabelX
        AxisLabelY
        IsValid
        HasAccurateMassPrecursors
        """
        with open_raw_file(self.datafile_path) as raw_file:
            instrument_data = raw_file.GetInstrumentData()

            instrument_data_list = [
                "Name",
                "Model",
                "SerialNumber",
                "SoftwareVersion",
                "HardwareVersion",
                # "ChannelLabels", not serializable
                # "Units", not serializable
                "Flags",
                "AxisLabelX",
                "AxisLabelY",
                "IsValid",
                "HasAccurateMassPrecursors",
            ]

            instrument_dict = {
                row: getattr(instrument_data, row) for row in instrument_data_list
            }
            instrument_df = pd.DataFrame.from_dict(
                instrument_dict, orient="index", columns=["Value"]
            )
            return instrument_df

    @property
    def trailer(self):
        """Trailer information of the raw file. The following information is available:

        Scan Description
        Multiple Injection
        Multi Inject Info
        AGC
        Micro Scan Count
        Scan Segment
        Scan Event
        Master Index
        Master Scan Number
        Charge State
        Monoisotopic M/Z
        Error in isotopic envelope fit
        Ion Injection Time (ms)
        Max. Ion Time (ms)
        FT Resolution
        MS2 Isolation Width
        MS2 Isolation Offset
        AGC Target
        HCD Energy
        HCD Energy V
        Analyzer Temperature

        === Mass Calibration: ===
        Conversion Parameter B
        Conversion Parameter C
        Temperature Comp. (ppm)
        RF Comp. (ppm)
        Space Charge Comp. (ppm)
        Resolution Comp. (ppm)
        Number of Lock Masses
        Lock Mass #1 (m/z)
        Lock Mass #2 (m/z)
        Lock Mass #3 (m/z)
        LM Search Window (ppm)
        LM Search Window (mmu)
        Number of LM Found
        Last Locking (sec)
        LM m/z-Correction (ppm)

        === Ion Optics Settings: ===
        S-Lens RF Level

        ====  Diagnostic Data:  ====
        Application Mode
        Mild Trapping Mode
        APD
        OT Intens Comp Factor
        Res. Dep. Intens
        Q Trans Comp
        PrOSA NumF
        PrOSA Comp
        PrOSA ScScr
        RawOvFtT
        Dynamic RT Shift (min)
        LC FWHM parameter
        PS Inj. Time (ms)
        AGC PS Mode
        AGC PS Diag
        AGC Target Adjust
        AGC Diag 1
        AGC Diag 2
        HCD abs. Offset
        Source CID eV
        AGC Fill
        Injection t0
        t0 FLP
        Iso Para R
        Inj Para R
        Access Id
        Analog In A (V)
        Analog In B (V)
        FAIMS Attached
        FAIMS Voltage On
        FAIMS CV
        """
        with open_raw_file(self.datafile_path) as raw_file:
            trailer_dict = {}
            header_labels = None
            for i in range(1, self.num_of_scans + 1):
                header = raw_file.GetTrailerExtraInformation(i)
                if header_labels is None:
                    header_labels = list(header.Labels)
                trailer_dict[i] = list(header.Values)

            trailer_df = pd.DataFrame.from_dict(trailer_dict, orient="columns")
            trailer_df.index = header_labels
            return trailer_df

    @property
    def statistics(self):
        """Get per scan statistics:

        HighMass
        LowMass
        LongWavelength
        ShortWavelength
        BasePeakIntensity
        BasePeakMass
        TIC
        StartTime
        PacketCount
        NumberOfChannels
        ScanNumber
        ScanEventNumber
        SegmentNumber
        IsCentroidScan
        Frequency
        IsUniformTime
        AbsorbanceUnitScale
        WavelengthStep
        ScanType
        CycleNumber
        """
        with open_raw_file(self.datafile_path) as raw_file:
            num_of_scans = raw_file.RunHeaderEx.SpectraCount

            scan_statistics = [
                raw_file.GetScanStatsForScanNumber(i)
                for i in range(1, num_of_scans + 1)
            ]

            stat_list = [
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

            scan_stats = dict()
            for i in range(num_of_scans):
                scan_stats[i + 1] = [
                    getattr(scan_statistics[i], stat) for stat in stat_list
                ]

            scan_stats_df = pd.DataFrame.from_dict(scan_stats, orient="columns")
            scan_stats_df.index = stat_list

            return scan_stats_df

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
        with open_raw_file(self.datafile_path) as raw_file:
            num_of_scans = raw_file.RunHeaderEx.SpectraCount
            scans = tuple(Extensions.GetScans(raw_file, 1, num_of_scans))
            for i, scan in enumerate(scans):
                centroid_scan = scan.CentroidScan
                if centroid_scan is not None and centroid_scan.Length > 0:
                    mzs = np.frombuffer(centroid_scan.Masses).tolist()
                    intensities = np.frombuffer(centroid_scan.Intensities).tolist()
                    resolutions = np.frombuffer(centroid_scan.Resolutions).tolist()
                    noises = np.frombuffer(centroid_scan.Noises).tolist()
                else:
                    mzs = []
                    intensities = []
                    resolutions = []
                    noises = []
                scan_time = raw_file.GetScanStatsForScanNumber(i).StartTime * 60
                result["time"].append(scan_time)
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

        The dictionary contains the number of scans, statistics per scan, and statistics per file.
        The statistics per scan and per file are represented as dictionaries.
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
