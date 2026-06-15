"""Reader-backend seam for ``mascope_thermo``.

Selects the file-reading implementation behind a single switch so the public
functions in :mod:`mascope_thermo.thermo` can run on either Thermo's
RawFileReader (the current default) or — once implemented — the open-source
OpenTFRaw reader, without the callers caring which.

Select with the ``MASCOPE_THERMO_BACKEND`` environment variable::

    "thermo"     -> ThermoBackend (default; pythonnet + bundled .NET DLLs)
    "opentfraw"  -> OpenTFRawBackend (built in a later migration step)

See ``libraries/thermo/OpenTFRaw_migration_execution_plan.md`` (§3) for the
rationale (a capability protocol, not an emulation of the .NET RawFile object).

This is introduced incrementally: :class:`ReaderBackend` lists only the
capabilities of functions already migrated onto the seam. More methods (profile
arrays, centroids, multi-scan averaging, XIC, trailer, run header, ...) are
added as the remaining ``thermo.py`` functions move over.
"""

from __future__ import annotations

import os
from typing import Literal, Protocol, runtime_checkable

import numpy as np


ENV_BACKEND = "MASCOPE_THERMO_BACKEND"

Polarity = Literal["+", "-"]
MsType = Literal["Ms", "Ms2"]


@runtime_checkable
class ReaderBackend(Protocol):
    """Capability interface the :mod:`mascope_thermo.thermo` functions depend on.

    Implementations are context managers: open the file in ``__enter__`` and
    release it in ``__exit__``. All methods return backend-neutral Python/NumPy
    data (never .NET objects), so callers are backend-agnostic.
    """

    def __enter__(self) -> ReaderBackend: ...
    def __exit__(self, *exc) -> None: ...

    def polarities(self) -> set[str]:
        """Set of polarities present in the file, as ``"+"`` / ``"-"``."""
        ...

    def scan_times(
        self,
        polarity: Polarity | None = None,
        t_min: float | None = None,
        t_max: float | None = None,
        ms_type: MsType | None = "Ms",
    ) -> np.ndarray:
        """Scan start times [s] for the scans matching the given filters."""
        ...

    def tic_per_scan(
        self,
        polarity: Polarity | None = None,
        t_min: float | None = None,
        t_max: float | None = None,
        ms_type: MsType | None = "Ms",
    ) -> tuple[np.ndarray, np.ndarray]:
        """``(scan_times_s, tic)`` for the scans matching the given filters."""
        ...

    def instrument_details(self) -> dict:
        """Instrument metadata dict (Name, Model, SerialNumber, ...)."""
        ...

    def num_scans(self) -> int:
        """Total number of scans (spectra) in the file."""
        ...

    def scan_acquisition_settings(
        self,
        polarity: Polarity | None = None,
        t_min: float | None = None,
        t_max: float | None = None,
        ms_type: MsType | None = "Ms",
    ) -> dict:
        """Per-scan trailer table ``{"header_labels": [...], "settings": {...}}``."""
        ...

    def scan_statistics(
        self,
        polarity: Polarity | None = None,
        t_min: float | None = None,
        t_max: float | None = None,
        ms_type: MsType | None = "Ms",
    ) -> dict:
        """Per-scan statistics keyed by 1-based scan number."""
        ...

    def scan_indices(
        self,
        polarity: Polarity | None = None,
        t_min: float | None = None,
        t_max: float | None = None,
        ms_type: MsType | None = "Ms",
    ) -> list[int]:
        """1-based scan numbers matching the given filters."""
        ...

    def centroids_per_scan(
        self,
        polarity: Polarity | None = None,
        t_min: float | None = None,
        t_max: float | None = None,
        ms_type: MsType | None = None,
        mz_min: float | None = None,
        mz_max: float | None = None,
    ) -> list[dict]:
        """Per-scan centroids: list of dicts with ``masses``, ``intensities``,
        ``resolutions``, ``signal_to_noise``, ``timestamp``."""
        ...

    def average_centroids(
        self,
        scan_indices: list[int],
        ppm: int = 1,
        average: bool = False,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Multi-scan ppm-binned averaged centroids:
        ``(masses, intensities, resolutions, signal_to_noise)``.

        Gap 5.3: the Thermo backend uses ``Extensions.AverageScans``; the
        OpenTFRaw backend must reimplement ppm binning in NumPy."""
        ...

    def centroids_meta(self) -> dict:
        """All-scan centroid arrays for legacy metadata: ``{"time": [...],
        "data": [{"mzs", "intensities", "resolutions", "noises"}]}``."""
        ...


# Field set returned by GetInstrumentData (excluding non-serializable
# ChannelLabels / Units). Kept here so every backend reports the same shape.
INSTRUMENT_FIELDS = (
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
)

# Per-scan statistics fields read from Thermo's ScanStats. (OpenTFRaw exposes a
# subset; the metadata remap is assessment Phase 4.)
SCAN_STAT_FIELDS = (
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
)


class ThermoBackend:
    """:class:`ReaderBackend` backed by Thermo RawFileReader via pythonnet.

    Wraps the existing ``RawFileManager`` + ``ScanSelector`` machinery in
    :mod:`mascope_thermo.thermo` (imported lazily to avoid an import cycle).
    """

    def __init__(self, datafile_path: str):
        self.datafile_path = datafile_path
        self._mgr = None
        self._raw = None

    def __enter__(self) -> ThermoBackend:
        from mascope_thermo.thermo import RawFileManager

        self._mgr = RawFileManager(self.datafile_path)
        self._raw = self._mgr.__enter__()
        return self

    def __exit__(self, *exc) -> None:
        try:
            if self._mgr is not None:
                self._mgr.__exit__(*exc)
        finally:
            self._mgr = None
            self._raw = None

    def _selector(
        self,
        polarity: Polarity | None = None,
        t_min: float | None = None,
        t_max: float | None = None,
        ms_type: MsType | None = "Ms",
    ):
        from mascope_thermo.thermo import ScanSelector

        return ScanSelector(
            self._raw,
            polarity=polarity,
            t_min=t_min,
            t_max=t_max,
            ms_type=ms_type,
        )

    def polarities(self) -> set[str]:
        out: set[str] = set()
        for scan_filter in self._selector(ms_type=None).raw_scan_filters:
            verbose = scan_filter.Polarity.ToString()
            if verbose == "Positive":
                out.add("+")
            elif verbose == "Negative":
                out.add("-")
        return out

    def scan_times(
        self,
        polarity: Polarity | None = None,
        t_min: float | None = None,
        t_max: float | None = None,
        ms_type: MsType | None = "Ms",
    ) -> np.ndarray:
        return self._selector(polarity, t_min, t_max, ms_type).scan_times

    def tic_per_scan(
        self,
        polarity: Polarity | None = None,
        t_min: float | None = None,
        t_max: float | None = None,
        ms_type: MsType | None = "Ms",
    ) -> tuple[np.ndarray, np.ndarray]:
        selector = self._selector(polarity, t_min, t_max, ms_type)
        times = selector.scan_times
        tic = np.asarray(
            [
                self._raw.GetScanStatsForScanNumber(i).TIC
                for i in selector.scan_indices_1based
            ],
            dtype=np.float64,
        )
        return times, tic

    def instrument_details(self) -> dict:
        data = self._raw.GetInstrumentData()
        return {field: getattr(data, field) for field in INSTRUMENT_FIELDS}

    def num_scans(self) -> int:
        return self._raw.RunHeaderEx.SpectraCount

    def scan_acquisition_settings(
        self,
        polarity: Polarity | None = None,
        t_min: float | None = None,
        t_max: float | None = None,
        ms_type: MsType | None = "Ms",
    ) -> dict:
        selector = self._selector(polarity, t_min, t_max, ms_type)
        settings: dict[int, list] = {}
        header_labels = None
        for i in selector.scan_indices_1based:
            header = self._raw.GetTrailerExtraInformation(i)
            if header_labels is None:
                header_labels = list(header.Labels)
            settings[i] = list(header.Values)
        return {"header_labels": header_labels, "settings": settings}

    def scan_statistics(
        self,
        polarity: Polarity | None = None,
        t_min: float | None = None,
        t_max: float | None = None,
        ms_type: MsType | None = "Ms",
    ) -> dict:
        selector = self._selector(polarity, t_min, t_max, ms_type)
        return {
            scan_index: {
                **{
                    name: getattr(selector.raw_scan_stats[scan_index - 1], name)
                    for name in SCAN_STAT_FIELDS
                },
                # Scan type isn't in ScanStats; read it from the filter.
                "MsType": selector.raw_scan_filters[scan_index - 1].MSOrder.ToString(),
            }
            for scan_index in selector.scan_indices_1based
        }

    def scan_indices(
        self,
        polarity: Polarity | None = None,
        t_min: float | None = None,
        t_max: float | None = None,
        ms_type: MsType | None = "Ms",
    ) -> list[int]:
        return self._selector(polarity, t_min, t_max, ms_type).scan_indices_1based

    def centroids_per_scan(
        self,
        polarity: Polarity | None = None,
        t_min: float | None = None,
        t_max: float | None = None,
        ms_type: MsType | None = None,
        mz_min: float | None = None,
        mz_max: float | None = None,
    ) -> list[dict]:
        from mascope_thermo.thermo import _validate_mz_range

        mz_min, mz_max = _validate_mz_range(self._raw, mz_min, mz_max)
        selector = self._selector(polarity, t_min, t_max, ms_type)

        out: list[dict] = []
        for scan, timestamp in zip(selector.scans, selector.scan_times):
            centroid_scan = scan.CentroidScan
            if centroid_scan is None or centroid_scan.Length == 0:
                masses = np.array([], dtype=np.float64)
                intensities = np.array([], dtype=np.float64)
                resolutions = np.array([], dtype=np.float64)
                signal_to_noise = np.array([], dtype=np.float64)
            else:
                peaks = centroid_scan.GetLabelPeaks()
                n = len(peaks)
                masses = np.fromiter(
                    (c.Mass for c in peaks), dtype=np.float64, count=n
                )
                intensities = np.fromiter(
                    (c.Intensity for c in peaks), dtype=np.float64, count=n
                )
                resolutions = np.fromiter(
                    (c.Resolution for c in peaks), dtype=np.float64, count=n
                )
                signal_to_noise = np.fromiter(
                    (c.SignalToNoise for c in peaks), dtype=np.float64, count=n
                )
                mz_mask = np.logical_and(mz_min <= masses, masses <= mz_max)
                masses = masses[mz_mask]
                intensities = intensities[mz_mask]
                resolutions = resolutions[mz_mask]
                signal_to_noise = signal_to_noise[mz_mask]

            out.append(
                {
                    "masses": masses,
                    "intensities": intensities,
                    "resolutions": resolutions,
                    "signal_to_noise": signal_to_noise,
                    "timestamp": timestamp,
                }
            )
        return out

    def average_centroids(
        self,
        scan_indices: list[int],
        ppm: int = 1,
        average: bool = False,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        from mascope_thermo.thermo import _average_scans_centroids

        return _average_scans_centroids(
            self._raw, scan_indices, ppm=ppm, average=average
        )

    def centroids_meta(self) -> dict:
        result = {"time": [], "data": []}
        selector = self._selector(ms_type=None)
        for timestamp, scan in zip(selector.scan_times, selector.scans):
            centroid_scan = scan.CentroidScan
            if centroid_scan is not None and centroid_scan.Length > 0:
                mzs = np.frombuffer(centroid_scan.Masses)
                intensities = np.frombuffer(centroid_scan.Intensities)
                resolutions = np.frombuffer(centroid_scan.Resolutions)
                noises = np.frombuffer(centroid_scan.Noises)

                valid = (
                    np.isfinite(resolutions)
                    & (resolutions > 0)
                    & np.isfinite(intensities)
                    & (intensities > 0)
                )
                mzs = mzs[valid].tolist()
                intensities = intensities[valid].tolist()
                resolutions = resolutions[valid].tolist()
                noises = noises[valid].tolist()
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


def open_backend(datafile_path: str) -> ReaderBackend:
    """Open ``datafile_path`` with the backend selected by ``MASCOPE_THERMO_BACKEND``.

    Returns a context manager. Defaults to the Thermo backend, preserving today's
    behaviour when the variable is unset.
    """
    name = os.environ.get(ENV_BACKEND, "thermo").lower()
    if name == "thermo":
        return ThermoBackend(datafile_path)
    if name == "opentfraw":
        raise NotImplementedError(
            "OpenTFRaw backend is not implemented yet "
            "(see OpenTFRaw_migration_execution_plan.md, step 4)."
        )
    raise ValueError(
        f"Unknown {ENV_BACKEND}={name!r}; expected 'thermo' or 'opentfraw'."
    )
