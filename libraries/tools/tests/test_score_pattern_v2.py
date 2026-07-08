"""Unit tests for the v2 match score (detectability-gated, SNR-aware) and its
calibration. Inputs follow the matched-array convention: one entry per predicted
isotopologue (index 0 = monoisotopic), unmatched entries carry 0.
"""

import numpy as np

from mascope_tools.composition.heuristic_filter import (
    DEFAULT_CALIBRATION_V2,
    SCORE_VERSION,
    calibrate_score,
    score_pattern,
    score_pattern_v2,
)

# A two-isotopologue ion: M0 (rel 1.0) + M+1 (rel 0.11), base SNR 500.
PRED = np.array([1.0, 0.11])
ME = np.array([0.2, 0.3])  # ppm errors
SNR = np.array([500.0, 55.0])


def _perfect():
    return score_pattern_v2(ME, np.array([1000.0, 110.0]), SNR, PRED)


def test_version_constant():
    assert SCORE_VERSION == 2


def test_perfect_match_scores_high():
    assert _perfect() > 0.95


def test_detectable_missing_isotopologue_is_penalized():
    # M+1 predicted at 0.11 -> expected SNR 0.11*500 = 55 >= 3 -> should be visible
    missing = score_pattern_v2(ME, np.array([1000.0, 0.0]), np.array([500.0, 0.0]), PRED)
    assert missing < _perfect() - 0.05


def test_undetectable_missing_isotopologue_not_penalized():
    # tiny M+1 (rel 0.005) -> expected SNR 0.005*500 = 2.5 < 3 -> below noise, excluded
    pred = np.array([1.0, 0.005])
    s = score_pattern_v2(
        np.array([0.2, 0.3]), np.array([1000.0, 0.0]), np.array([500.0, 0.0]), pred
    )
    assert s > 0.95


def test_low_snr_isotopologue_gets_wide_tolerance():
    # a noisy (SNR 4) M+1 off by ~30% is penalized but NOT tanked, because its
    # tolerance scales with its own noise (a hard relative-error term would zero it)
    noisy = score_pattern_v2(ME, np.array([1000.0, 80.0]), np.array([500.0, 4.0]), PRED)
    assert 0.85 < noisy < _perfect()


def test_low_snr_mass_error_is_forgiven():
    # A trace M+1 off by 0.6 ppm scores higher when it is NOISY than when it is clean:
    # a weak peak's centroid is legitimately less precise, so the mass width scales with
    # 1/SNR. Intensities are kept perfect (exact ratio) to isolate the mass term.
    pred = np.array([1.0, 0.3])
    ints = np.array([1000.0, 300.0])  # exact 0.3 ratio -> intensity term ~1
    me = np.array([0.0, 0.6])
    clean = score_pattern_v2(me, ints, np.array([500.0, 200.0]), pred, sigma_ppm=0.3)
    noisy = score_pattern_v2(me, ints, np.array([500.0, 4.0]), pred, sigma_ppm=0.3)
    assert noisy > clean


def test_high_snr_mass_width_is_essentially_the_fixed_sigma():
    # At high SNR the SNR term (MASS_SNR_K/SNR) is negligible, so a 0.6 ppm error on a
    # trace peak is penalised against the tight fixed sigma (Br3--like: no free pass).
    pred = np.array([1.0, 0.3])
    ints = np.array([1000.0, 300.0])
    me = np.array([0.0, 0.6])
    s = score_pattern_v2(me, ints, np.array([5000.0, 5000.0]), pred, sigma_ppm=0.3)
    assert s < 0.75  # ~0.63: the 2-sigma error is still penalised at high SNR


def test_absent_monoisotopic_returns_zero():
    assert score_pattern_v2(ME, np.array([0.0, 0.0]), np.array([0.0, 0.0]), PRED) == 0.0


def test_calibration_is_probability_and_monotone():
    lo, hi = calibrate_score(0.5), calibrate_score(0.99)
    assert 0.0 < lo < hi < 1.0
    assert DEFAULT_CALIBRATION_V2[0] > 0  # positive slope


def test_v1_score_pattern_unchanged_perfect():
    # guard that v1 still behaves (byte-identical formula): a clean match scores high
    s = score_pattern(
        np.array([100.0, 101.0]),  # observed_masses
        np.array([0.2, 0.3]),  # mass errors ppm
        np.array([1000.0, 110.0]),  # intensities
        np.array([0.0, 0.02]),  # intensity errors
        PRED,  # predicted_rel
    )
    assert 0.9 < s <= 1.0
