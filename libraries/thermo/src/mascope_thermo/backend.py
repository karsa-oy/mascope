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

    # -- not yet available (raise NotImplementedError → contract tests xfail) --

    def instrument_details(self) -> dict:
        raise NotImplementedError(
            "OpenTFRaw exposes only instrument_model, not the full instrument "
            "details table (Phase 4 metadata remap)."
        )

    def scan_acquisition_settings(self, *args, **kwargs) -> dict:
        raise NotImplementedError(
            "Per-scan trailer table is not exposed by OpenTFRaw (Phase 4)."
        )

    def scan_statistics(self, *args, **kwargs) -> dict:
        raise NotImplementedError(
            "Thermo scan-statistics fields are not exposed by OpenTFRaw (Phase 4)."
        )

    def centroids_per_scan(self, *args, **kwargs) -> list[dict]:
        raise NotImplementedError(
            "Per-peak resolution / S:N are not decoded by OpenTFRaw (gap 5.1)."
        )

    def average_centroids(self, *args, **kwargs):
        raise NotImplementedError(
            "ppm-binned centroid averaging not yet reimplemented (gap 5.3, step 5)."
        )

    def centroids_meta(self) -> dict:
        raise NotImplementedError(
            "Per-peak resolution / noise are not decoded by OpenTFRaw (gap 5.1)."
        )

    def profile_per_scan(self, *args, **kwargs):
        raise NotImplementedError(
            "Profile / SegmentedScan arrays are not exposed by OpenTFRaw (gap 5.2)."
        )

    def average_profile(self, *args, **kwargs):
        raise NotImplementedError(
            "Profile + ppm averaging not yet available (gaps 5.2 / 5.3)."
        )

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
        # window, per selected scan.
        mzs = np.asarray(mzs, dtype=float)
        selected = self._selected(polarity, t_min, t_max, ms_type)
        lows = mzs - mzs * ppm / 1e6
        highs = mzs + mzs * ppm / 1e6

        intensities = np.zeros((len(mzs), len(selected)), dtype=np.float64)
        for j, scan in enumerate(selected):
            scan_mz = np.asarray(scan["mz"], dtype=np.float64)
            scan_int = np.asarray(scan["intensity"], dtype=np.float64)
            for i in range(len(mzs)):
                in_window = (scan_mz >= lows[i]) & (scan_mz <= highs[i])
                intensities[i, j] = scan_int[in_window].sum()

        times = np.array(
            [s["retention_time"] * _SECONDS_PER_MINUTE for s in selected]
        )
        return intensities, times

    def ms2_precursor_by_scan(self, *args, **kwargs) -> dict[int, float]:
        raise NotImplementedError(
            "MS² precursor m/z is returned as None by OpenTFRaw (gap 5.1b)."
        )

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
