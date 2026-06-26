"""Unit tests for the v2 match-score backend adapter (mascope_tools)."""

import numpy as np
import pandas as pd

from mascope_backend.api.controllers.match.lib.match_score_v2 import (
    fit_sample_mass_accuracy,
    ion_score_v2,
    match_score_version,
    sample_noise_floor,
)


def _ion(m1_intensity, snr=None):
    """One ion's isotopologue rows (M0 rel 1.0 + M+1 rel 0.11), as
    compute_match_isotopes produces them (unmatched -> intensity 0)."""
    d = {
        "relative_abundance": [1.0, 0.11],
        "match_mz_error": [0.2, 0.3],
        "sample_peak_intensity": [1000.0, m1_intensity],
    }
    if snr is not None:
        d["signal_to_noise"] = snr
    return pd.DataFrame(d)


def test_perfect_match_high_probability():
    assert ion_score_v2(_ion(110.0, snr=[500, 55]), sigma_ppm=0.5) > 0.7


def test_detectable_missing_isotopologue_penalized():
    perfect = ion_score_v2(_ion(110.0, snr=[500, 55]), sigma_ppm=0.5)
    missing = ion_score_v2(_ion(0.0, snr=[500, 0]), sigma_ppm=0.5)  # M+1 should be visible
    assert missing < perfect


def test_absent_monoisotopic_scores_zero():
    g = pd.DataFrame(
        {"relative_abundance": [1.0, 0.11], "match_mz_error": [0.0, 0.0],
         "sample_peak_intensity": [0.0, 0.0], "signal_to_noise": [0.0, 0.0]}
    )
    # Absent monoisotopic -> raw score 0 (no match). The calibrated probability cannot
    # be exactly 0 (sigmoid); it maps to the calibration floor ~0.0155, which is the
    # observed live minimum for no-evidence ions.
    assert ion_score_v2(g, sigma_ppm=0.5, calibrate=False) == 0.0
    assert ion_score_v2(g, sigma_ppm=0.5) < 0.02


def test_proxy_snr_path_when_column_absent():
    # no signal_to_noise column -> proxy SNR from intensity / noise floor
    s = ion_score_v2(_ion(110.0), sigma_ppm=0.5, noise=5.0)
    assert 0.0 < s <= 1.0


def test_raw_vs_calibrated():
    g = _ion(110.0, snr=[500, 55])
    raw = ion_score_v2(g, sigma_ppm=0.5, calibrate=False)
    cal = ion_score_v2(g, sigma_ppm=0.5, calibrate=True)
    assert 0.0 < raw <= 1.0 and 0.0 < cal < 1.0


def test_fit_sample_mass_accuracy():
    rng = np.random.default_rng(0)
    df = pd.DataFrame(
        {"match_mz_error": rng.normal(0.1, 0.3, 50), "sample_peak_intensity": [100.0] * 50}
    )
    mu, sigma = fit_sample_mass_accuracy(df)
    assert abs(mu - 0.1) < 0.2 and 0.1 < sigma < 0.6
    # too few anchors -> sigma None (caller falls back)
    assert fit_sample_mass_accuracy(df.head(3))[1] is None


def test_sample_noise_floor_positive():
    df = pd.DataFrame({"sample_peak_intensity": [1.0, 10.0, 100.0, 1000.0]})
    assert sample_noise_floor(df) > 0


def test_satellite_matched_isotopologue_treated_as_absent():
    base = dict(_ion(110.0, snr=[500, 55]))
    normal = ion_score_v2(pd.DataFrame({**base, "is_satellite": [False, False]}), sigma_ppm=0.5)
    # M+1 "matched" a satellite artifact -> treated as absent -> detectability penalty
    sat = ion_score_v2(pd.DataFrame({**base, "is_satellite": [False, True]}), sigma_ppm=0.5)
    assert sat < normal


def test_match_score_version_env(monkeypatch):
    monkeypatch.delenv("MASCOPE_MATCH_SCORE_VERSION", raising=False)
    assert match_score_version() == 2  # v2 is the consolidated default
    monkeypatch.setenv("MASCOPE_MATCH_SCORE_VERSION", "1")
    assert match_score_version() == 1  # explicit legacy escape hatch
    monkeypatch.setenv("MASCOPE_MATCH_SCORE_VERSION", "garbage")
    assert match_score_version() == 2  # malformed -> default, not a silent downgrade


def test_category_thresholds_are_score_version_aware(monkeypatch):
    """Categories use version-aware default bands: v1 (0.8/0.7 on the ~0.95-clustered
    fit score) vs v2 (0.7/0.3 on the calibrated-probability scale)."""
    import asyncio

    from mascope_backend.api.controllers.match.lib.match_aggregate import (
        set_ions_match_category,
    )

    def cats(version):
        monkeypatch.setenv("MASCOPE_MATCH_SCORE_VERSION", str(version))
        df = pd.DataFrame(
            {"match_score": [0.85, 0.5, 0.1], "instrument": ["orbitrap"] * 3}
        )
        out = asyncio.run(set_ions_match_category(df, None))
        return list(out["match_category"])

    assert cats(2) == [2, 1, 0]  # 0.85>=0.7; 0.3<=0.5<0.7; 0.1<0.3
    assert cats(1) == [2, 0, 0]  # 0.85>=0.8; 0.5<0.7; 0.1<0.7
