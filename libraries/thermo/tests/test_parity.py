"""File-agnostic parity tests: Thermo RawFileReader vs OpenTFRaw.

These tests discover every ``*.raw`` file in the target directory and run the
same comparison on each, so adding more realistic files later needs no code
changes — just drop them in (or point ``MASCOPE_PARITY_RAW_DIR`` at them).

Run from the repository root, in the venv that has both ``mascope_thermo`` and
``opentfraw`` installed::

    uv run mascope test run libraries -m thermo
    # or directly, to see the per-file numeric report:
    uv run pytest libraries/thermo/tests/test_parity.py -v -s

If either backend is unavailable, or no files are found, the tests skip rather
than fail.

Design — this suite is a *backrest* for the migration (assessment Phases 0–6):

* Tests for things OpenTFRaw already reproduces (scan count, RT, polarity, TIC,
  centroids, isolation width, HCD energy, injection time, charge, instrument
  model) assert real parity and must stay green — they catch regressions.
* Tests for the known capability gaps (per-peak resolution/S:N, MS² precursor
  m/z, profile arrays) assert the *target* parity but are marked ``xfail``. They
  fail today (expected), and flip to ``XPASS`` the moment a gap closes — e.g.
  when you contribute the decoder upstream or add it in a fork. Watch the pytest
  summary for ``xpassed``: that's your signal to delete the marker and tighten.

The end state: every gap closed → no ``xfail`` left → the suite passes outright,
which is the same condition under which the app can run on OpenTFRaw alone.

Environment overrides:
    MASCOPE_PARITY_RAW_DIR   directory to scan for .raw files
    MASCOPE_PARITY_MIN_MATCH minimum acceptable median centroid-match fraction
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path

import pytest
from parity import parity


# Skip the whole module unless both backends import.
pytest.importorskip("opentfraw", reason="opentfraw not installed")
pytest.importorskip("pythonnet", reason="pythonnet (Thermo backend) not installed")


def _raw_dir() -> Path:
    return Path(os.environ.get("MASCOPE_PARITY_RAW_DIR", str(parity.DEFAULT_RAW_DIR)))


def _discover() -> list[Path]:
    try:
        return parity.discover_raw_files(_raw_dir())
    except Exception:
        return []


RAW_FILES = _discover()

# Generous Phase 0 floor; tighten once we have real numbers from real files.
MIN_MATCH_FRACTION = float(os.environ.get("MASCOPE_PARITY_MIN_MATCH", "0.99"))


@pytest.fixture(scope="module")
def summaries() -> dict[str, dict]:
    """Read every file once with both backends; cache the comparison summaries."""
    out: dict[str, dict] = {}
    for f in RAW_FILES:
        thermo = parity.read_thermo(str(f))
        otf = parity.read_opentfraw(str(f))
        out[f.name] = parity.compare_file(thermo, otf)
    return out


@pytest.mark.skipif(not RAW_FILES, reason="no .raw files found to compare")
@pytest.mark.parametrize("raw_file", RAW_FILES, ids=lambda p: p.name)
class TestParity:
    """One instance per discovered .raw file."""

    def test_report(self, raw_file, summaries, capsys):
        """Always print the full numeric summary (visible with -s)."""
        s = summaries[raw_file.name]
        with capsys.disabled():
            print("\n" + json.dumps(s, indent=2))

    def test_scan_count_matches(self, raw_file, summaries):
        s = summaries[raw_file.name]
        assert s["scan_count_match"], (
            f"scan count differs: thermo={s['thermo_num_scans']} "
            f"opentfraw={s['opentfraw_num_scans']}"
        )

    def test_polarity_agrees(self, raw_file, summaries):
        s = summaries[raw_file.name]
        assert s["polarity_mismatch_count"] == 0, (
            f"polarity mismatches on scans {s['polarity_mismatch_scans']}"
        )

    def test_ms_level_agrees(self, raw_file, summaries):
        s = summaries[raw_file.name]
        assert s["ms_level_mismatch_count"] == 0, (
            f"MS-level mismatches on scans {s['ms_level_mismatch_scans']}"
        )

    def test_retention_time_aligns(self, raw_file, summaries):
        s = summaries[raw_file.name]
        assert s["rt_max_abs_diff_min"] <= parity.RT_TOL_MIN, (
            f"retention-time drift {s['rt_max_abs_diff_min']:.3e} min "
            f"> {parity.RT_TOL_MIN} min"
        )

    def test_tic_close(self, raw_file, summaries):
        s = summaries[raw_file.name]
        assert s["tic_median_rel_err"] <= parity.TIC_REL_TOL, (
            f"median TIC rel err {s['tic_median_rel_err']:.3e} > {parity.TIC_REL_TOL}"
        )

    def test_centroids_mostly_match(self, raw_file, summaries):
        s = summaries[raw_file.name]
        assert s["peak_matched_frac_median"] >= MIN_MATCH_FRACTION, (
            f"median centroid match fraction {s['peak_matched_frac_median']:.3f} "
            f"< {MIN_MATCH_FRACTION}"
        )

    def test_injection_time_close(self, raw_file, summaries):
        s = summaries[raw_file.name]
        if math.isnan(s["injection_time_max_rel_err"]):
            pytest.skip("no comparable injection-time values")
        assert s["injection_time_max_rel_err"] <= parity.INJECTION_TIME_REL_TOL, (
            f"injection-time max rel err {s['injection_time_max_rel_err']:.3e} "
            f"> {parity.INJECTION_TIME_REL_TOL}"
        )

    def test_charge_state_agrees(self, raw_file, summaries):
        s = summaries[raw_file.name]
        if not s["charge_compared_count"]:
            pytest.skip("no comparable charge states")
        assert s["charge_mismatch_count"] == 0, (
            f"{s['charge_mismatch_count']}/{s['charge_compared_count']} "
            f"charge-state mismatches"
        )

    def test_instrument_model_agrees(self, raw_file, summaries):
        s = summaries[raw_file.name]
        if not s["opentfraw_instrument_model"]:
            pytest.skip("OpenTFRaw reports no instrument model")
        assert s["instrument_model_match"], (
            f"instrument model differs: thermo={s['thermo_instrument_model']!r} "
            f"opentfraw={s['opentfraw_instrument_model']!r}"
        )

    # ---- MS²-specific parity (skips on MS1-only files) ----

    def test_isolation_width_agrees(self, raw_file, summaries):
        s = summaries[raw_file.name]
        if not s["ms2_scan_count"]:
            pytest.skip("no MS² scans in this file")
        assert s["isolation_width_mismatch_count"] == 0, (
            f"{s['isolation_width_mismatch_count']} isolation-width mismatches "
            f"(max abs diff {s['isolation_width_max_abs_diff']:.3g} Da)"
        )

    def test_collision_energy_agrees(self, raw_file, summaries):
        """Nominal HCD energy (filter ``@hcd``) must match OpenTFRaw's value."""
        s = summaries[raw_file.name]
        if not s["ms2_scan_count"]:
            pytest.skip("no MS² scans in this file")
        assert s["collision_energy_mismatch_count"] == 0, (
            f"{s['collision_energy_mismatch_count']} HCD-energy mismatches "
            f"(max abs diff {s['collision_energy_max_abs_diff']:.3g})"
        )

    # ---- Known-gap parity (xfail until OpenTFRaw closes the gap) ----
    #
    # These assert the *target* state. They xfail today and will XPASS the moment
    # the capability lands (e.g. an upstream/fork decoder). An XPASS in the pytest
    # summary is the signal to delete the marker and keep the assertion as a
    # regular regression guard. See the module docstring.

    @pytest.mark.xfail(
        reason="OpenTFRaw 1.1.0 gap (5.1): no per-peak resolution / S:N / noise",
        strict=False,
    )
    def test_resolution_parity(self, raw_file, summaries):
        s = summaries[raw_file.name]
        assert s["thermo_has_resolution"], "expected Thermo resolution data"
        assert s["opentfraw_has_resolution"], "OpenTFRaw exposes no per-peak resolution"

    @pytest.mark.xfail(
        reason="OpenTFRaw 1.1.0 gap (5.1b): MS² precursor m/z is None",
        strict=False,
    )
    def test_ms2_precursor_parity(self, raw_file, summaries):
        """Every MS² scan with a Thermo precursor must have a matching one in
        OpenTFRaw (drives ``_group_ms2_scans_by_parent``)."""
        s = summaries[raw_file.name]
        if not (s["ms2_scan_count"] and s["precursor_thermo_count"]):
            pytest.skip("no MS² scans with a Thermo precursor in this file")
        assert s["precursor_opentfraw_count"] == s["precursor_thermo_count"], (
            f"OpenTFRaw precursor m/z present for "
            f"{s['precursor_opentfraw_count']}/{s['precursor_thermo_count']} scans"
        )
        assert s["precursor_max_ppm"] <= parity.PRECURSOR_PPM_TOL, (
            f"precursor m/z max deviation {s['precursor_max_ppm']:.2f} ppm "
            f"> {parity.PRECURSOR_PPM_TOL}"
        )

    @pytest.mark.xfail(
        reason="OpenTFRaw 1.1.0 gap (5.2): no profile / SegmentedScan arrays",
        strict=False,
    )
    def test_profile_parity(self, raw_file, summaries):
        s = summaries[raw_file.name]
        assert s["thermo_has_profile"], "expected Thermo profile data"
        assert s["opentfraw_has_profile"], (
            "OpenTFRaw exposes no profile / SegmentedScan arrays"
        )
