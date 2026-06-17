"""Cross-backend numerical parity for reimplemented computed ops.

Where OpenTFRaw needs a NumPy reimplementation of a Thermo-computed operation
(assessment gaps 5.3 / 5.4), the dual-backend contract suite only checks the
*shape* of the result. These tests pin the *values*: run the same public
function under both backends and assert agreement. This is the evidence that a
reimplementation actually reproduces Thermo's numbers, not just its structure.

File-agnostic, like the parity harness: every ``*.raw`` in ``test_files/`` is
compared (only the small committed sample files ship; drop in more locally, or
point ``MASCOPE_THERMO_TEST_FILES_DIR`` at a wider corpus). Both backends
(pythonnet + opentfraw) are runtime dependencies of
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

# MS2 calibrated HCD energy / isolation width need RawFile.scan_parameters()
# (the trailer accessor), present only in a build with that accessor.
_OTF_HAS_SCAN_PARAMS = hasattr(opentfraw.RawFile, "scan_parameters")


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
    agree. These come from the *same* binary stream Thermo decodes, so they are
    bit-exact in practice (measured: 0 ppm m/z, 0 rel-err resolution, ~2e-7 S:N
    across the corpus). The tolerances are therefore tight -- loose tolerances
    here would silently tolerate a real decode regression. S:N is
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
        # m/z is bit-exact; atol=1e-5 Da is ~0.0002 ppm at m/z 50, still ~100x
        # tighter than a 1 ppm decode error (5e-5 Da there) would produce.
        np.testing.assert_allclose(o["masses"], t["masses"], rtol=0, atol=1e-5)
        np.testing.assert_allclose(
            o["resolutions"], t["resolutions"], rtol=1e-6, atol=1.0
        )
        np.testing.assert_allclose(
            o["signal_to_noise"], t["signal_to_noise"], rtol=1e-5, atol=1e-3
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


@pytest.mark.skipif(
    not _OTF_HAS_SCAN_PARAMS,
    reason="installed opentfraw lacks the Exploris scan-event fix (fork build)",
)
@pytest.mark.parametrize("path", RAW_FILES, ids=lambda p: p.name)
def test_ms2_precursor_matches_thermo(monkeypatch, path):
    """OpenTFRaw's MS2 precursor m/z must match Thermo's.

    Both backends parse the precursor from the rendered scan-filter string.
    OpenTFRaw renders it correctly only with the Exploris scan-event fix; the
    released wheel renders Exploris precursors partially/incorrectly, so this is
    gated on a fork-build marker (scan_parameters ships in the same build).
    Skips files with no MS2 scans.
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


def _hcd_tuple(value):
    return tuple(
        round(float(part.replace(",", ".")), 2)
        for part in str(value).split(",")
        if part.strip()
    )


@pytest.mark.skipif(
    not _OTF_HAS_SCAN_PARAMS,
    reason="installed opentfraw lacks RawFile.scan_parameters() (trailer accessor)",
)
@pytest.mark.parametrize("path", RAW_FILES, ids=lambda p: p.name)
def test_ms2_acquisition_info_matches_thermo(monkeypatch, path):
    """OpenTFRaw's MS2 isolation width + calibrated HCD energy (read from the
    decoded trailer) must match Thermo's "MS2 Isolation Width:" / "HCD Energy
    V:". Skips files without MS2 scans.
    """
    path = str(path)

    monkeypatch.setenv("MASCOPE_THERMO_BACKEND", "thermo")
    try:
        with open_backend(path) as backend:
            th_width, th_hcd = backend.ms2_acquisition_info()
    except m_thermo.NoScansFoundError:
        pytest.skip("no MS2 scans")

    monkeypatch.setenv("MASCOPE_THERMO_BACKEND", "opentfraw")
    with open_backend(path) as backend:
        ot_width, ot_hcd = backend.ms2_acquisition_info()

    assert ot_width == pytest.approx(th_width, abs=1e-3), "isolation width differs"
    assert set(ot_hcd) == set(th_hcd), "MS2 scan set differs"
    for scan_number, hcd in th_hcd.items():
        assert _hcd_tuple(ot_hcd[scan_number]) == _hcd_tuple(hcd), (
            f"scan {scan_number}: HCD energy {ot_hcd[scan_number]!r} vs {hcd!r}"
        )


# Cap on scans averaged by the ppm-averaging parity tests, to bound runtime on
# files with thousands of scans (the averaging still spans many scans).
MAX_AVG_SCANS = 25
_MIN_SCANS_FOR_PROFILE_PARITY = 3  # fewer scans -> freq average not representative


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
    sub-ppm and the summed intensity to a few percent, while resolution is
    coarser and not asserted (it does not feed the instrument fit). S:N *is*
    asserted at the weak-peak threshold (it feeds peak detection's weak-peak
    filter): the count of peaks above the threshold must track Thermo, which the
    n/sqrt(N) averaged-S:N scaling restores. Guards against gross regressions.
    Bounded to a small scan window for speed.
    """
    path = str(path)
    t_min, t_max = _bounded_window(monkeypatch, path)

    tm, ti, _, tsn = _run_under(
        monkeypatch, "thermo", m_thermo.get_centroids, path, t_min=t_min, t_max=t_max
    )
    om, oi, orr, osn = _run_under(
        monkeypatch, "opentfraw", m_thermo.get_centroids, path, t_min=t_min, t_max=t_max
    )
    if tm.size == 0:
        pytest.skip("no centroids")

    assert om.size == orr.size == osn.size == oi.size
    # Peak counts in the same ballpark (re-centroiding splits/merges differently;
    # measured 0.99-1.04 across the corpus, so this is comfortably loose).
    assert 0.85 * tm.size <= om.size <= 1.20 * tm.size, (
        f"centroid count {om.size} vs Thermo {tm.size}"
    )
    # Summed intensity within a few percent.
    np.testing.assert_allclose(oi.sum(), ti.sum(), rtol=0.1)

    # Each OpenTFRaw peak's nearest Thermo peak (robust to which single peak
    # happens to be tallest, unlike a base-peak check).
    tm_sorted = np.sort(tm)
    pos = np.searchsorted(tm_sorted, om)
    dev_ppm = np.full(om.shape, np.inf)
    for k, mzv in enumerate(om):
        for c in (pos[k] - 1, pos[k]):
            if 0 <= c < tm_sorted.size:
                dev_ppm[k] = min(dev_ppm[k], abs(tm_sorted[c] - mzv) / mzv * 1e6)
    # (1) High match fraction within 1 ppm. The ~5-8 % that don't pair are
    # sub-threshold noise peaks (discarded downstream) and ringing/satellite
    # artifacts around very intense peaks (a sub-FWHM picket fence the two
    # backends position slightly differently; flagged downstream by
    # flag_satellite_peaks) -- not lost analytes; measured >=0.95 across the
    # corpus, so 0.92 leaves margin. Pushing to ~100 % would need re-centroiding
    # the averaged profile (see report 4.4/4.5), not a threshold.
    matched = dev_ppm <= 1.0
    assert matched.mean() >= 0.92, (
        f"only {int(matched.sum())}/{om.size} averaged centroids matched Thermo "
        "within 1 ppm"
    )
    # (2) The matched peaks must agree to *sub-0.1 ppm* -- this is the HRMS mass
    # accuracy guarantee, and the centroid m/z is what feeds peak detection.
    # Measured median 0.02-0.05 ppm, p90 <= 0.15 ppm.
    md = dev_ppm[matched]
    assert float(np.median(md)) <= 0.1, (
        f"median matched-peak m/z deviation {np.median(md):.3f} ppm (> 0.1)"
    )
    assert float(np.percentile(md, 90)) <= 0.4, (
        f"p90 matched-peak m/z deviation {np.percentile(md, 90):.3f} ppm (> 0.4)"
    )

    # Averaged S:N must track Thermo well enough that peak detection's weak-peak
    # filter (S:N >= 3) keeps/drops the same peaks. Thermo reads S:N off the
    # noise-reduced averaged profile (~sqrt(N) lower noise); the backend scales
    # the pooled per-scan S:N by n/sqrt(N) to match. Without it the count above
    # the threshold runs ~sqrt(N) low and near-threshold peaks vanish. Assert the
    # above-threshold count tracks Thermo where there are enough peaks to be
    # statistically meaningful.
    t_pass = int((tsn >= 3.0).sum())
    o_pass = int((osn >= 3.0).sum())
    if t_pass >= 20:
        assert 0.7 * t_pass <= o_pass <= 1.4 * t_pass, (
            f"{o_pass} averaged centroids above S:N 3 vs Thermo {t_pass}"
        )


def _profile_fwhm_ppm(mz, inten, center, window_ppm=40):
    """FWHM (in ppm) of the peak nearest `center` in a profile spectrum, or
    None if it can't be measured cleanly. Half-max crossings are linearly
    interpolated between adjacent points."""
    sel = np.abs(mz - center) / center * 1e6 < window_ppm
    x, y = mz[sel], inten[sel]
    # Count signal (nonzero) points only, so the inserted baseline zeros don't
    # make a near-blank window spuriously measurable.
    if (y > 0).sum() < 5:
        return None
    order = np.argsort(x)
    x, y = x[order], y[order]
    i = int(np.argmax(y))
    ymax = y[i]
    if ymax <= 0:
        return None
    half = ymax / 2.0

    def cross(a, b):  # interpolate x where y == half between indices a, b
        if y[b] == y[a]:
            return x[a]
        return x[a] + (half - y[a]) * (x[b] - x[a]) / (y[b] - y[a])

    li = i
    while li > 0 and y[li] > half:
        li -= 1
    if y[li] > half:
        return None
    ri = i
    while ri < y.size - 1 and y[ri] > half:
        ri += 1
    if y[ri] > half:
        return None
    return (cross(ri, ri - 1) - cross(li, li + 1)) / center * 1e6


def _profile_apex(mz, inten, center, window_ppm=40):
    """Apex intensity of the peak nearest `center` (the OpenTFRaw profile m/z can
    be offset by up to ~20 ppm, so search a window), or None if not measurable."""
    sel = np.abs(mz - center) / center * 1e6 < window_ppm
    y = inten[sel]
    if (y > 0).sum() < 3:  # signal points only (ignore inserted baseline zeros)
        return None
    ymax = float(y.max())
    return ymax if ymax > 0 else None


def _profile_apex_mz(mz, inten, center, window_ppm=40):
    """m/z of the apex of the peak nearest `center`, or None if not measurable."""
    sel = np.abs(mz - center) / center * 1e6 < window_ppm
    sub_mz, sub_i = mz[sel], inten[sel]
    if (sub_i > 0).sum() < 3:  # signal points only (ignore inserted baseline zeros)
        return None
    return float(sub_mz[int(np.argmax(sub_i))])


@pytest.mark.skipif(
    not _OTF_HAS_PROFILE,
    reason="installed opentfraw lacks RawFile.profile() (needs the accessor build)",
)
@pytest.mark.parametrize("path", RAW_FILES, ids=lambda p: p.name)
def test_sum_signal_matches_thermo(monkeypatch, path):
    """OpenTFRaw's averaged profile (compute_sum_signal -> average_profile) must
    reproduce Thermo's, in the two properties that matter downstream: absolute
    peak intensity (base-peak height) and per-peak FWHM. Thermo interpolates each
    scan onto a common axis (broadening by between-scan m/z jitter); a binning sum
    would leave peaks too narrow, so this guards the interpolation behaviour.
    average_profile conserves the integrated signal (not the grid-dependent
    point-sum), so absolute intensities -- and thus the apex -- match Thermo.
    Bounded to a small scan window for speed.
    """
    path = str(path)
    t_min, t_max = _bounded_window(monkeypatch, path)

    th_sig, th_n = _run_under(
        monkeypatch, "thermo", m_thermo.compute_sum_signal, path, t_min=t_min, t_max=t_max
    )
    ot_sig, ot_n = _run_under(
        monkeypatch, "opentfraw", m_thermo.compute_sum_signal, path, t_min=t_min, t_max=t_max
    )
    assert ot_n == th_n, "number of combined scans differs"
    if th_n < _MIN_SCANS_FOR_PROFILE_PARITY:
        # With very few scans the frequency-domain average is not representative
        # (apex can differ ~40% on a 2-scan near-blank), and the result peak
        # heights are sourced from the profile apex only within a modest band, so
        # this doesn't affect real-data heights. Skip the profile-shape parity.
        pytest.skip(f"too few scans ({th_n}) for averaged-profile parity")

    tmz, tv = np.asarray(th_sig.mz), np.asarray(th_sig.values)
    omz, ov = np.asarray(ot_sig.mz), np.asarray(ot_sig.values)

    # Parity on the strongest, well-separated peaks for both absolute apex
    # intensity and per-peak FWHM. average_profile conserves the integrated
    # signal, so a peak's apex matches Thermo up to the (separately checked)
    # small FWHM difference. Median over several peaks is robust to a single
    # noise-level apex on near-blank files.
    order = np.argsort(tv)[::-1]
    centers = []
    for k in order[:600]:
        c = tmz[k]
        if all(abs(c - cc) / c * 1e6 > 50 for cc in centers):
            centers.append(c)
        if len(centers) >= 12:
            break

    apex_ratios, fwhm_ratios, mz_off_ppm = [], [], []
    for c in centers:
        ta, oa = _profile_apex(tmz, tv, c), _profile_apex(omz, ov, c)
        if ta and oa:
            apex_ratios.append(oa / ta)
        tf, of = _profile_fwhm_ppm(tmz, tv, c), _profile_fwhm_ppm(omz, ov, c)
        if tf and of and tf > 0:
            fwhm_ratios.append(of / tf)
        om = _profile_apex_mz(omz, ov, c)
        if om:
            mz_off_ppm.append((om - c) / c * 1e6)

    if len(apex_ratios) < 3 or len(fwhm_ratios) < 3:
        pytest.skip("too few measurable peaks for profile comparison")
    # Measured median apex 0.99-1.02, FWHM 0.99-1.01 across the corpus.
    assert 0.92 <= float(np.median(apex_ratios)) <= 1.10, (
        f"median apex ratio OTF/Thermo = {np.median(apex_ratios):.3f}"
    )
    assert 0.93 <= float(np.median(fwhm_ratios)) <= 1.10, (
        f"median FWHM ratio OTF/Thermo = {np.median(fwhm_ratios):.3f}"
    )
    # Profile m/z is aligned to the centroid labels (average_profile step 4), so
    # the OpenTFRaw profile axis should match Thermo's, not sit at the raw
    # lock-mass-level offset. The floor is a few ppm, set by files whose strongest
    # peaks fall in a dense low-m/z cluster where the per-peak residual is worst;
    # most files are well under this. The median is the right metric. Assert where
    # alignment can run.
    if len(mz_off_ppm) >= 6:
        assert abs(float(np.median(mz_off_ppm))) <= 5.0, (
            f"median profile m/z offset OTF vs Thermo = {np.median(mz_off_ppm):.2f} "
            "ppm (profile axis should be aligned to the centroid labels)"
        )
