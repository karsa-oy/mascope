import numpy as np

import mascope_sdk as msdk
from mascope_tools.alignment.calibration import CentroidedSpectrum

from .config import DEFAULT_NOISE_THRESHOLD, DEFAULT_PARENT_PEAK_TOLERANCE


class DataExtractor:
    """Thin client for MS2 analysis.

    Uses the Mascope SDK's MS2 sub-resource to fetch pre-processed data.
    """

    def __init__(
        self,
        mascope: msdk.MascopeClient,
        sample_item_id: str,
        params: dict | None = None,
    ):
        """
        Initialize the DataExtractor by fetching MS2 analysis data from the server.

        :param mascope: An instance of the MascopeClient to use for API calls
        :type mascope: msdk.MascopeClient
        :param sample_item_id: ID of the sample item to analyze
        :type sample_item_id: str
        :param params: Optional parameters for data extraction and processing:
            - noise_threshold: Intensity threshold for filtering out noise peaks (default: 10)
            - parent_peak_tolerance: Tolerance in Da for merging parent peaks (default: 0.001)
        :type params: dict, optional
        :raises ValueError: If the server returns no data for the sample.
        """
        if isinstance(params, dict):
            self.params = params
        else:
            self.params = {}

        self._mascope = mascope
        self._sample_item_id = sample_item_id
        self._ms2 = mascope.samples.ms2(sample_item_id)

        noise_threshold = self.params.get("noise_threshold", DEFAULT_NOISE_THRESHOLD)
        parent_peak_tolerance = self.params.get(
            "parent_peak_tolerance", DEFAULT_PARENT_PEAK_TOLERANCE
        )

        summary = self._ms2.get_summary(parent_peak_tolerance=parent_peak_tolerance)
        if summary is None:
            raise ValueError("Failed to retrieve MS2 summary for the sample.")

        parent_peaks = summary.get("parent_peaks", [])
        isolation_width = summary.get("isolation_width", None)
        if not parent_peaks or isolation_width is None:
            raise ValueError(
                "No MS2 scans were found for the sample; MS2 analysis requires "
                "non-empty parent peaks and a valid isolation width."
            )

        self.parent_peaks = np.array(parent_peaks)
        self.isolation_width = isolation_width
        self.hcd_energy_map = {
            float(k): v for k, v in summary["hcd_energy_map"].items()
        }

        centroids_data = self._ms2.get_averaged_centroids(
            noise_threshold=noise_threshold,
            parent_peak_tolerance=parent_peak_tolerance,
        )
        self.ms2_spectra: dict[float, CentroidedSpectrum] = {}
        if centroids_data:
            for pp_str, data in centroids_data.items():
                pp = float(pp_str)
                mz = np.array(data["mz"])
                intensity = np.array(data["intensity"])
                resolution = np.array(data.get("resolution", []))
                signal_to_noise = np.array(data.get("signal_to_noise", []))
                if resolution.size != mz.size:
                    resolution = np.zeros_like(mz)
                if signal_to_noise.size != mz.size:
                    signal_to_noise = np.zeros_like(mz)
                self.ms2_spectra[pp] = CentroidedSpectrum(
                    mz=mz,
                    intensity=intensity,
                    signal_to_noise=signal_to_noise,
                    resolution=resolution,
                )
        # Ensure every parent peak has an entry
        for pp in self.parent_peaks:
            if pp not in self.ms2_spectra:
                self.ms2_spectra[pp] = CentroidedSpectrum(
                    mz=np.array([]),
                    intensity=np.array([]),
                    signal_to_noise=np.array([]),
                    resolution=np.array([]),
                )

        # MS2 TIC per parent peak
        self.ms2_tic: dict[float, float] = {
            pp: float(spec.intensity.sum()) for pp, spec in self.ms2_spectra.items()
        }

        # Lazy-loaded properties
        self._ms1_spectrum: CentroidedSpectrum | None = None
        self._parent_peak_intensities: dict | None = None
        self._ms1_isolation_tic: dict | None = None

    @property
    def ms1_spectrum(self) -> CentroidedSpectrum:
        """Averaged MS1 spectrum."""
        if self._ms1_spectrum is None:
            self._load_ms1_spectrum()
        assert self._ms1_spectrum is not None
        return self._ms1_spectrum

    @property
    def ms1_tic(self) -> float:
        """Total ion count from averaged MS1 spectrum."""
        return float(self.ms1_spectrum.intensity.sum())

    @property
    def parent_peak_intensities(self) -> dict:
        """Parent peak intensities from averaged MS1 spectrum."""
        if self._parent_peak_intensities is None:
            mz = self.ms1_spectrum.mz
            intensity = self.ms1_spectrum.intensity
            if mz.size == 0 or intensity.size == 0:
                self._parent_peak_intensities = {
                    pp: float("nan") for pp in self.parent_peaks
                }
                return self._parent_peak_intensities
            result = {}
            for pp in self.parent_peaks:
                idx = np.argmin(np.abs(mz - pp))
                result[pp] = float(intensity[idx])
            self._parent_peak_intensities = result
        return self._parent_peak_intensities

    @property
    def ms1_isolation_tic(self) -> dict:
        """Sum MS1 intensities within isolation window per parent peak."""
        if self._ms1_isolation_tic is None:
            mz = self.ms1_spectrum.mz
            intensity = self.ms1_spectrum.intensity
            if mz.size == 0 or intensity.size == 0:
                self._ms1_isolation_tic = {pp: float("nan") for pp in self.parent_peaks}
                return self._ms1_isolation_tic
            half_iso = self.isolation_width / 2
            self._ms1_isolation_tic = {
                pp: float(intensity[np.abs(mz - pp) <= half_iso].sum())
                for pp in self.parent_peaks
            }
        return self._ms1_isolation_tic

    def _load_ms1_spectrum(self):
        """Load averaged MS1 centroided spectrum from the server."""
        ms1_data = self._ms2.get_ms1_centroids()
        if ms1_data is None or len(ms1_data.get("mz", [])) == 0:
            self._ms1_spectrum = CentroidedSpectrum(
                mz=np.array([]),
                intensity=np.array([]),
                signal_to_noise=np.array([]),
                resolution=np.array([]),
            )
            return

        self._ms1_spectrum = CentroidedSpectrum(
            mz=np.array(ms1_data["mz"]),
            intensity=np.array(ms1_data["intensity"]),
            resolution=np.array(ms1_data.get("resolution", [])),
            signal_to_noise=np.array(ms1_data.get("signal_to_noise", [])),
        )
