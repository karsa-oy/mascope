import re
import warnings
import pandas as pd
import numpy as np
import mascope_sdk as msdk
from mascope_tools.alignment.calibration import CentroidedSpectrum, Spectra


DEFAULT_NOISE_THRESHOLD = 10


class DataExtractor:
    def __init__(
        self,
        mascope_url: str,
        access_token: str,
        sample_file_id: str,
        params: dict = {},
    ):
        """
        Initialize the DataExtractor by fetching metadata and spectra from the MAScope API,
        and precomputing necessary data structures for analysis.

        :param mascope_url: Mascope app URL
        :type mascope_url: str
        :param access_token: Access token for authentication with the Mascope API
        :type access_token: str
        :param sample_file_id: ID of the sample file to analyze
        :type sample_file_id: str
        :param params: Optional parameters for data extraction and processing:
            - noise_threshold: Intensity threshold for filtering out noise peaks in the spectra
            (default: 10)
        :type params: dict, optional
        :raises ValueError:
        """
        self.params = params
        meta = msdk.get_sample_file_metadata(mascope_url, access_token, sample_file_id)

        if meta is None:
            raise ValueError("Failed to retrieve metadata for the sample file.")

        self.stats = pd.DataFrame(meta["stats_per_scan"])
        centroids_data = meta["centroids_meta"]
        self.timestamps: list = centroids_data["time"]
        self.centroids: list = centroids_data["data"]

        # Filter centroids
        self.centroids = self._filter_centroids()

        # Distinguish MS scans
        self.ms2_mask = self.stats.loc["MsType"] == "Ms2"
        self.ms1_mask = ~self.ms2_mask

        # Extract unique parent peaks from MS2 scans
        self.parent_peaks = self._get_parent_peaks()

        # Calculate average HCD energy for each unique parent peak
        self.hcd_energy_map = self._get_hcd_energy_map()

        # Build masks for MS2 spectra corresponding to each unique parent peak
        self._ms2_per_parent_masks = self._get_ms2_masks_per_parent_peak()

        # Extract isolation width (assuming it's the same for all MS2 scans)
        self.isolation_width = self._get_isolation_width()

        # Build spectra objects
        self._spectra_objects = self._get_spectra_objects()

        # Extract MS1 and MS2 spectra
        self.ms1_spectrum, self._ms1_spectra_obj = self._get_ms1_spectra()
        self.ms2_spectra, self._ms2_spectra_objs = self._get_ms2_spectra()

        # Build mapping from MS2 scan indices to parent MS1 scan indices
        self.parent_scan_map = self._build_parent_scan_map()

        # Precompute MS1 timeseries
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                category=FutureWarning,
            )
            self.ms1_timeseries = self._ms1_spectra_obj.get_timeseries()
            self.normalized_ms2_timeseries = self._get_normalized_ms2_timeseries()

    def _filter_centroids(self):
        """Filter out noise peaks:
        - Based on minimum signal-to-noise ratio threshold defined in params (default: 10)
        """
        noise_threshold = self.params.get("noise_threshold", DEFAULT_NOISE_THRESHOLD)
        filtered_centroids = []
        for centroid in self.centroids:
            noise_mask = np.array(centroid["noises"]) >= noise_threshold
            mask = noise_mask
            filtered_centroids.append(
                {
                    "mzs": np.array(centroid["mzs"])[mask],
                    "intensities": np.array(centroid["intensities"])[mask],
                    "noises": np.array(centroid["noises"])[mask],
                    "resolutions": np.array(centroid["resolutions"])[mask],
                }
            )
        return filtered_centroids

    def _get_parent_peaks(self):
        """Extract unique parent peaks from MS2 scans"""

        def extract_parent_peak(scan_type):
            """Extract the parent peak m/z from the scan type string"""
            match = re.search(r"ms2 ([\d.]+)@", scan_type)
            if match:
                return float(match.group(1))
            else:
                raise ValueError(
                    f"Failed to extract parent peak from the string: {scan_type}"
                )

        scan_type_per_ms2_scan = self.stats.loc["ScanType"][self.ms2_mask]
        parent_peaks = scan_type_per_ms2_scan.apply(extract_parent_peak)
        return parent_peaks.unique()

    def _get_hcd_energy_map(self):
        """Calculate the average HCD energy for each unique parent peak"""
        hcd_energy_per_parent_peak = {}
        for parent_peak in self.parent_peaks:
            hcd = (
                self.stats.loc["HCD Energy V:"][
                    self.stats.loc["ScanType"].str.contains(f"{parent_peak}@")
                ]
                .astype(float)
                .mean()
                .round(2)
            )
            hcd_energy_per_parent_peak[parent_peak] = hcd
        return hcd_energy_per_parent_peak

    def _get_isolation_width(self) -> float:
        """Extract the isolation width"""
        isolation_width = self.stats.loc["MS2 Isolation Width:"][self.ms2_mask].unique()
        if len(isolation_width) == 1:
            isolation_width = float(isolation_width[0].replace(",", "."))
        else:
            raise ValueError("Multiple isolation widths found for MS2 scans.")
        return isolation_width

    def _get_spectra_objects(self) -> np.ndarray:
        """Convert centroid data into CentroidedSpectrum objects"""
        return np.array(
            [
                CentroidedSpectrum(
                    mz=centroid["mzs"],
                    intensity=centroid["intensities"],
                    signal_to_noise=centroid["noises"],
                    resolution=centroid["resolutions"],
                )
                for centroid in self.centroids
            ]
        )

    def _get_ms2_masks_per_parent_peak(self):
        """Create masks for MS2 spectra corresponding to each unique parent peak"""
        return {
            parent_peak: self.stats.loc["ScanType"]
            .str.contains(f"{parent_peak}@")
            .values
            for parent_peak in self.parent_peaks
        }

    def _get_ms1_spectra(self):
        """Build MS1 spectra from centroid data"""

        ms1_spectra_obj = Spectra(
            self._spectra_objects[self.ms1_mask].tolist(),
            np.array(self.timestamps)[self.ms1_mask],
        )
        ms1_spectrum = ms1_spectra_obj.compute_sum_spectrum(average=True)

        return ms1_spectrum, ms1_spectra_obj

    def _get_ms2_spectra(self):
        """Build MS2 spectra for each unique parent peak"""
        ms2_spectra = {}
        ms2_spectra_objs = {}
        for parent_peak in self.parent_peaks:
            mask = self._ms2_per_parent_masks[parent_peak]
            spectra_obj = Spectra(
                self._spectra_objects[mask].tolist(), np.array(self.timestamps)[mask]
            )
            ms2_spectra_objs[parent_peak] = spectra_obj
            ms2_spectra[parent_peak] = spectra_obj.compute_sum_spectrum(average=True)

        return ms2_spectra, ms2_spectra_objs

    def _build_parent_scan_map(self):
        """Build a mapping from MS2 scan indices to their corresponding parent MS1 scan indices"""
        return {
            ms2_index: parent_scan_index
            for ms2_index, parent_scan_index in self.stats.loc[
                ["ScanNumber", "Master Scan Number:"]
            ]
            .T.astype(int)
            .values[self.ms2_mask]
        }

    def _get_normalized_ms2_timeseries(self):
        """
        For each parent peak, normalize the MS2 fragment timeseries by
        the parent intensity at the corresponding time
        """
        # Map scan number -> position index in centroided_spectra
        scan_numbers = self.stats.loc["ScanNumber"].values.astype(int)
        scan_number_to_pos = {sn: i for i, sn in enumerate(scan_numbers)}

        # Precompute MS2 fragment timeseries per parent peak
        normalized_ms2_timeseries = {}
        half_iso = self.isolation_width / 2
        for pp in self.parent_peaks:
            frag_ts = self._ms2_spectra_objs[pp].get_timeseries()
            if frag_ts.empty:
                normalized_ms2_timeseries[pp] = frag_ts
                continue

            # For each MS2 scan that targeted this parent peak, find parent intensity in its MS1 parent scan
            ms2_scan_positions = np.where(self._ms2_per_parent_masks[pp])[0]
            ms2_scan_numbers = scan_numbers[ms2_scan_positions]

            parent_intensities = []
            parent_timestamps = []
            for ms2_sn in ms2_scan_numbers:
                ms1_sn = self.parent_scan_map.get(int(ms2_sn))
                if ms1_sn is None:
                    continue
                ms1_pos = scan_number_to_pos.get(int(ms1_sn))
                if ms1_pos is None:
                    continue
                ms1_spec = self._spectra_objects[ms1_pos]
                # Find peaks within isolation window around parent m/z
                within = np.abs(ms1_spec.mz - pp) <= half_iso
                parent_int = (
                    float(ms1_spec.intensity[within].sum())
                    if np.any(within)
                    else np.nan
                )
                parent_intensities.append(parent_int)
                parent_timestamps.append(
                    self.timestamps[
                        ms2_scan_positions[np.where(ms2_scan_numbers == ms2_sn)[0][0]]
                    ]
                )

            parent_series = pd.Series(
                parent_intensities,
                index=pd.to_datetime(parent_timestamps, unit="s"),
            )

            # Align columns: fragment timeseries columns are MS2 timestamps
            # Normalize each fragment by parent intensity at matching time
            aligned_parent = parent_series.reindex(
                frag_ts.columns, method="nearest", tolerance=pd.Timedelta("2s")
            )
            normalized_ms2_timeseries[pp] = frag_ts.div(aligned_parent, axis=1)

        return normalized_ms2_timeseries
