from pathlib import Path
from itertools import compress
from contextlib import contextmanager
from typing import Iterable, Optional
import numpy as np
import xarray as xr
import dask.array as da
from mascope_hardware.runtime import hardware_runtime

from ThermoFisher.CommonCore.RawFileReader import RawFileReaderAdapter
from ThermoFisher.CommonCore.Data.Business import Device, MassOptions
from ThermoFisher.CommonCore.Data import ToleranceUnits, Extensions
import System


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
        hardware_runtime.logger.error(
            f"Failed to open the file {Path(datafile_path).name}: {e}"
        )


def get_signal(
    datafile_path: str,
    t_min: Optional[float] = None,
    t_max: Optional[float] = None,
    mz_min: Optional[float] = None,
    mz_max: Optional[float] = None,
    polarity: str = None,
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
        # Determine m/z range
        mz_min = raw_file.RunHeaderEx.LowMass if mz_min is None else mz_min
        mz_max = raw_file.RunHeaderEx.HighMass if mz_max is None else mz_max

        # Check m/z range
        if mz_min > mz_max:
            raise ValueError(f"Invalid m/z range: {mz_min} > {mz_max}")

        # Determine time range
        t_min = raw_file.RunHeaderEx.StartTime * 60 if t_min is None else t_min  # [s]
        t_max = raw_file.RunHeaderEx.EndTime * 60 if t_max is None else t_max  # [s]

        # Check time range
        if t_min > t_max:
            raise ValueError(f"Invalid time range: {t_min} > {t_max}")

        num_of_scans = raw_file.RunHeaderEx.SpectraCount
        scan_indices = list(range(1, num_of_scans + 1))
        # Get all scans
        scans = tuple(Extensions.GetScans(raw_file, 1, num_of_scans))

        # Filter by polarity
        if polarity is not None:
            if polarity not in ["-", "+"]:
                raise (
                    ValueError(
                        "Polarity must be passed as a string containing either '+' or '-'"
                    )
                )
            polarity = "Negative" if polarity == "-" else "Positive"
            polarity_mask = [
                raw_file.GetFilterForScanNumber(i).Polarity.ToString() == polarity
                for i in scan_indices
            ]
            scan_indices = list(compress(scan_indices, polarity_mask))

        scan_time = [scan.ScanStatistics.StartTime * 60 for scan in scans]  # [s]

        # Filter by time range
        time_mask = [t_min <= t <= t_max for t in scan_time]
        scan_indices = list(compress(scan_indices, time_mask))

        # Update time scale
        scan_time = list(compress(scan_time, time_mask))

        # Extract scan spectra and m/z values
        scan_specs = []
        scan_mzs = []
        for i in scan_indices:
            intensities = np.frombuffer(scans[i - 1].SegmentedScan.Intensities)
            positions = np.frombuffer(scans[i - 1].SegmentedScan.Positions)

            # Filter by m/z range
            mz_mask = np.logical_and(mz_min <= positions, positions <= mz_max)
            scan_specs.append(intensities[mz_mask])
            scan_mzs.append(positions[mz_mask])

        if scan_mzs == []:
            raise ValueError(
                f"""No data found in the specified time or m/z range.
                M/z range of the sample file: {raw_file.RunHeaderEx.LowMass} - {raw_file.RunHeaderEx.HighMass}
                Time range: {raw_file.RunHeaderEx.StartTime*60:.1f} - {raw_file.RunHeaderEx.EndTime*60:.1f} s.
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

        # Convert to dask array
        signal_dask = da.from_array(signal_array, chunks="auto")

        # Create and return xarray Dataset
        return xr.Dataset(
            {"signal": (("mz", "time"), signal_dask)},
            coords={"mz": all_mzs, "time": scan_time},
        )


def compute_sum_signal_in_time_range(
    datafile_path: str,
    t_min: Optional[float] = None,
    t_max: Optional[float] = None,
    average: Optional[bool] = False,
    ppm: int = 1,
) -> xr.core.dataarray.DataArray:
    """Computes sum signal in (t_min, t_max) time range, binning counts within "ppm" value

    :param datafile_path: Path to the Thermo Fisher raw file (.raw) containing the data.
    :type datafile_path: str
    :param t_min: Start time [s]
    :type t_min: float, optional
    :param t_max: End time [s]
    :type t_max: float, optional
    :param average: If spectrum should be averaged, defaults to False
    :type average: bool, optional
    :param ppm: ppm precision for binning, defaults to 1
    :type ppm: int, optional
    :return: Sum signal
    :rtype: xr.core.dataarray.DataArray
    """
    with open_raw_file(datafile_path) as raw_file:
        # Get full time range
        t_start = raw_file.RunHeader.StartTime
        t_end = raw_file.RunHeader.EndTime

        # Check if t_min and t_max are passed
        t_min = t_start if t_min is None else t_min / 60
        t_max = t_end if t_max is None else t_max / 60

        # Setup mz tolerance - counts within ppm are binned
        mass_option = MassOptions(ppm, ToleranceUnits.ppm)

        # Get averaged spectrum in time range (t_max, t_max)
        average_scan = Extensions.AverageScansInTimeRange(
            raw_file, t_min, t_max, System.String(""), mass_option
        )
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
    datafile_path: str, timestamps: Iterable[float] | None = None
) -> tuple:
    """Extracts the Total Ion Current (TIC) per scan from the raw file.

    :param datafile_path: Path to the Thermo Fisher raw file (.raw) containing the data.
    :type datafile_path: str
    :param timestamps: Optional iterable of timestamps [s] to extract TIC values for, defaults to None
    :type timestamps: Iterable[float], optional
    :return: Tuple containing the scan timestamps [s] and TIC values as numpy arrays
    :rtype: tuple
    """
    with open_raw_file(datafile_path) as raw_file:
        num_of_scans = raw_file.RunHeaderEx.SpectraCount
        scan_indices = list(range(num_of_scans))

        scan_statistics = [
            raw_file.GetScanStatsForScanNumber(i + 1) for i in scan_indices
        ]
        scan_tic = np.asarray([scan_stat.TIC for scan_stat in scan_statistics])
        scan_timestamp = np.asarray(
            [scan_stat.StartTime for scan_stat in scan_statistics]
        )

        if timestamps:
            # Filter TIC values by timestamps
            timestamps = np.asarray(timestamps)
            # Find closest scan index for each timestamp
            scan_indices = np.searchsorted(scan_timestamp, timestamps)
            # Ensure indices are within valid range
            scan_indices = np.clip(scan_indices, 0, len(scan_timestamp) - 1)
            # Extract scan TIC and scan timestamps values for the closest scan index
            scan_tic = scan_tic[scan_indices]
            scan_timestamp = scan_timestamp[scan_indices]

        return scan_timestamp, scan_tic


def get_peak_profiles(
    datafile_path: str,
    mzs: Iterable[float],
    t_min: Optional[float] = None,
    t_max: Optional[float] = None,
    polarity: Optional[str] = None,
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
    :return: An xarray Dataset containing the peak profiles
    :rtype: xr.Dataset
    """
    with open_raw_file(datafile_path) as raw_file:
        # Make sure mzs are numpy array
        mzs = np.asarray(mzs)
        # Get full time range
        t_start = raw_file.RunHeader.StartTime * 60  # [s]
        t_end = raw_file.RunHeader.EndTime * 60  # [s]

        # Check if t_min and t_max are passed
        t_min = t_start if t_min is None else t_min
        t_max = t_end if t_max is None else t_max

        num_of_scans = raw_file.RunHeaderEx.SpectraCount
        scan_indices = list(range(0, num_of_scans))
        # Get all scans
        scans = tuple(Extensions.GetScans(raw_file, 1, num_of_scans))

        # Filter by polarity
        if polarity is not None:
            if polarity not in ["-", "+"]:
                raise (
                    ValueError(
                        "Polarity must be passed as a string containing either '+' or '-'"
                    )
                )
            polarity = "Negative" if polarity == "-" else "Positive"
            polarity_mask = [
                raw_file.GetFilterForScanNumber(i + 1).Polarity.ToString() == polarity
                for i in scan_indices
            ]
            scan_indices = list(compress(scan_indices, polarity_mask))

        scan_time = [scan.ScanStatistics.StartTime * 60 for scan in scans]  # [s]

        # Filter by time range
        time_mask = [t_min <= t <= t_max for t in scan_time]
        scan_indices = list(compress(scan_indices, time_mask))

        # If scan_indices is empty, raise an error
        if not scan_indices:
            raise ValueError(
                f"""No data found in the specified time range.
                Time range of the sample file: {t_start:.1f} - {t_end:.1f} s.
                """
            )

        # Update time scale
        scan_time = list(compress(scan_time, time_mask))

        intensities = [
            np.frombuffer(scans[i].SegmentedScan.Intensities) for i in scan_indices
        ]
        positions = [
            np.frombuffer(scans[i].SegmentedScan.Positions) for i in scan_indices
        ]

        # Calculate the intensities for the given mz_values
        intensities_for_mz_values = []
        for pos, intens in zip(positions, intensities):
            intensities_for_mz_values.append(np.interp(mzs, pos, intens))

        # Convert to dask array, transpose to have mz values as columns
        peak_profiles_dask = da.from_array(
            np.array(intensities_for_mz_values).T, chunks="auto"
        )

        # Export xarray array with time and mz coordinates
        return xr.DataArray(
            peak_profiles_dask,
            dims=("mz", "time"),
            coords={"mz": mzs, "time": np.array(scan_time)},
            name="signal",
        )
