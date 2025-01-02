from pathlib import Path
from itertools import compress
from contextlib import contextmanager
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


def get_signal(datafile_path: str, polarity: str = None) -> xr.Dataset:
    """This function uses the Thermo Fisher libraries to read the raw file and extract the scan data.
    It then merges the scans to have a common m/z scale and converts the data to an xarray Dataset.

    :param datafile_path: Path to the Thermo Fisher raw file (.raw) containing the data.
    :type datafile_path: str
    :param polarity: + or -, Polarity of the scans to be retrieved, optional, defaults to None (get all scans)
    :type polarity: str
    :return: An xarray Dataset containing the signal data
    :rtype: xr.Dataset
    """
    with open_raw_file(datafile_path) as raw_file:
        num_of_scans = raw_file.RunHeaderEx.SpectraCount
        scan_indices = list(range(num_of_scans))

        # Filter by polarity
        if polarity:
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

        # Extract scan statistics and segmented scan data
        scan_statistics = [
            raw_file.GetScanStatsForScanNumber(i + 1) for i in scan_indices
        ]
        segmented_scan = [
            raw_file.GetSegmentedScanFromScanNumber(i + 1, scan_statistics[i])
            for i in scan_indices
        ]

        # Extract scan spectra and m/z values
        scan_specs = [
            np.fromiter(scan.Intensities, np.float64) for scan in segmented_scan
        ]  # [Relative abundance]
        scan_mzs = [
            np.fromiter(scan.Positions, np.float32) for scan in segmented_scan
        ]  # [Th]
        scan_time = [scan_stat.StartTime * 60 for scan_stat in scan_statistics]  # [s]

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
    t1: float = None,
    t2: float = None,
    average: bool = False,
    ppm: int = 1,
) -> xr.core.dataarray.DataArray:
    """Computes sum signal in (t1, t2) time range, binning counts within "ppm" value

    :param datafile_path: Path to the Thermo Fisher raw file (.raw) containing the data.
    :type datafile_path: str
    :param t1: Start time [s]
    :type t1: float, optional
    :param t2: End time [s]
    :type t2: float, optional
    :param average: If spectrum should be averaged, defaults to False
    :type average: bool, optional
    :param ppm: ppm precision for binning, defaults to 1
    :type ppm: int, optional
    :return: Sum signal
    :rtype: xr.core.dataarray.DataArray
    """
    with open_raw_file(datafile_path) as raw_file:
        # Get full time range
        t_min = raw_file.RunHeader.StartTime
        t_max = raw_file.RunHeader.EndTime

        # Check if t1 and t2 are passed
        t1 = t_min if t1 is None else t1 / 60
        t2 = t_max if t2 is None else t2 / 60

        # Setup mz tolerance - counts within ppm are binned
        mass_option = MassOptions(ppm, ToleranceUnits.ppm)

        # Get averaged spectrum in time range (t1, t2)
        average_scan = Extensions.AverageScansInTimeRange(
            raw_file, t1, t2, System.String(""), mass_option
        )
        averaged_spec = average_scan.SegmentedScan

        # Extract averaged signal, multiply by num_of_scans to restore sum signal
        mz = np.fromiter(averaged_spec.Positions, np.float32)
        sum_signal = np.fromiter(averaged_spec.Intensities, np.float32)

        if not average:
            # Multiply by number of averaged scans
            sum_signal *= average_scan.ScansCombined

        # Convert sum signal to dask array
        sum_signal_dask = da.from_array(sum_signal, chunks="auto")

        # Convert to xarray.DataArray
        return xr.DataArray(
            data=sum_signal_dask, dims=["mz"], coords={"mz": mz}, name="sum_signal"
        )
