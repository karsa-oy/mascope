"""Cross-backend numerical parity for reimplemented computed ops.

Where OpenTFRaw needs a NumPy reimplementation of a Thermo-computed operation
(assessment gaps 5.3 / 5.4), the dual-backend contract suite only checks the
*shape* of the result. These tests pin the *values*: run the same public
function under both backends and assert agreement. This is the evidence that a
reimplementation actually reproduces Thermo's numbers, not just its structure.

File-agnostic, like the parity harness: every ``*.raw`` in ``test_files/`` is
compared (only the KORBI files are committed; drop in more locally for wider
coverage). Both backends (pythonnet + opentfraw) are runtime dependencies of
``mascope_thermo``, so they're assumed importable.

Targets are sampled *evenly across the m/z range* rather than "all peaks": a
full Orbitrap file can have hundreds of thousands of averaged centroids, and
``get_peak_timeseries`` issues one Thermo ``GetChromatogramData`` trace per
target — so all-peaks is O(100k traces x scans) and takes tens of minutes. An
even spread (capped at ``MASCOPE_PARITY_MAX_XIC_TARGETS``, default 200) covers
the whole m/z range and varied peak densities in a second or two per file.
"""

import os

import numpy as np
import opentfraw
import pytest
from conftest import TEST_FILES_DIR

import mascope_thermo.thermo as m_thermo
from mascope_thermo.backend import open_backend


RAW_FILES = sorted(TEST_FILES_DIR.glob("*.raw"))

# Cap on XIC targets per file (even spread across m/z). Override to widen
# coverage (e.g. MASCOPE_PARITY_MAX_XIC_TARGETS=1000) at the cost of runtime.
MAX_XIC_TARGETS = int(os.environ.get("MASCOPE_PARITY_MAX_XIC_TARGETS", "200"))

# Profile parity needs an opentfraw build that exposes RawFile.profile(). The
# published 1.1.0 wheel does not; a maturin build of the accessor branch does.
_OTF_HAS_PROFILE = hasattr(opentfraw.RawFile, "profile")

# Per-peak label parity (resolution / S:N) needs an opentfraw build exposing
# RawFile.centroid_labels(). Same story as profile: a maturin build of the
# decoder branch, not the published wheel.
_OTF_HAS_LABELS = hasattr(opentfraw.RawFile, "centroid_labels")


def _run_under(monkeypatch, backend, fn, *args, **kwargs):
    monkeypatch.setenv("MASCOPE_THERMO_BACKEND", backend)
    return fn(*args, **kwargs)


def _num_of_scans(path):
    return m_thermo.RawFileMetadataLegacy(path).num_of_scans


@pytest.mark.skipif(not RAW_FILES, reason="no .raw files in test_files/")
@pytest.mark.parametrize("path", RAW_FILES, ids=lambda p: p.name)
def test_xic_matches_thermo(monkeypatch, path):
    """OpenTFRaw's NumPy XIC must reproduce Thermo's MassRange chromatogram for
    targets spanning the file's full m/z range, across all MS1 scans.
    """
    path = str(path)

    # Source real targets from the averaged centroids, then sample an even
    # spread across the sorted m/z range.
    monkeypatch.setenv("MASCOPE_THERMO_BACKEND", "thermo")
    masses, _, _, _ = m_thermo.get_centroids(path)
    if masses.size == 0:
        pytest.skip("no centroids to target")
    masses = np.sort(masses)
    idx = np.unique(
        np.linspace(0, masses.size - 1, min(MAX_XIC_TARGETS, masses.size)).astype(int)
    )
    targets = masses[idx]

    thermo_xic = _run_under(
        monkeypatch, "thermo", m_thermo.get_peak_timeseries, path, targets
    ).values
    otf_xic = _run_under(
        monkeypatch, "opentfraw", m_thermo.get_peak_timeseries, path, targets
    ).values

    assert otf_xic.shape == thermo_xic.shape
    np.testing.assert_allclose(otf_xic, thermo_xic, rtol=1e-4, atol=1e-3)


@pytest.mark.skipif(not RAW_FILES, reason="no .raw files in test_files/")
@pytest.mark.parametrize("path", RAW_FILES, ids=lambda p: p.name)
def test_clean_mappings_match_thermo(monkeypatch, path):
    """Regression-guard the OpenTFRaw capabilities that already work.

    The contract suite only xpasses these under ``strict=False`` — a regression
    would silently turn XPASS into xfail and stay green. Comparing the values
    through the real public functions under both backends protects them.
    """
    path = str(path)

    th_pol = _run_under(monkeypatch, "thermo", m_thermo.get_polarity_options, path)
    ot_pol = _run_under(monkeypatch, "opentfraw", m_thermo.get_polarity_options, path)
    assert th_pol == ot_pol

    th_n = _run_under(monkeypatch, "thermo", _num_of_scans, path)
    ot_n = _run_under(monkeypatch, "opentfraw", _num_of_scans, path)
    assert th_n == ot_n

    th_t = _run_under(monkeypatch, "thermo", m_thermo.get_scan_timestamps, path)
    ot_t = _run_under(monkeypatch, "opentfraw", m_thermo.get_scan_timestamps, path)
    np.testing.assert_allclose(ot_t, th_t, rtol=1e-6, atol=1e-6)

    tic = m_thermo.get_tic_per_scan
    th_ts, th_tic = _run_under(monkeypatch, "thermo", tic, path)
    ot_ts, ot_tic = _run_under(monkeypatch, "opentfraw", tic, path)
    np.testing.assert_allclose(ot_ts, th_ts, rtol=1e-6, atol=1e-6)
    np.testing.assert_allclose(ot_tic, th_tic, rtol=1e-4, atol=1e-3)


@pytest.mark.skipif(
    not _OTF_HAS_LABELS,
    reason="installed opentfraw lacks RawFile.centroid_labels() (decoder build)",
)
@pytest.mark.parametrize("path", RAW_FILES, ids=lambda p: p.name)
def test_centroids_per_scan_matches_thermo(monkeypatch, path):
    """OpenTFRaw's decoded per-peak labels must match Thermo's CentroidStream.

    Pins the values behind ``get_centroids_per_scan`` under both backends:
    per FT scan, the peak count must match and masses / resolution / S:N must
    agree. Resolution is decoded verbatim (exact); S:N is
    ``(intensity - baseline) / (noise - baseline)`` (matches Thermo to f32).
    Works on Exploris too, unlike the profile m/z.
    """
    path = str(path)

    th = _run_under(monkeypatch, "thermo", m_thermo.get_centroids_per_scan, path)
    ot = _run_under(monkeypatch, "opentfraw", m_thermo.get_centroids_per_scan, path)

    assert len(ot) == len(th), "per-scan centroid list length differs"

    compared = 0
    for t, o in zip(th, ot):
        assert o["masses"].size == t["masses"].size, (
            f"peak count differs: OpenTFRaw {o['masses'].size} vs "
            f"Thermo {t['masses'].size}"
        )
        if t["masses"].size == 0:
            continue
        compared += 1
        np.testing.assert_allclose(o["masses"], t["masses"], rtol=0, atol=1e-3)
        np.testing.assert_allclose(
            o["resolutions"], t["resolutions"], rtol=1e-5, atol=1.0
        )
        np.testing.assert_allclose(
            o["signal_to_noise"], t["signal_to_noise"], rtol=1e-4, atol=1e-3
        )
        np.testing.assert_allclose(o["timestamp"], t["timestamp"], rtol=1e-6)

    if compared == 0:
        pytest.skip("no FT centroid scans to compare")


@pytest.mark.skipif(
    not _OTF_HAS_PROFILE,
    reason="installed opentfraw lacks RawFile.profile() (needs the accessor build)",
)
@pytest.mark.parametrize("path", RAW_FILES, ids=lambda p: p.name)
def test_profile_matches_thermo(monkeypatch, path):
    """OpenTFRaw's profile spectrum must match Thermo's SegmentedScan.

    Guards the profile path so a structural-only check (e.g. get_signal's
    size>0) can't mask wrong m/z. Compares the first MS1 scan's non-zero profile
    points: count must match, and the base-peak m/z must agree within a coarse
    tolerance. (On Q Exactive the m/z agrees to ~20 ppm - a lock-mass-level
    offset - hence 50 ppm, not sub-ppm.)

    Exploris profile m/z is now correct too (the scan-event coefficient fix);
    it previously xfailed here while the coefficients were mis-decoded.
    """
    path = str(path)
    raw = opentfraw.RawFile(path)

    monkeypatch.setenv("MASCOPE_THERMO_BACKEND", "thermo")
    with open_backend(path) as backend:
        first_ms1 = backend.scan_indices(ms_type="Ms")[0]
        mzs, specs, _ = backend.profile_per_scan(ms_type="Ms")
    tmz = np.asarray(mzs[0], dtype=float)
    tint = np.asarray(specs[0], dtype=float)

    omz, oint = (np.asarray(a, dtype=float) for a in raw.profile(first_ms1))

    om, tm = omz[oint > 0], tmz[tint > 0]
    oi, ti = oint[oint > 0], tint[tint > 0]
    if om.size == 0 or tm.size == 0:
        pytest.skip("no profile signal in the first MS1 scan")

    assert om.size == tm.size, (
        f"non-zero profile point count: OpenTFRaw {om.size} vs Thermo {tm.size}"
    )
    bp_otf = om[np.argmax(oi)]
    bp_thermo = tm[np.argmax(ti)]
    ppm = abs(bp_otf - bp_thermo) / bp_thermo * 1e6
    assert ppm <= 50, (
        f"base-peak m/z {bp_otf:.4f} vs Thermo {bp_thermo:.4f} ({ppm:.0f} ppm)"
    )


@pytest.mark.skipif(not RAW_FILES, reason="no .raw files in test_files/")
@pytest.mark.parametrize("path", RAW_FILES, ids=lambda p: p.name)
def test_ms2_precursor_matches_thermo(monkeypatch, path):
    """OpenTFRaw's MS2 precursor m/z must match Thermo's.

    Both backends parse the precursor from the rendered scan-filter string;
    OpenTFRaw renders it once the scan-event reaction is decoded (Exploris
    needed the offset-4 fix). Skips files with no MS2 scans.
    """
    path = str(path)

    monkeypatch.setenv("MASCOPE_THERMO_BACKEND", "thermo")
    try:
        with open_backend(path) as backend:
            th = backend.ms2_precursor_by_scan()
    except m_thermo.NoScansFoundError:
        pytest.skip("no MS2 scans")
    if not th:
        pytest.skip("no resolvable MS2 precursors")

    monkeypatch.setenv("MASCOPE_THERMO_BACKEND", "opentfraw")
    with open_backend(path) as backend:
        ot = backend.ms2_precursor_by_scan()

    # The precursor comes from the rendered filter string; an opentfraw build
    # without the Exploris scan-event fix renders no precursor on Exploris and
    # returns nothing. Skip then (capability gate), like the profile/labels
    # tests -- but if it decodes any, they must match Thermo exactly.
    if not ot:
        pytest.skip("installed opentfraw does not render MS2 precursors here")

    assert set(ot) == set(th), "MS2 scan set with a resolvable precursor differs"
    for scan_number, mz_thermo in th.items():
        assert ot[scan_number] == pytest.approx(mz_thermo, abs=1e-3), (
            f"scan {scan_number}: OpenTFRaw {ot[scan_number]} vs Thermo {mz_thermo}"
        )


@pytest.mark.skipif(not RAW_FILES, reason="no .raw files in test_files/")
@pytest.mark.parametrize("path", RAW_FILES, ids=lambda p: p.name)
def test_scan_statistics_match_thermo(monkeypatch, path):
    """OpenTFRaw's mapped scan statistics must match Thermo for the fields it
    provides (Phase-4 metadata remap). Uses only the base opentfraw API (the
    typed scan dict), so it runs against the released wheel too -- no gate.
    """
    path = str(path)

    monkeypatch.setenv("MASCOPE_THERMO_BACKEND", "thermo")
    with open_backend(path) as backend:
        th = backend.scan_statistics()
    monkeypatch.setenv("MASCOPE_THERMO_BACKEND", "opentfraw")
    with open_backend(path) as backend:
        ot = backend.scan_statistics()

    assert set(ot) == set(th), "scan set differs"
    for scan_number, t in th.items():
        o = ot[scan_number]
        assert o["MsType"] == t["MsType"]
        assert o["StartTime"] == pytest.approx(t["StartTime"], rel=1e-6, abs=1e-6)
        assert o["TIC"] == pytest.approx(t["TIC"], rel=1e-4, abs=1e-3)
        assert o["BasePeakMass"] == pytest.approx(t["BasePeakMass"], rel=1e-5, abs=1e-3)
        assert o["BasePeakIntensity"] == pytest.approx(
            t["BasePeakIntensity"], rel=1e-3, abs=1.0
        )


# Cap on scans averaged by the ppm-averaging parity tests, to bound runtime on
# files with thousands of scans (the averaging still spans many scans).
MAX_AVG_SCANS = 25


def _bounded_window(monkeypatch, path):
    """(t_min, t_max) [s] covering at most MAX_AVG_SCANS scans."""
    times = np.sort(_run_under(monkeypatch, "thermo", m_thermo.get_scan_timestamps, path))
    if times.size == 0:
        return None, None
    return float(times[0]), float(times[min(times.size, MAX_AVG_SCANS) - 1])


@pytest.mark.skipif(
    not _OTF_HAS_LABELS,
    reason="installed opentfraw lacks RawFile.centroid_labels() (decoder build)",
)
@pytest.mark.parametrize("path", RAW_FILES, ids=lambda p: p.name)
def test_centroids_average_matches_thermo(monkeypatch, path):
    """Approximate parity for averaged centroids (gap 5.3).

    Thermo's AverageScans re-centroids the averaged profile, so this NumPy
    ppm-binning of per-scan centroids cannot match it exactly: m/z agrees to
    sub-ppm and the summed intensity to a few percent, while resolution / S:N
    are coarser and not asserted (they do not feed the instrument fit; see the
    follow-up ticket). Guards against gross regressions. Bounded to a small
    scan window for speed.
    """
    path = str(path)
    t_min, t_max = _bounded_window(monkeypatch, path)

    tm, ti, _, _ = _run_under(
        monkeypatch, "thermo", m_thermo.get_centroids, path, t_min=t_min, t_max=t_max
    )
    om, oi, orr, osn = _run_under(
        monkeypatch, "opentfraw", m_thermo.get_centroids, path, t_min=t_min, t_max=t_max
    )
    if tm.size == 0:
        pytest.skip("no centroids")

    assert om.size == orr.size == osn.size == oi.size
    # Peak counts in the same ballpark (re-centroiding splits/merges differently).
    assert 0.6 * tm.size <= om.size <= 1.6 * tm.size, (
        f"centroid count {om.size} vs Thermo {tm.size}"
    )
    # Summed intensity within a few percent.
    np.testing.assert_allclose(oi.sum(), ti.sum(), rtol=0.1)

    # Most OpenTFRaw peaks match a Thermo peak within 1 ppm (robust to which
    # single peak happens to be tallest, unlike a base-peak check).
    tm_sorted = np.sort(tm)
    pos = np.searchsorted(tm_sorted, om)
    matched = 0
    for k, mzv in enumerate(om):
        for c in (pos[k] - 1, pos[k]):
            if 0 <= c < tm_sorted.size and abs(tm_sorted[c] - mzv) / mzv * 1e6 <= 1.0:
                matched += 1
                break
    assert matched / om.size >= 0.8, (
        f"only {matched}/{om.size} averaged centroids matched Thermo within 1 ppm"
    )
