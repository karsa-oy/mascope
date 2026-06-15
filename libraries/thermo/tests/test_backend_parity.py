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
    not _OTF_HAS_PROFILE,
    reason="installed opentfraw lacks RawFile.profile() (needs the accessor build)",
)
@pytest.mark.parametrize("path", RAW_FILES, ids=lambda p: p.name)
def test_profile_matches_thermo(request, monkeypatch, path):
    """OpenTFRaw's profile spectrum must match Thermo's SegmentedScan.

    Guards the profile path so a structural-only check (e.g. get_signal's
    size>0) can't mask wrong m/z. Compares the first MS1 scan's non-zero profile
    points: count must match, and the base-peak m/z must agree within a coarse
    tolerance. (On Q Exactive the m/z agrees to ~20 ppm - a lock-mass-level
    offset - hence 50 ppm, not sub-ppm.)

    OpenTFRaw mis-calibrates Exploris profile m/z (the bins/intensities decode,
    but the frequency->m/z coefficients don't), so Exploris is xfailed pending
    the upstream fix; the non-zero *count* still matches there.
    """
    path = str(path)
    raw = opentfraw.RawFile(path)
    if "exploris" in (raw.instrument_model or "").lower():
        request.applymarker(
            pytest.mark.xfail(
                reason="OpenTFRaw profile m/z mis-calibrated on Exploris (upstream)",
                strict=False,
            )
        )

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
