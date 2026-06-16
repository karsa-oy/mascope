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
import re
from typing import Literal, Protocol, runtime_checkable

import numpy as np


ENV_BACKEND = "MASCOPE_THERMO_BACKEND"

Polarity = Literal["+", "-"]
MsType = Literal["Ms", "Ms2"]

# Scan times are reported in minutes by both backends but the public API returns
# seconds (matching the Thermo path's StartTime * 60).
_SECONDS_PER_MINUTE = 60


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

    def mass_range(self) -> tuple[float, float]:
        """Run-level ``(low_mass, high_mass)`` from the run header."""
        ...

    def profile_per_scan(
        self,
        polarity: Polarity | None = None,
        t_min: float | None = None,
        t_max: float | None = None,
        ms_type: MsType | None = "Ms",
        mz_min: float | None = None,
        mz_max: float | None = None,
    ) -> tuple[list[np.ndarray], list[np.ndarray], np.ndarray]:
        """Per-scan profile spectra: ``(scan_mzs, scan_intensities, scan_times)``,
        the m/z and intensity arrays already restricted to ``[mz_min, mz_max]``.

        Gap 5.2: OpenTFRaw's Python bindings expose centroids only; an
        OpenTFRaw backend needs the profile arrays surfaced (fork/upstream)."""
        ...

    def average_profile(
        self,
        scan_indices: list[int],
        ppm: int = 1,
        average: bool = False,
    ) -> tuple[np.ndarray, np.ndarray, int]:
        """Multi-scan ppm-binned averaged profile spectrum:
        ``(mz, intensities, scans_combined)``. With ``average=False`` the
        intensities are scaled back up by the combined-scan count (sum signal).

        Combines gaps 5.2 (profile) and 5.3 (ppm averaging)."""
        ...

    def xic(
        self,
        mzs,
        ppm: float = 5,
        polarity: Polarity | None = None,
        t_min: float | None = None,
        t_max: float | None = None,
        ms_type: MsType | None = "Ms",
    ) -> tuple[np.ndarray, np.ndarray]:
        """Extracted-ion chromatograms for each target m/z within ``ppm``:
        ``(intensities[n_mz, n_scans], scan_times)``.

        Gap 5.4: the Thermo backend uses ``GetChromatogramData``; the OpenTFRaw
        backend must reimplement m/z-window summation in NumPy."""
        ...

    def ms2_precursor_by_scan(
        self,
        polarity: Polarity | None = None,
        t_min: float | None = None,
        t_max: float | None = None,
    ) -> dict[int, float]:
        """``{scan_number: precursor_mz}`` for MS² scans (only those whose
        precursor is resolvable).

        Gap 5.1b: the Thermo backend parses the precursor from the filter
        string; OpenTFRaw returns it as ``None`` (fork/upstream candidate)."""
        ...

    def ms2_acquisition_info(
        self,
        polarity: Polarity | None = None,
        t_min: float | None = None,
        t_max: float | None = None,
    ) -> tuple[float | None, dict[int, str]]:
        """``(isolation_width, {scan_number: hcd_energy_string})`` for MS² scans.

        ``isolation_width`` is the single MS² isolation width across the scans;
        the HCD energy strings may be comma-separated (step dissociation). Thermo
        reads both from the trailer (``"MS2 Isolation Width:"`` /
        ``"HCD Energy V:"``); a backend lacking the calibrated HCD energy raises
        ``NotImplementedError``."""
        ...

    def ms2_centroids_for_scans(
        self, scan_indices: list[int]
    ) -> tuple[list[dict], list[float]]:
        """Per-scan centroids + TIC for explicit scan numbers:
        ``([{masses, intensities, resolutions, signal_to_noise, timestamp}], tics)``."""
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

# Per-scan acquisition fields OpenTFRaw decodes (from its typed scan dict),
# surfaced as a trailer-like table. The label strings are descriptive and
# intentionally differ from Thermo's trailer labels, which OpenTFRaw does not
# expose; the (key, label) pairs map an OpenTFRaw scan-dict key to a column.
_OTF_TRAILER_FIELDS = (
    ("ion_injection_time_ms", "Ion Injection Time (ms)"),
    ("charge", "Charge State"),
    ("precursor_mz", "Precursor m/z"),
    ("isolation_width", "Isolation Width (m/z)"),
    ("collision_energy", "Collision Energy"),
)

# Output grid resolution (constant ppm) for average_profile. Fine enough to
# sample per-peak FWHM (~4-8 ppm on Orbitrap) at many points while collapsing
# the between-scan jitter duplicates into one cell per native position.
_AVG_PROFILE_GRID_PPM = 0.2


def _label_peaks(
    centroid_scan,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Extract ``(masses, intensities, resolutions, signal_to_noise)`` from a
    Thermo CentroidScan's label peaks, or four empty arrays if there are none.
    """
    if centroid_scan is None or centroid_scan.Length == 0:
        return (
            np.array([], dtype=np.float64),
            np.array([], dtype=np.float64),
            np.array([], dtype=np.float64),
            np.array([], dtype=np.float64),
        )
    peaks = centroid_scan.GetLabelPeaks()
    n = len(peaks)
    return (
        np.fromiter((c.Mass for c in peaks), dtype=np.float64, count=n),
        np.fromiter((c.Intensity for c in peaks), dtype=np.float64, count=n),
        np.fromiter((c.Resolution for c in peaks), dtype=np.float64, count=n),
        np.fromiter((c.SignalToNoise for c in peaks), dtype=np.float64, count=n),
    )


def _ppm_bin(
    mz: np.ndarray,
    intensity: np.ndarray,
    extras: list[np.ndarray],
    ppm: float,
) -> tuple[np.ndarray, np.ndarray, list[np.ndarray]]:
    """Greedily cluster ``(mz, intensity)`` points within ``ppm`` and aggregate.

    Points (pooled across scans) are sorted by m/z; a new bin starts wherever
    the gap to the previous point exceeds ``ppm`` (relative to the lower m/z).
    Per bin: intensity-weighted mean m/z, summed intensity, and an
    intensity-weighted mean of each array in ``extras`` (e.g. resolution, S:N).
    Vectorized with ``np.add.reduceat`` so it scales to the hundreds of
    thousands of profile points a multi-scan window produces.

    Returns ``(binned_mz, summed_intensity, [binned_extra, ...])``.
    """
    empty = np.array([], dtype=np.float64)
    if mz.size == 0:
        return empty, empty, [empty for _ in extras]

    order = np.argsort(mz, kind="stable")
    mz = mz[order]
    intensity = intensity[order]
    extras = [e[order] for e in extras]

    if mz.size == 1:
        starts = np.array([0])
    else:
        gap_ppm = np.diff(mz) / mz[:-1] * 1e6
        starts = np.concatenate(([0], np.flatnonzero(gap_ppm > ppm) + 1))

    counts = np.diff(np.append(starts, mz.size))
    isum = np.add.reduceat(intensity, starts)
    # Guard against zero-intensity bins (fall back to a plain mean for m/z and
    # the extras there).
    safe = np.where(isum > 0, isum, 1.0)
    nonzero = isum > 0

    wmz = np.add.reduceat(mz * intensity, starts) / safe
    plain_mz = np.add.reduceat(mz, starts) / counts
    binned_mz = np.where(nonzero, wmz, plain_mz)

    binned_extras = []
    for e in extras:
        we = np.add.reduceat(e * intensity, starts) / safe
        plain_e = np.add.reduceat(e, starts) / counts
        binned_extras.append(np.where(nonzero, we, plain_e))

    return binned_mz, isum, binned_extras


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
            masses, intensities, resolutions, signal_to_noise = _label_peaks(
                scan.CentroidScan
            )
            mz_mask = np.logical_and(mz_min <= masses, masses <= mz_max)
            out.append(
                {
                    "masses": masses[mz_mask],
                    "intensities": intensities[mz_mask],
                    "resolutions": resolutions[mz_mask],
                    "signal_to_noise": signal_to_noise[mz_mask],
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

    def mass_range(self) -> tuple[float, float]:
        header = self._raw.RunHeaderEx
        return header.LowMass, header.HighMass

    def profile_per_scan(
        self,
        polarity: Polarity | None = None,
        t_min: float | None = None,
        t_max: float | None = None,
        ms_type: MsType | None = "Ms",
        mz_min: float | None = None,
        mz_max: float | None = None,
    ) -> tuple[list[np.ndarray], list[np.ndarray], np.ndarray]:
        from mascope_thermo.thermo import _validate_mz_range

        mz_min, mz_max = _validate_mz_range(self._raw, mz_min, mz_max)
        selector = self._selector(polarity, t_min, t_max, ms_type)

        scan_mzs: list[np.ndarray] = []
        scan_specs: list[np.ndarray] = []
        for scan in selector.scans:
            positions = np.frombuffer(scan.SegmentedScan.Positions)
            intensities = np.frombuffer(scan.SegmentedScan.Intensities)
            mz_mask = np.logical_and(mz_min <= positions, positions <= mz_max)
            scan_mzs.append(positions[mz_mask])
            scan_specs.append(intensities[mz_mask])
        return scan_mzs, scan_specs, selector.scan_times

    def average_profile(
        self,
        scan_indices: list[int],
        ppm: int = 1,
        average: bool = False,
    ) -> tuple[np.ndarray, np.ndarray, int]:
        from System.Collections.Generic import List
        from ThermoFisher.CommonCore.Data import Extensions, ToleranceUnits
        from ThermoFisher.CommonCore.Data.Business import MassOptions

        dotnet_indices = List[int]()
        for index in scan_indices:
            dotnet_indices.Add(index)

        average_scan = Extensions.AverageScans(
            self._raw, dotnet_indices, MassOptions(ppm, ToleranceUnits.ppm)
        )
        segmented = average_scan.SegmentedScan
        num_combined = average_scan.ScansCombined
        mz = np.frombuffer(segmented.Positions)
        intensities = np.frombuffer(segmented.Intensities)
        if not average:
            intensities = intensities * num_combined
        return mz, intensities, num_combined

    def xic(
        self,
        mzs,
        ppm: float = 5,
        polarity: Polarity | None = None,
        t_min: float | None = None,
        t_max: float | None = None,
        ms_type: MsType | None = "Ms",
    ) -> tuple[np.ndarray, np.ndarray]:
        from ThermoFisher.CommonCore.Data.Business import (
            ChromatogramSignal,
            ChromatogramTraceSettings,
            Range,
            TraceType,
        )

        mzs = np.asarray(mzs, dtype=float)
        selector = self._selector(polarity, t_min, t_max, ms_type)
        indices_0based = selector.scan_indices_0based

        intensities = np.zeros((len(mzs), len(indices_0based)), dtype=np.float64)
        mz_lows = mzs - (mzs * ppm / 1e6)
        mz_highs = mzs + (mzs * ppm / 1e6)

        settings = []
        for mz_low, mz_high in zip(mz_lows, mz_highs):
            mz_range = Range()
            mz_range.Low = mz_low
            mz_range.High = mz_high
            setting = ChromatogramTraceSettings(TraceType.MassRange)
            setting.MassRanges = [mz_range]
            settings.append(setting)

        # -1, -1 -> all scans; slice down to the filtered scans afterwards.
        chromatogram = self._raw.GetChromatogramData(settings, -1, -1)
        traces = ChromatogramSignal.FromChromatogramData(chromatogram)
        for i, trace in enumerate(traces):
            intensities[i] = np.fromiter(
                trace.Intensities, dtype=np.float64, count=len(trace.Intensities)
            )[indices_0based]

        return intensities, selector.scan_times

    def ms2_precursor_by_scan(
        self,
        polarity: Polarity | None = None,
        t_min: float | None = None,
        t_max: float | None = None,
    ) -> dict[int, float]:
        selector = self._selector(polarity, t_min, t_max, ms_type="Ms2")
        out: dict[int, float] = {}
        for scan_idx, scan_filter in zip(
            selector.scan_indices_1based, selector.scan_filters, strict=True
        ):
            match = re.search(r"ms2 ([\d.]+)@", scan_filter.ToString())
            if match:
                out[scan_idx] = float(match.group(1))
        return out

    def ms2_acquisition_info(
        self,
        polarity: Polarity | None = None,
        t_min: float | None = None,
        t_max: float | None = None,
    ) -> tuple[float | None, dict[int, str]]:
        acq = self.scan_acquisition_settings(polarity, t_min, t_max, ms_type="Ms2")
        trailer_labels = acq["header_labels"]
        isolation_width_idx = trailer_labels.index("MS2 Isolation Width:")
        hcd_label_idx = trailer_labels.index("HCD Energy V:")

        isolation_widths = set()
        scan_idx_to_hcd: dict[int, str] = {}
        for scan_idx, trailer_values in acq["settings"].items():
            isolation_widths.add(trailer_values[isolation_width_idx])
            scan_idx_to_hcd[scan_idx] = trailer_values[hcd_label_idx]

        isolation_widths.discard(None)
        isolation_widths.discard("")
        if len(isolation_widths) == 1:
            isolation_width = float(isolation_widths.pop().replace(",", "."))
        else:
            raise ValueError("Multiple isolation widths found for MS2 scans.")
        return isolation_width, scan_idx_to_hcd

    def ms2_centroids_for_scans(
        self, scan_indices: list[int]
    ) -> tuple[list[dict], list[float]]:
        from ThermoFisher.CommonCore.Data import Extensions

        from mascope_thermo.thermo import SECONDS_PER_MINUTE

        centroids: list[dict] = []
        tic_values: list[float] = []
        for scan_idx in scan_indices:
            scan_obj = list(Extensions.GetScans(self._raw, scan_idx, scan_idx))[0]
            stats = self._raw.GetScanStatsForScanNumber(scan_idx)
            masses, intensities, resolutions, signal_to_noise = _label_peaks(
                scan_obj.CentroidScan
            )
            centroids.append(
                {
                    "masses": masses,
                    "intensities": intensities,
                    "resolutions": resolutions,
                    "signal_to_noise": signal_to_noise,
                    "timestamp": stats.StartTime * SECONDS_PER_MINUTE,
                }
            )
            tic_values.append(float(stats.TIC))
        return centroids, tic_values


class OpenTFRawBackend:
    """:class:`ReaderBackend` backed by the open-source OpenTFRaw reader.

    Built incrementally (migration step 4+). Capabilities OpenTFRaw 1.1.0 exposes
    cleanly are implemented; the rest raise ``NotImplementedError`` referencing
    the relevant gap, so the dual-backend contract suite xfails them until they
    land (decode/fork work or NumPy reimplementations).
    """

    def __init__(self, datafile_path: str):
        self.datafile_path = datafile_path
        self._raw = None
        self._scans: list[dict] | None = None

    def __enter__(self) -> OpenTFRawBackend:
        import opentfraw

        self._raw = opentfraw.RawFile(self.datafile_path)
        return self

    def __exit__(self, *exc) -> None:
        self._raw = None
        self._scans = None

    # -- scan selection: mirrors thermo.ScanSelector over OpenTFRaw scan dicts --

    def _all_scans(self) -> list[dict]:
        if self._scans is None:
            self._scans = list(self._raw.iter_scans())
        return self._scans

    def _selected(
        self,
        polarity: Polarity | None = None,
        t_min: float | None = None,
        t_max: float | None = None,
        ms_type: MsType | None = "Ms",
    ) -> list[dict]:
        from mascope_thermo.thermo import (
            InvalidRangeError,
            NoScansFoundError,
            PolarityError,
            ScanTypeError,
        )

        scans = self._all_scans()
        mask = np.ones(len(scans), dtype=bool)

        if polarity:
            if polarity not in ("-", "+"):
                raise PolarityError(
                    f"Invalid polarity '{polarity}' provided. "
                    "Polarity must be '+' or '-'."
                )
            mask &= np.array([s["polarity"] == polarity for s in scans])

        if t_min is not None or t_max is not None:
            start_s = np.array(
                [s["retention_time"] * _SECONDS_PER_MINUTE for s in scans]
            )
            low = start_s.min() if t_min is None else t_min
            high = start_s.max() if t_max is None else t_max
            if low > high:
                raise InvalidRangeError(
                    f"Invalid time range: t_min={low} s > t_max={high} s"
                )
            eps = np.finfo(np.float64).eps * high
            mask &= (low - eps < start_s) & (start_s < high + eps)

        if ms_type:
            level = {"Ms": 1, "Ms2": 2}.get(ms_type)
            if level is None:
                raise ScanTypeError(
                    f"Invalid scan type '{ms_type}' provided. "
                    "MS scan type must be 'Ms' or 'Ms2'."
                )
            mask &= np.array([int(s["ms_level"]) == level for s in scans])

        selected = [s for s, keep in zip(scans, mask) if keep]
        if not selected:
            raise NoScansFoundError(
                "No scans found matching the specified filters: "
                f"polarity='{polarity}', time_range=({t_min}, {t_max}), "
                f"ms_type='{ms_type}'"
            )
        return selected

    # -- clean mappings (implemented) --

    def polarities(self) -> set[str]:
        return {s["polarity"] for s in self._all_scans() if s["polarity"] in ("+", "-")}

    def scan_times(
        self,
        polarity: Polarity | None = None,
        t_min: float | None = None,
        t_max: float | None = None,
        ms_type: MsType | None = "Ms",
    ) -> np.ndarray:
        return np.array(
            [
                s["retention_time"] * _SECONDS_PER_MINUTE
                for s in self._selected(polarity, t_min, t_max, ms_type)
            ]
        )

    def tic_per_scan(
        self,
        polarity: Polarity | None = None,
        t_min: float | None = None,
        t_max: float | None = None,
        ms_type: MsType | None = "Ms",
    ) -> tuple[np.ndarray, np.ndarray]:
        selected = self._selected(polarity, t_min, t_max, ms_type)
        times = np.array(
            [s["retention_time"] * _SECONDS_PER_MINUTE for s in selected]
        )
        tic = np.array([s["total_ion_current"] for s in selected], dtype=np.float64)
        return times, tic

    def num_scans(self) -> int:
        return int(self._raw.num_scans)

    def scan_indices(
        self,
        polarity: Polarity | None = None,
        t_min: float | None = None,
        t_max: float | None = None,
        ms_type: MsType | None = "Ms",
    ) -> list[int]:
        return [
            int(s["scan_number"])
            for s in self._selected(polarity, t_min, t_max, ms_type)
        ]

    def mass_range(self) -> tuple[float, float]:
        scans = self._all_scans()
        return (
            float(min(s["low_mz"] for s in scans)),
            float(max(s["high_mz"] for s in scans)),
        )

    # -- Phase-4 metadata remap --

    def instrument_details(self) -> dict:
        # OpenTFRaw detects only the instrument model (it does not parse the
        # structured InstID block), so Model / Name are populated and the rest
        # (serial number, software/hardware version, axis labels, flags) are
        # absent. Model is the field downstream relies on. The same keys as the
        # Thermo backend are returned so the shape is stable; missing values are
        # None. (Populating the rest needs OpenTFRaw InstID parsing -- ticket.)
        model = self._raw.instrument_model
        details = {field: None for field in INSTRUMENT_FIELDS}
        details["Model"] = model or ""
        details["Name"] = model or ""
        details["IsValid"] = model is not None
        return details

    def scan_acquisition_settings(
        self,
        polarity: Polarity | None = None,
        t_min: float | None = None,
        t_max: float | None = None,
        ms_type: MsType | None = "Ms",
    ) -> dict:
        # OpenTFRaw exposes typed per-scan params rather than Thermo's
        # trailer-label table, so surface the subset OpenTFRaw decodes under
        # descriptive labels. Shape matches ThermoBackend (header_labels +
        # settings rows aligned 1:1); the label *names* differ from Thermo's.
        selected = self._selected(polarity, t_min, t_max, ms_type)
        header_labels = [label for _, label in _OTF_TRAILER_FIELDS]
        settings = {
            int(s["scan_number"]): [s.get(key) for key, _ in _OTF_TRAILER_FIELDS]
            for s in selected
        }
        return {"header_labels": header_labels, "settings": settings}

    def scan_statistics(
        self,
        polarity: Polarity | None = None,
        t_min: float | None = None,
        t_max: float | None = None,
        ms_type: MsType | None = "Ms",
    ) -> dict:
        # Map the per-scan stats OpenTFRaw decodes onto Thermo's ScanStats field
        # names. Fields OpenTFRaw does not provide (LongWavelength, Frequency,
        # PacketCount, ...) are omitted rather than faked. StartTime is in
        # minutes, matching Thermo's ScanStats.StartTime. MsType mirrors Thermo's
        # MSOrder.ToString() ("Ms" / "Ms2").
        selected = self._selected(polarity, t_min, t_max, ms_type)
        return {
            int(s["scan_number"]): {
                "TIC": float(s["total_ion_current"]),
                "StartTime": float(s["retention_time"]),
                "BasePeakMass": float(s["base_peak_mz"]),
                "BasePeakIntensity": float(s["base_peak_intensity"]),
                "LowMass": float(s["low_mz"]),
                "HighMass": float(s["high_mz"]),
                "ScanNumber": int(s["scan_number"]),
                "MsType": "Ms" if int(s["ms_level"]) == 1 else f"Ms{int(s['ms_level'])}",
            }
            for s in selected
        }

    def _require_centroid_labels(self) -> None:
        """Gap 5.1 is only closed if the installed OpenTFRaw exposes the
        per-peak label accessor. The released wheel does not, so fall back to
        ``NotImplementedError`` (the contract suite xfails) rather than an
        ``AttributeError``.
        """
        if not hasattr(self._raw, "centroid_labels"):
            raise NotImplementedError(
                "Per-peak resolution / S:N require "
                "opentfraw.RawFile.centroid_labels (gap 5.1); not available in "
                "this opentfraw build."
            )

    def _validate_mz_range(
        self, mz_min: float | None, mz_max: float | None
    ) -> tuple[float, float]:
        from mascope_thermo.thermo import InvalidRangeError

        low, high = self.mass_range()
        low = low if mz_min is None else mz_min
        high = high if mz_max is None else mz_max
        if low > high:
            raise InvalidRangeError(
                f"Invalid m/z range: mz_min={low}, mz_max={high}, "
                "where mz_min > mz_max"
            )
        return low, high

    def centroids_per_scan(
        self,
        polarity: Polarity | None = None,
        t_min: float | None = None,
        t_max: float | None = None,
        ms_type: MsType | None = None,
        mz_min: float | None = None,
        mz_max: float | None = None,
    ) -> list[dict]:
        self._require_centroid_labels()
        mz_min, mz_max = self._validate_mz_range(mz_min, mz_max)
        selected = self._selected(polarity, t_min, t_max, ms_type)

        out: list[dict] = []
        for s in selected:
            labels = self._raw.centroid_labels(int(s["scan_number"]))
            masses = np.asarray(labels["mz"], dtype=np.float64)
            intensities = np.asarray(labels["intensity"], dtype=np.float64)
            resolutions = np.asarray(labels["resolution"], dtype=np.float64)
            signal_to_noise = np.asarray(
                labels["signal_to_noise"], dtype=np.float64
            )
            # Keep only FT label peaks (finite resolution / S:N), mirroring
            # Thermo, where non-FT scans return no centroid label peaks at all.
            mask = (
                (mz_min <= masses)
                & (masses <= mz_max)
                & np.isfinite(resolutions)
                & np.isfinite(signal_to_noise)
            )
            out.append(
                {
                    "masses": masses[mask],
                    "intensities": intensities[mask],
                    "resolutions": resolutions[mask],
                    "signal_to_noise": signal_to_noise[mask],
                    "timestamp": s["retention_time"] * _SECONDS_PER_MINUTE,
                }
            )
        return out

    def average_centroids(
        self,
        scan_indices: list[int],
        ppm: int = 1,
        average: bool = False,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        # NumPy reimplementation of Thermo's AverageScans over centroids (gap
        # 5.3): pool the per-scan FT label peaks and ppm-bin them. Thermo
        # averages in profile space and re-centroids, so this is an
        # approximation -- m/z agrees to sub-ppm, intensity to a few percent,
        # resolution/S:N more coarsely (they are not used by the instrument
        # resolution fit, which reads the profile sum). See gap 5.3 notes.
        self._require_centroid_labels()
        if ppm <= 0:
            raise ValueError(f"Invalid ppm value: {ppm}. ppm must be > 0.")

        mz_parts, int_parts, res_parts, sn_parts = [], [], [], []
        for scan_number in scan_indices:
            labels = self._raw.centroid_labels(int(scan_number))
            mz = np.asarray(labels["mz"], dtype=np.float64)
            intensity = np.asarray(labels["intensity"], dtype=np.float64)
            resolution = np.asarray(labels["resolution"], dtype=np.float64)
            signal_to_noise = np.asarray(labels["signal_to_noise"], dtype=np.float64)
            keep = np.isfinite(resolution) & np.isfinite(signal_to_noise)
            mz_parts.append(mz[keep])
            int_parts.append(intensity[keep])
            res_parts.append(resolution[keep])
            sn_parts.append(signal_to_noise[keep])

        num_combined = len(scan_indices)
        mz_all = np.concatenate(mz_parts) if mz_parts else np.array([])
        int_all = np.concatenate(int_parts) if int_parts else np.array([])
        res_all = np.concatenate(res_parts) if res_parts else np.array([])
        sn_all = np.concatenate(sn_parts) if sn_parts else np.array([])

        masses, summed, (resolutions, signal_to_noise) = _ppm_bin(
            mz_all, int_all, [res_all, sn_all], ppm
        )
        intensities = summed / num_combined if (average and num_combined) else summed
        return masses, intensities, resolutions, signal_to_noise

    def centroids_meta(self) -> dict:
        self._require_centroid_labels()
        result = {"time": [], "data": []}
        for s in self._all_scans():
            labels = self._raw.centroid_labels(int(s["scan_number"]))
            mzs = np.asarray(labels["mz"], dtype=np.float64)
            intensities = np.asarray(labels["intensity"], dtype=np.float64)
            resolutions = np.asarray(labels["resolution"], dtype=np.float64)
            noises = np.asarray(labels["noise"], dtype=np.float64)

            valid = (
                np.isfinite(resolutions)
                & (resolutions > 0)
                & np.isfinite(intensities)
                & (intensities > 0)
            )
            result["time"].append(s["retention_time"] * _SECONDS_PER_MINUTE)
            result["data"].append(
                {
                    "intensities": intensities[valid].tolist(),
                    "mzs": mzs[valid].tolist(),
                    "resolutions": resolutions[valid].tolist(),
                    "noises": noises[valid].tolist(),
                }
            )
        return result

    def profile_per_scan(
        self,
        polarity: Polarity | None = None,
        t_min: float | None = None,
        t_max: float | None = None,
        ms_type: MsType | None = "Ms",
        mz_min: float | None = None,
        mz_max: float | None = None,
    ) -> tuple[list[np.ndarray], list[np.ndarray], np.ndarray]:
        if not hasattr(self._raw, "profile"):
            raise NotImplementedError(
                "Profile arrays require opentfraw.RawFile.profile (gap 5.2); "
                "not available in this opentfraw build."
            )
        mz_min, mz_max = self._validate_mz_range(mz_min, mz_max)
        selected = self._selected(polarity, t_min, t_max, ms_type)

        scan_mzs: list[np.ndarray] = []
        scan_specs: list[np.ndarray] = []
        for s in selected:
            mz, intensities = self._raw.profile(int(s["scan_number"]))
            mz = np.asarray(mz, dtype=np.float64)
            intensities = np.asarray(intensities, dtype=np.float64)
            mask = np.logical_and(mz_min <= mz, mz <= mz_max)
            scan_mzs.append(mz[mask])
            scan_specs.append(intensities[mask])
        times = np.array(
            [s["retention_time"] * _SECONDS_PER_MINUTE for s in selected]
        )
        return scan_mzs, scan_specs, times

    def average_profile(
        self,
        scan_indices: list[int],
        ppm: int = 1,
        average: bool = False,
    ) -> tuple[np.ndarray, np.ndarray, int]:
        # NumPy reimplementation of Thermo's AverageScans over profile data
        # (gap 5.3). Thermo interpolates each scan onto a common axis and
        # averages (broadening by between-scan m/z jitter), so we must
        # interpolate, not bin (binning keeps peaks ~40% too narrow). Steps:
        #   1. Output grid = the union of the selected scans' profile m/z,
        #      quantized to a fine constant-ppm grid. Quantizing collapses the
        #      millions of jitter-duplicated points into one cell per native
        #      position -> bounded, fast, and spans heterogeneous ranges.
        #   2. Linear-interpolate each scan onto the grid (0 outside its range)
        #      and sum -> reproduces Thermo's per-peak FWHM.
        #   3. Rescale to the true total (sum of per-scan point sums) so the
        #      finer-than-native grid does not inflate intensity.
        if not hasattr(self._raw, "profile"):
            raise NotImplementedError(
                "Profile arrays require opentfraw.RawFile.profile (gap 5.2); "
                "not available in this opentfraw build."
            )
        if ppm <= 0:
            raise ValueError(f"Invalid ppm value: {ppm}. ppm must be > 0.")

        mz_parts, int_parts = [], []
        for scan_number in scan_indices:
            mz, intensity = self._raw.profile(int(scan_number))
            mz = np.asarray(mz, dtype=np.float64)
            intensity = np.asarray(intensity, dtype=np.float64)
            if mz.size:
                mz_parts.append(mz)
                int_parts.append(intensity)

        num_combined = len(scan_indices)
        if not mz_parts:
            return np.array([]), np.array([]), num_combined

        mz_all = np.concatenate(mz_parts)
        lo = float(mz_all.min())
        log_step = np.log1p(_AVG_PROFILE_GRID_PPM / 1e6)
        occupied = np.unique(np.floor(np.log(mz_all / lo) / log_step).astype(np.int64))
        grid = lo * np.exp((occupied + 0.5) * log_step)

        summed = np.zeros(grid.shape, dtype=np.float64)
        total_raw = 0.0
        for mz, intensity in zip(mz_parts, int_parts):
            order = np.argsort(mz, kind="stable")
            mz_sorted, int_sorted = mz[order], intensity[order]
            total_raw += float(int_sorted.sum())
            # Interpolate only over the grid span this scan actually covers;
            # outside [mz.min, mz.max] the contribution is zero anyway. This
            # skips the (often large) empty grid regions for narrow / SIM /
            # time-windowed selections (identical result, less work).
            lo = int(np.searchsorted(grid, mz_sorted[0], side="left"))
            hi = int(np.searchsorted(grid, mz_sorted[-1], side="right"))
            if hi > lo:
                summed[lo:hi] += np.interp(grid[lo:hi], mz_sorted, int_sorted)

        grid_total = summed.sum()
        if grid_total > 0:
            summed *= total_raw / grid_total
        if average and num_combined:
            summed = summed / num_combined
        return grid, summed, num_combined

    def xic(
        self,
        mzs,
        ppm: float = 5,
        polarity: Polarity | None = None,
        t_min: float | None = None,
        t_max: float | None = None,
        ms_type: MsType | None = "Ms",
    ) -> tuple[np.ndarray, np.ndarray]:
        # NumPy reimplementation of the Thermo MassRange chromatogram (gap 5.4):
        # for each target m/z, sum the centroid intensities falling in its ppm
        # window [mz(1-ppm), mz(1+ppm)], per selected scan.
        #
        # Vectorized per scan via a sorted prefix sum: peaks in [low, high] are
        # the half-open index range [searchsorted(left), searchsorted(right)),
        # so the window sum is cumsum[right] - cumsum[left] for all targets at
        # once. Scales to "all peaks as targets" on large files.
        mzs = np.asarray(mzs, dtype=float)
        selected = self._selected(polarity, t_min, t_max, ms_type)
        lows = mzs - mzs * ppm / 1e6
        highs = mzs + mzs * ppm / 1e6

        intensities = np.zeros((len(mzs), len(selected)), dtype=np.float64)
        for j, scan in enumerate(selected):
            scan_mz = np.asarray(scan["mz"], dtype=np.float64)
            scan_int = np.asarray(scan["intensity"], dtype=np.float64)
            order = np.argsort(scan_mz)
            scan_mz = scan_mz[order]
            prefix = np.concatenate(([0.0], np.cumsum(scan_int[order])))
            left = np.searchsorted(scan_mz, lows, side="left")
            right = np.searchsorted(scan_mz, highs, side="right")
            intensities[:, j] = prefix[right] - prefix[left]

        times = np.array(
            [s["retention_time"] * _SECONDS_PER_MINUTE for s in selected]
        )
        return intensities, times

    def ms2_precursor_by_scan(
        self,
        polarity: Polarity | None = None,
        t_min: float | None = None,
        t_max: float | None = None,
    ) -> dict[int, float]:
        # Mirror the Thermo path: parse the precursor from the rendered filter
        # string. OpenTFRaw's build_filter now renders it for Exploris too once
        # the scan-event reaction is decoded (e.g. "... ms2 100.0757@hcd3.00").
        out: dict[int, float] = {}
        for s in self._selected(polarity, t_min, t_max, ms_type="Ms2"):
            scan_number = int(s["scan_number"])
            filter_string = self._raw.scan_filter(scan_number) or s.get(
                "filter_string"
            )
            if not filter_string:
                continue
            match = re.search(r"ms2 ([\d.]+)@", filter_string)
            if match:
                out[scan_number] = float(match.group(1))
        return out

    def ms2_acquisition_info(
        self,
        polarity: Polarity | None = None,
        t_min: float | None = None,
        t_max: float | None = None,
    ) -> tuple[float | None, dict[int, str]]:
        # The calibrated "HCD Energy V:" and "MS2 Isolation Width:" live in the
        # per-scan trailer (generic record), which OpenTFRaw decodes but only
        # the scan_parameters() accessor surfaces. Guard so a released wheel
        # without it still raises NotImplementedError (contract xfails).
        if not hasattr(self._raw, "scan_parameters"):
            raise NotImplementedError(
                "MS2 isolation width / calibrated HCD energy require "
                "opentfraw.RawFile.scan_parameters (the trailer accessor); not "
                "available in this opentfraw build (gap 5.1b / metadata)."
            )

        def _as_float(value) -> float:
            if isinstance(value, (int, float)):
                return float(value)
            return float(str(value).replace(",", "."))

        isolation_widths: set[float] = set()
        scan_idx_to_hcd: dict[int, str] = {}
        for s in self._selected(polarity, t_min, t_max, ms_type="Ms2"):
            scan_number = int(s["scan_number"])
            params = self._raw.scan_parameters(scan_number) or {}
            width = params.get("MS2 Isolation Width:")
            if width is not None and str(width) != "":
                # round away the f32->f64 noise so identical widths dedupe.
                isolation_widths.add(round(_as_float(width), 6))
            hcd = params.get("HCD Energy V:")
            scan_idx_to_hcd[scan_number] = "" if hcd is None else str(hcd)

        isolation_widths.discard(None)
        if len(isolation_widths) == 1:
            isolation_width = float(isolation_widths.pop())
        else:
            raise ValueError("Multiple isolation widths found for MS2 scans.")
        return isolation_width, scan_idx_to_hcd

    def ms2_centroids_for_scans(self, *args, **kwargs):
        raise NotImplementedError(
            "Per-peak resolution / S:N are not decoded by OpenTFRaw (gap 5.1)."
        )


def open_backend(datafile_path: str) -> ReaderBackend:
    """Open ``datafile_path`` with the backend selected by ``MASCOPE_THERMO_BACKEND``.

    Returns a context manager. Defaults to the Thermo backend, preserving today's
    behaviour when the variable is unset.
    """
    name = os.environ.get(ENV_BACKEND, "thermo").lower()
    if name == "thermo":
        return ThermoBackend(datafile_path)
    if name == "opentfraw":
        return OpenTFRawBackend(datafile_path)
    raise ValueError(
        f"Unknown {ENV_BACKEND}={name!r}; expected 'thermo' or 'opentfraw'."
    )
