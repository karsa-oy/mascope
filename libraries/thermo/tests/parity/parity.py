"""Phase 0 parity harness: Thermo RawFileReader vs OpenTFRaw.

This is a *proof-of-concept validation* tool, not production code. Its job is to
quantify how closely the open-source OpenTFRaw reader reproduces the numbers the
current Thermo-backed ``mascope_thermo`` pipeline relies on, so we can make an
evidence-based go/no-go call before investing in the migration.

It is deliberately **agnostic to which files are present**: point it at a
directory and it discovers every ``*.raw`` file and compares both backends on
each one.

What it compares, per scan (centroids only — see "Known gaps" below):
  - scan count
  - retention time (minutes)
  - polarity, MS level
  - total ion current (TIC), base peak m/z + intensity
  - filter string (string-equality rate; formatting may legitimately differ)
  - centroid peaks: count, matched fraction within a ppm tolerance, and the
    m/z (ppm) and intensity (relative) deviation of matched peaks

Known gaps this harness will surface but cannot bridge (OpenTFRaw 1.1.0):
  - No per-peak resolution / signal-to-noise / noise (Thermo provides them).
  - No profile / segmented-spectrum arrays exposed to Python (centroids only).
  - No multi-scan ppm averaging, no arbitrary-m/z XIC.

Both backends only run where their dependencies exist:
  - Thermo: ``pythonnet`` + the bundled .NET DLLs (Windows / .NET runtime).
  - OpenTFRaw: ``pip install opentfraw`` (wheels for Win/Linux/macOS).

Run from the repository root (so the Thermo DLL loader resolves its relative
path):

    python -m libraries.thermo.tests.parity.parity            # default dir
    python -m libraries.thermo.tests.parity.parity <dir> --json out.json --md out.md
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np


# Default location of the checked-in sample files. Override on the CLI.
DEFAULT_RAW_DIR = Path(__file__).resolve().parents[1] / "test_files"

# Tolerances used for the human-readable PASS/WARN summary. The pytest layer has
# its own (see test_parity.py); these are intentionally generous because Phase 0
# is about *measuring* deviation, not enforcing a contract yet.
PEAK_MATCH_PPM = 2.0  # m/z window for calling two centroids "the same"
RT_TOL_MIN = 1e-3  # acceptable retention-time delta (minutes)
TIC_REL_TOL = 0.02  # acceptable median relative TIC error
MATCH_FRACTION_WARN = 0.95  # warn if fewer than this fraction of peaks match

# MS² / trailer-metadata tolerances. These drive the parent-grouping, HCD-energy
# and isolation-width contracts that `get_ms2_centroids_by_parent` and
# `get_ms2_summary_metadata` rely on (see assessment §2 and §5).
PRECURSOR_PPM_TOL = 5.0  # precursor m/z agreement (filter value is rounded to 4 dp)
ISOLATION_WIDTH_TOL = 0.05  # Da
COLLISION_ENERGY_TOL = 0.1  # nominal HCD energy units (the value shown in the filter)
INJECTION_TIME_REL_TOL = 0.01  # relative


# --------------------------------------------------------------------------- #
# Data containers
# --------------------------------------------------------------------------- #
@dataclass
class ScanRecord:
    """Backend-neutral view of a single scan."""

    scan_number: int
    rt_min: float
    tic: float
    base_mz: float
    base_intensity: float
    polarity: str  # "+" / "-" / ""
    ms_level: int
    filter_string: str | None
    mz: np.ndarray  # centroid m/z (float64), ascending
    intensity: np.ndarray  # centroid intensity (float64)
    # MS² / trailer metadata. None where the scan isn't MS² or the backend does
    # not expose the field. These back the MS²-workflow contract that the
    # migration must preserve (parent grouping, HCD energy, isolation width).
    precursor_mz: float | None = None
    isolation_width: float | None = None
    # Nominal HCD energy as shown in the filter ("@hcd3.00") / Thermo's
    # "HCD Energy:" trailer — this is what OpenTFRaw's `collision_energy` reports.
    collision_energy: float | None = None
    injection_time_ms: float | None = None
    charge: int | None = None
    # Thermo-only extras (None for OpenTFRaw) — used purely to *demonstrate* the
    # gap quantitatively in the report.
    has_resolution: bool = False
    # Thermo-only: the "HCD Energy V:" trailer value that `get_ms2_summary_metadata`
    # currently reads. OpenTFRaw does NOT expose this calibrated-voltage quantity
    # (it gives the nominal energy above instead), so this is a separate gap.
    hcd_energy_v: float | None = None


@dataclass
class FileRead:
    backend: str
    path: str
    num_scans: int
    low_mass: float
    high_mass: float
    scans: list[ScanRecord] = field(default_factory=list)
    # Instrument / sample metadata. OpenTFRaw 1.1.0 exposes only the model; the
    # rest of `instrument_details` (serial, software/hardware version, method
    # file, creation date) has no Python accessor yet — tracked as gaps.
    instrument_model: str | None = None
    # Whether the backend can hand back profile / SegmentedScan arrays. Thermo
    # can; OpenTFRaw's Python bindings return centroids only (gap 5.2).
    has_profile: bool = False


# --------------------------------------------------------------------------- #
# Small parsing helpers (shared by both backends)
# --------------------------------------------------------------------------- #
def _to_float(value: Any) -> float | None:
    """Parse a possibly-locale-formatted ('0,40') / None / '' value to float."""
    if value is None:
        return None
    s = str(value).strip().replace(",", ".")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _to_int(value: Any) -> int | None:
    f = _to_float(value)
    return int(round(f)) if f is not None else None


def _models_compatible(a: str | None, b: str | None) -> bool:
    """Best-effort instrument-model match: True if either normalized name
    contains the other (handles 'Q Exactive Plus' vs 'Q Exactive Plus Orbitrap').
    """
    if not a or not b:
        return False
    na, nb = a.strip().casefold(), b.strip().casefold()
    return na in nb or nb in na


# --------------------------------------------------------------------------- #
# Thermo backend (reference)
# --------------------------------------------------------------------------- #
def read_thermo(path: str) -> FileRead:
    """Read a .raw file through the current Thermo / pythonnet stack.

    Importing ``mascope_thermo`` triggers ``load_dotnet`` which registers the
    bundled CLR assemblies, after which the ``ThermoFisher.CommonCore`` namespaces
    are importable. Mirrors exactly how ``thermo.py`` reads scans.
    """
    # Import mascope_thermo FIRST: its side effect (load_dotnet) registers the
    # CLR assemblies, without which `System` / `ThermoFisher.CommonCore` are not
    # importable. Order matters when this module is run on its own.
    import mascope_thermo
    from mascope_thermo.thermo import RawFileManager

    # Load-bearing barrier: a non-import statement here stops the linter's isort
    # rule from hoisting the CLR imports above the side-effecting import above.
    assert mascope_thermo  # noqa: S101

    from System.Collections.Generic import List
    from ThermoFisher.CommonCore.Data import Extensions

    with RawFileManager(path) as rf:
        header = rf.RunHeaderEx
        n = header.SpectraCount

        indices = List[int]()
        for i in range(1, n + 1):
            indices.Add(i)
        scans = list(Extensions.GetScans(rf, indices))

        records: list[ScanRecord] = []
        for i in range(1, n + 1):
            stats = rf.GetScanStatsForScanNumber(i)
            scan_filter = rf.GetFilterForScanNumber(i)
            scan = scans[i - 1]

            mz_list: list[float] = []
            int_list: list[float] = []
            has_res = False
            centroid = scan.CentroidScan
            if centroid is not None and centroid.Length > 0:
                for peak in centroid.GetLabelPeaks():
                    mz_list.append(float(peak.Mass))
                    int_list.append(float(peak.Intensity))
                has_res = True  # Thermo exposes Resolution + SignalToNoise here

            mz = np.asarray(mz_list, dtype=np.float64)
            inten = np.asarray(int_list, dtype=np.float64)
            order = np.argsort(mz)
            mz, inten = mz[order], inten[order]

            filter_str = str(scan_filter.ToString())
            polarity = "+" if scan_filter.Polarity.ToString() == "Positive" else "-"
            ms_level = _ms_order_to_level(scan_filter.MSOrder.ToString())

            # Trailer-extra table (label -> value), as used by thermo.py.
            trailer = rf.GetTrailerExtraInformation(i)
            trailer_map = dict(zip(list(trailer.Labels), list(trailer.Values)))

            # MS² precursor m/z: parsed from the filter exactly as
            # `_group_ms2_scans_by_parent` does (`ms2 <mz>@`).
            precursor_mz = None
            collision_energy = None
            if ms_level >= 2:
                m_prec = re.search(r"ms2 ([\d.]+)@", filter_str)
                if m_prec:
                    precursor_mz = float(m_prec.group(1))
                # Nominal HCD energy from the filter ("@hcd3.00"), falling back to
                # the "HCD Energy:" trailer; this is what OpenTFRaw exposes.
                m_hcd = re.search(r"@hcd([\d.]+)", filter_str)
                collision_energy = (
                    float(m_hcd.group(1))
                    if m_hcd
                    else _to_float(trailer_map.get("HCD Energy:"))
                )

            records.append(
                ScanRecord(
                    scan_number=i,
                    rt_min=float(stats.StartTime),
                    tic=float(stats.TIC),
                    base_mz=float(stats.BasePeakMass),
                    base_intensity=float(stats.BasePeakIntensity),
                    polarity=polarity,
                    ms_level=ms_level,
                    filter_string=filter_str,
                    mz=mz,
                    intensity=inten,
                    precursor_mz=precursor_mz,
                    isolation_width=(
                        _to_float(trailer_map.get("MS2 Isolation Width:"))
                        if ms_level >= 2
                        else None
                    ),
                    collision_energy=collision_energy,
                    injection_time_ms=_to_float(
                        trailer_map.get("Ion Injection Time (ms):")
                    ),
                    charge=_to_int(trailer_map.get("Charge State:")),
                    has_resolution=has_res,
                    hcd_energy_v=(
                        _to_float(trailer_map.get("HCD Energy V:"))
                        if ms_level >= 2
                        else None
                    ),
                )
            )

        model = rf.GetInstrumentData().Model

        return FileRead(
            backend="thermo",
            path=path,
            num_scans=n,
            low_mass=float(header.LowMass),
            high_mass=float(header.HighMass),
            scans=records,
            instrument_model=str(model) if model is not None else None,
            has_profile=True,  # Thermo exposes SegmentedScan profile arrays
        )


def _ms_order_to_level(ms_order: str) -> int:
    """'Ms' -> 1, 'Ms2' -> 2, 'Ms3' -> 3, ..."""
    m = re.search(r"(\d+)", ms_order or "")
    if m:
        return int(m.group(1))
    return 1  # 'Ms' has no digit


# --------------------------------------------------------------------------- #
# OpenTFRaw backend (candidate)
# --------------------------------------------------------------------------- #
def read_opentfraw(path: str) -> FileRead:
    """Read a .raw file through OpenTFRaw's Python bindings (centroids only)."""
    import opentfraw

    raw = opentfraw.RawFile(path)
    records: list[ScanRecord] = []
    low = np.inf
    high = -np.inf
    has_profile = False  # flipped if a future build exposes profile arrays

    for s in raw.iter_scans():
        mz = np.asarray(s["mz"], dtype=np.float64)
        inten = np.asarray(s["intensity"], dtype=np.float64)
        order = np.argsort(mz)
        mz, inten = mz[order], inten[order]

        low = min(low, float(s["low_mz"]))
        high = max(high, float(s["high_mz"]))

        # Future-proof capability sniffing: these keys don't exist in 1.1.0, but
        # if a later release adds them the corresponding xfail tests flip to pass.
        keys = {k.lower() for k in s}
        has_profile = has_profile or bool(
            keys & {"profile", "profile_mz", "positions", "segmented_scan"}
        )
        has_res = bool(keys & {"resolution", "resolutions"})

        ms_level = int(s["ms_level"])
        records.append(
            ScanRecord(
                scan_number=int(s["scan_number"]),
                rt_min=float(s["retention_time"]),
                tic=float(s["total_ion_current"]),
                base_mz=float(s["base_peak_mz"]),
                base_intensity=float(s["base_peak_intensity"]),
                polarity=str(s["polarity"]),
                ms_level=ms_level,
                filter_string=s["filter_string"],
                mz=mz,
                intensity=inten,
                # OpenTFRaw reports isolation_width even for MS1 (the full scan
                # window); only keep it for MS² so it compares like-for-like.
                precursor_mz=_to_float(s.get("precursor_mz")),
                isolation_width=(
                    _to_float(s.get("isolation_width")) if ms_level >= 2 else None
                ),
                collision_energy=_to_float(s.get("collision_energy")),
                injection_time_ms=_to_float(s.get("ion_injection_time_ms")),
                charge=_to_int(s.get("charge")),
                has_resolution=has_res,
                hcd_energy_v=None,  # not exposed by OpenTFRaw — see ScanRecord
            )
        )

    model = getattr(raw, "instrument_model", None)

    return FileRead(
        backend="opentfraw",
        path=path,
        num_scans=int(raw.num_scans),
        low_mass=low if np.isfinite(low) else float("nan"),
        high_mass=high if np.isfinite(high) else float("nan"),
        scans=records,
        instrument_model=str(model) if model is not None else None,
        has_profile=has_profile,
    )


# --------------------------------------------------------------------------- #
# Comparison
# --------------------------------------------------------------------------- #
def match_peaks(
    mz_ref: np.ndarray,
    int_ref: np.ndarray,
    mz_cmp: np.ndarray,
    int_cmp: np.ndarray,
    ppm: float = PEAK_MATCH_PPM,
) -> dict[str, float]:
    """Greedy nearest-neighbour match of two centroid lists within ``ppm``.

    Returns matched fraction (relative to the reference) and the m/z (ppm) and
    intensity (relative) deviation distribution over matched pairs.
    """
    out = {
        "n_ref": int(mz_ref.size),
        "n_cmp": int(mz_cmp.size),
        "n_matched": 0,
        "matched_frac_ref": 0.0,
        "median_abs_ppm": float("nan"),
        "max_abs_ppm": float("nan"),
        "median_int_rel_err": float("nan"),
        "max_int_rel_err": float("nan"),
    }
    if mz_ref.size == 0 or mz_cmp.size == 0:
        return out

    # mz_cmp is sorted ascending (ensured by the readers).
    idx = np.searchsorted(mz_cmp, mz_ref)
    idx = np.clip(idx, 0, mz_cmp.size - 1)
    left = np.clip(idx - 1, 0, mz_cmp.size - 1)

    cand = np.where(
        np.abs(mz_cmp[idx] - mz_ref) <= np.abs(mz_cmp[left] - mz_ref),
        idx,
        left,
    )
    nearest_mz = mz_cmp[cand]
    ppm_diff = (nearest_mz - mz_ref) / mz_ref * 1e6
    matched = np.abs(ppm_diff) <= ppm

    n_matched = int(np.count_nonzero(matched))
    out["n_matched"] = n_matched
    out["matched_frac_ref"] = n_matched / mz_ref.size
    if n_matched:
        mp = np.abs(ppm_diff[matched])
        out["median_abs_ppm"] = float(np.median(mp))
        out["max_abs_ppm"] = float(np.max(mp))

        ref_i = int_ref[matched]
        cmp_i = int_cmp[cand][matched]
        with np.errstate(divide="ignore", invalid="ignore"):
            rel = np.abs(cmp_i - ref_i) / np.where(ref_i != 0, ref_i, np.nan)
        rel = rel[np.isfinite(rel)]
        if rel.size:
            out["median_int_rel_err"] = float(np.median(rel))
            out["max_int_rel_err"] = float(np.max(rel))
    return out


def compare_file(thermo: FileRead, otf: FileRead) -> dict[str, Any]:
    """Compare two reads of the same file. Returns a JSON-serialisable summary."""
    summary: dict[str, Any] = {
        "file": Path(thermo.path).name,
        "thermo_num_scans": thermo.num_scans,
        "opentfraw_num_scans": otf.num_scans,
        "scan_count_match": thermo.num_scans == otf.num_scans,
        "thermo_mass_range": [thermo.low_mass, thermo.high_mass],
        "opentfraw_mass_range": [otf.low_mass, otf.high_mass],
        "thermo_has_resolution": any(s.has_resolution for s in thermo.scans),
        "opentfraw_has_resolution": any(s.has_resolution for s in otf.scans),
        "thermo_has_profile": thermo.has_profile,
        "opentfraw_has_profile": otf.has_profile,
        "thermo_instrument_model": thermo.instrument_model,
        "opentfraw_instrument_model": otf.instrument_model,
        # OpenTFRaw's model is "best-effort" and often a shortened form (e.g.
        # "Q Exactive Plus" vs Thermo's "Q Exactive Plus Orbitrap"), so accept a
        # normalized containment match rather than strict equality.
        "instrument_model_match": _models_compatible(
            thermo.instrument_model, otf.instrument_model
        ),
    }

    n = min(len(thermo.scans), len(otf.scans))
    polarity_mismatches: list[int] = []
    mslevel_mismatches: list[int] = []
    filter_matches = 0
    rt_abs_diffs: list[float] = []
    tic_rel_errs: list[float] = []
    base_ppm: list[float] = []
    matched_fracs: list[float] = []
    median_ppms: list[float] = []
    median_int_errs: list[float] = []
    peakcount_ratio: list[float] = []

    # MS² metadata (collected over MS² scans only).
    ms2_count = 0
    prec_thermo_count = 0  # MS² scans where Thermo has a precursor m/z
    prec_otf_count = 0  # ...and where OpenTFRaw also reports one
    prec_otf_missing = 0  # Thermo has it, OpenTFRaw does not (the gap)
    prec_ppms: list[float] = []
    iso_diffs: list[float] = []
    iso_mismatch = 0
    energy_diffs: list[float] = []
    energy_mismatch = 0
    # Injection time / charge (apply to all scan levels).
    inj_rel_errs: list[float] = []
    charge_compared = 0
    charge_mismatch = 0

    for k in range(n):
        a, b = thermo.scans[k], otf.scans[k]

        if a.polarity != b.polarity:
            polarity_mismatches.append(a.scan_number)
        if a.ms_level != b.ms_level:
            mslevel_mismatches.append(a.scan_number)

        # ---- MS² metadata parity (precursor / isolation / energy) ----
        if a.ms_level >= 2:
            ms2_count += 1
            if a.precursor_mz is not None:
                prec_thermo_count += 1
                if b.precursor_mz is not None:
                    prec_otf_count += 1
                    prec_ppms.append(
                        abs(b.precursor_mz - a.precursor_mz) / a.precursor_mz * 1e6
                    )
                else:
                    prec_otf_missing += 1
            if a.isolation_width is not None and b.isolation_width is not None:
                d = abs(a.isolation_width - b.isolation_width)
                iso_diffs.append(d)
                if d > ISOLATION_WIDTH_TOL:
                    iso_mismatch += 1
            if a.collision_energy is not None and b.collision_energy is not None:
                d = abs(a.collision_energy - b.collision_energy)
                energy_diffs.append(d)
                if d > COLLISION_ENERGY_TOL:
                    energy_mismatch += 1

        # ---- Injection time / charge (all scans) ----
        if a.injection_time_ms and b.injection_time_ms is not None:
            inj_rel_errs.append(
                abs(a.injection_time_ms - b.injection_time_ms) / a.injection_time_ms
            )
        if a.charge is not None and b.charge is not None and a.charge and b.charge:
            charge_compared += 1
            if a.charge != b.charge:
                charge_mismatch += 1
        if (
            a.filter_string
            and b.filter_string
            and a.filter_string.strip() == b.filter_string.strip()
        ):
            filter_matches += 1

        rt_abs_diffs.append(abs(a.rt_min - b.rt_min))
        if a.tic:
            tic_rel_errs.append(abs(a.tic - b.tic) / a.tic)
        if a.base_mz:
            base_ppm.append(abs(a.base_mz - b.base_mz) / a.base_mz * 1e6)

        m = match_peaks(a.mz, a.intensity, b.mz, b.intensity)
        matched_fracs.append(m["matched_frac_ref"])
        if not np.isnan(m["median_abs_ppm"]):
            median_ppms.append(m["median_abs_ppm"])
        if not np.isnan(m["median_int_rel_err"]):
            median_int_errs.append(m["median_int_rel_err"])
        if a.mz.size:
            peakcount_ratio.append(b.mz.size / a.mz.size)

    def _stat(xs: list[float], fn) -> float:
        return float(fn(xs)) if xs else float("nan")

    summary.update(
        {
            "compared_scans": n,
            "polarity_mismatch_count": len(polarity_mismatches),
            "polarity_mismatch_scans": polarity_mismatches[:20],
            "ms_level_mismatch_count": len(mslevel_mismatches),
            "ms_level_mismatch_scans": mslevel_mismatches[:20],
            "filter_string_match_rate": (filter_matches / n) if n else float("nan"),
            "rt_max_abs_diff_min": _stat(rt_abs_diffs, np.max),
            "tic_median_rel_err": _stat(tic_rel_errs, np.median),
            "tic_max_rel_err": _stat(tic_rel_errs, np.max),
            "base_peak_median_ppm": _stat(base_ppm, np.median),
            "peak_matched_frac_median": _stat(matched_fracs, np.median),
            "peak_matched_frac_min": _stat(matched_fracs, np.min),
            "peak_median_ppm": _stat(median_ppms, np.median),
            "peak_intensity_median_rel_err": _stat(median_int_errs, np.median),
            "peakcount_ratio_median": _stat(peakcount_ratio, np.median),
            # ---- MS² metadata ----
            "ms2_scan_count": ms2_count,
            "precursor_thermo_count": prec_thermo_count,
            "precursor_opentfraw_count": prec_otf_count,
            "precursor_opentfraw_missing_count": prec_otf_missing,
            "precursor_median_ppm": _stat(prec_ppms, np.median),
            "precursor_max_ppm": _stat(prec_ppms, np.max),
            "isolation_width_max_abs_diff": _stat(iso_diffs, np.max),
            "isolation_width_mismatch_count": iso_mismatch,
            "collision_energy_max_abs_diff": _stat(energy_diffs, np.max),
            "collision_energy_mismatch_count": energy_mismatch,
            # Production reads the "HCD Energy V:" trailer, which OpenTFRaw does
            # not expose (it gives the nominal energy compared above instead).
            "hcd_energy_v_in_opentfraw": any(
                s.hcd_energy_v is not None for s in otf.scans
            ),
            # ---- injection time / charge ----
            "injection_time_median_rel_err": _stat(inj_rel_errs, np.median),
            "injection_time_max_rel_err": _stat(inj_rel_errs, np.max),
            "charge_compared_count": charge_compared,
            "charge_mismatch_count": charge_mismatch,
        }
    )

    # Heuristic verdict for the at-a-glance report.
    warns: list[str] = []
    if not summary["scan_count_match"]:
        warns.append("scan count differs")
    if summary["polarity_mismatch_count"]:
        warns.append("polarity mismatches")
    if summary["ms_level_mismatch_count"]:
        warns.append("MS-level mismatches")
    if summary["rt_max_abs_diff_min"] > RT_TOL_MIN:
        warns.append("retention-time drift")
    if summary["tic_median_rel_err"] > TIC_REL_TOL:
        warns.append("TIC deviation")
    if summary["peak_matched_frac_median"] < MATCH_FRACTION_WARN:
        warns.append("low peak-match fraction")
    if summary["precursor_opentfraw_missing_count"]:
        warns.append("MS² precursor m/z unavailable in OpenTFRaw")
    if summary["isolation_width_mismatch_count"]:
        warns.append("isolation-width mismatches")
    if summary["collision_energy_mismatch_count"]:
        warns.append("HCD-energy mismatches")
    if (
        not np.isnan(summary["injection_time_max_rel_err"])
        and summary["injection_time_max_rel_err"] > INJECTION_TIME_REL_TOL
    ):
        warns.append("injection-time deviation")
    if summary["charge_mismatch_count"]:
        warns.append("charge-state mismatches")
    if (
        summary["thermo_instrument_model"]
        and summary["opentfraw_instrument_model"]
        and not summary["instrument_model_match"]
    ):
        warns.append("instrument-model mismatch")
    summary["verdict"] = "PASS" if not warns else "WARN: " + "; ".join(warns)
    return summary


# --------------------------------------------------------------------------- #
# Orchestration + reporting
# --------------------------------------------------------------------------- #
def discover_raw_files(directory: Path) -> list[Path]:
    return sorted(p for p in directory.glob("*.raw") if p.is_file())


def run_parity(directory: Path) -> list[dict[str, Any]]:
    files = discover_raw_files(directory)
    if not files:
        raise FileNotFoundError(f"No .raw files found in {directory}")

    results: list[dict[str, Any]] = []
    for f in files:
        thermo = read_thermo(str(f))
        otf = read_opentfraw(str(f))
        results.append(compare_file(thermo, otf))
    return results


def render_markdown(results: list[dict[str, Any]]) -> str:
    lines = ["# OpenTFRaw vs Thermo — Phase 0 parity report", ""]
    lines.append(
        "Per-scan comparison: centroids, retention time, polarity/MS level, TIC, "
        "base peak, filter strings, plus MS² metadata (precursor m/z, isolation "
        "width, HCD energy), injection time and charge state.\n\n"
        "Known structural gaps OpenTFRaw 1.1.0 cannot bridge (surfaced as ← gap): "
        "no per-peak resolution/S:N, no MS² precursor m/z (so parent grouping can't "
        "be reproduced), no calibrated 'HCD Energy V:', and no profile arrays "
        "exposed to Python. Multi-scan ppm averaging and arbitrary-m/z XIC have no "
        "OpenTFRaw equivalent and must be reimplemented and tested separately.\n"
    )
    for r in results:
        lines.append(f"## {r['file']} — {r['verdict']}")
        lines.append("")
        lines.append(
            f"- scans: thermo={r['thermo_num_scans']} opentfraw={r['opentfraw_num_scans']} "
            f"(match={r['scan_count_match']})"
        )
        lines.append(
            f"- polarity mismatches: {r['polarity_mismatch_count']}; "
            f"MS-level mismatches: {r['ms_level_mismatch_count']}"
        )
        lines.append(
            f"- filter-string exact-match rate: {r['filter_string_match_rate']:.3f}"
        )
        lines.append(
            f"- retention time: max abs diff = {r['rt_max_abs_diff_min']:.2e} min"
        )
        lines.append(
            f"- TIC: median rel err = {r['tic_median_rel_err']:.2e}, "
            f"max = {r['tic_max_rel_err']:.2e}"
        )
        lines.append(f"- base peak m/z: median = {r['base_peak_median_ppm']:.2f} ppm")
        lines.append(
            f"- centroid match fraction: median = {r['peak_matched_frac_median']:.3f}, "
            f"min = {r['peak_matched_frac_min']:.3f}"
        )
        lines.append(f"- matched-peak m/z: median = {r['peak_median_ppm']:.2f} ppm")
        lines.append(
            f"- matched-peak intensity: median rel err = {r['peak_intensity_median_rel_err']:.2e}"
        )
        lines.append(
            f"- peak-count ratio (otf/thermo): median = {r['peakcount_ratio_median']:.3f}"
        )
        lines.append(
            f"- resolution/S:N available — thermo={r['thermo_has_resolution']}, "
            f"opentfraw={r['opentfraw_has_resolution']}  ← gap"
        )
        if r["ms2_scan_count"]:
            lines.append(f"- **MS² scans: {r['ms2_scan_count']}**")
            lines.append(
                f"  - precursor m/z: thermo={r['precursor_thermo_count']}, "
                f"opentfraw={r['precursor_opentfraw_count']}, "
                f"missing in opentfraw={r['precursor_opentfraw_missing_count']}"
                + (
                    "  ← gap"
                    if r["precursor_opentfraw_missing_count"]
                    else f" (median {r['precursor_median_ppm']:.2f} ppm)"
                )
            )
            lines.append(
                f"  - isolation width: max abs diff = "
                f"{r['isolation_width_max_abs_diff']:.3g} Da, "
                f"mismatches = {r['isolation_width_mismatch_count']}"
            )
            lines.append(
                f"  - HCD energy (nominal): max abs diff = "
                f"{r['collision_energy_max_abs_diff']:.3g}, "
                f"mismatches = {r['collision_energy_mismatch_count']}"
            )
            lines.append(
                f"  - 'HCD Energy V:' (calibrated) available in opentfraw: "
                f"{r['hcd_energy_v_in_opentfraw']}  ← gap"
            )
        lines.append(
            f"- injection time: median rel err = "
            f"{r['injection_time_median_rel_err']:.2e}, "
            f"max = {r['injection_time_max_rel_err']:.2e}"
        )
        lines.append(
            f"- charge state: compared {r['charge_compared_count']}, "
            f"mismatches = {r['charge_mismatch_count']}"
        )
        lines.append(
            f"- instrument model: thermo={r['thermo_instrument_model']!r}, "
            f"opentfraw={r['opentfraw_instrument_model']!r} "
            f"(match={r['instrument_model_match']})"
        )
        lines.append(
            f"- profile/SegmentedScan arrays — thermo={r['thermo_has_profile']}, "
            f"opentfraw={r['opentfraw_has_profile']}  ← gap"
        )
        lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Thermo vs OpenTFRaw parity check")
    ap.add_argument(
        "directory",
        nargs="?",
        default=str(DEFAULT_RAW_DIR),
        help="Directory containing .raw files (default: bundled test_files)",
    )
    ap.add_argument("--json", help="Write the raw comparison summary to this JSON path")
    ap.add_argument("--md", help="Write a human-readable markdown report to this path")
    args = ap.parse_args(argv)

    results = run_parity(Path(args.directory))

    report = render_markdown(results)
    print(report)

    if args.json:
        Path(args.json).write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"\nWrote JSON summary -> {args.json}")
    if args.md:
        Path(args.md).write_text(report, encoding="utf-8")
        print(f"Wrote markdown report -> {args.md}")

    # Non-zero exit if any file failed the heuristic verdict, for CI use.
    return 0 if all(r["verdict"] == "PASS" for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
