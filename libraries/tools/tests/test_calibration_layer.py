"""Unit tests for the confidence-calibration layer (assignment-confidence P2).

Contract: fit a score -> P(correct) Platt curve from labelled data, apply it, and be
honest -- a calibration carries provenance, an uncalibrated instrument returns None
(never a borrowed probability), and too little data refuses to fit. The machinery is
validated on synthetic labels (independent of the still-provisional real datasets).
See docs/dev/assignment_confidence.md (P2).
"""

import numpy as np
import pytest

from mascope_tools.composition.calibration import (
    DEFAULT_CORROBORATION_CAP,
    INSTRUMENT_CALIBRATIONS,
    MIN_CALIBRATION_LABELS,
    Calibration,
    InsufficientCalibrationData,
    apply_calibration,
    apply_corroboration,
    calibration_error,
    calibration_for,
    fit_calibration,
    recalibrate,
)


def _separated_labels(n=400, seed=0):
    """Scores where correctness rises with score (a calibratable signal)."""
    rng = np.random.default_rng(seed)
    scores = rng.uniform(0, 1, n)
    # P(correct) truly ~ score -> a good curve should recover calibration
    correct = rng.uniform(0, 1, n) < scores
    return scores, correct.astype(int)


def test_apply_calibration_is_a_probability():
    c = Calibration(a=6.0, b=-3.0)
    p = apply_calibration(np.array([0.0, 0.5, 1.0]), c)
    assert np.all((p >= 0) & (p <= 1))
    assert p[2] > p[0]  # monotone increasing in score
    # accepts a raw (a, b) tuple too
    assert apply_calibration(0.5, (6.0, -3.0)) == pytest.approx(p[1])


def test_calibration_error_zero_when_perfect():
    # probabilities that exactly match empirical correctness -> ECE 0
    probs = np.array([0.0] * 50 + [1.0] * 50)
    correct = np.array([0] * 50 + [1] * 50)
    assert calibration_error(probs, correct) == pytest.approx(0.0)


def test_calibration_error_detects_miscalibration():
    # claim 0.9 everywhere but only half are correct -> large ECE
    probs = np.full(100, 0.9)
    correct = np.array([1, 0] * 50)
    assert calibration_error(probs, correct) > 0.3


def test_fit_calibration_recovers_a_calibrated_curve():
    scores, correct = _separated_labels(n=600)
    cal = fit_calibration(scores, correct, instrument="orbi", source="synthetic")
    assert cal.instrument == "orbi"
    assert cal.n_pos > 0 and cal.n_neg > 0
    assert cal.fit_utc is not None
    # the fitted curve should be reasonably calibrated on held-out data
    assert cal.ece is not None and cal.ece < 0.15
    # applying it yields probabilities that increase with score
    p = apply_calibration(np.array([0.2, 0.8]), cal)
    assert p[1] > p[0]


def test_fit_calibration_refuses_too_few_labels():
    with pytest.raises(InsufficientCalibrationData):
        fit_calibration([0.9, 0.1], [1, 0])


def test_fit_calibration_refuses_single_class():
    scores = list(np.linspace(0, 1, MIN_CALIBRATION_LABELS + 10))
    with pytest.raises(InsufficientCalibrationData):
        fit_calibration(scores, [1] * len(scores))  # all correct, nothing to separate


def test_calibration_for_returns_provisional_orbitrap():
    cal = calibration_for("orbi")
    assert cal is not None
    assert cal.instrument == "orbi"
    assert cal.provisional is True


def test_calibration_for_uncalibrated_instrument_is_none():
    # TOF has no curated dataset yet -> None, so callers stay honest (uncalibrated)
    assert calibration_for("tof") is None
    assert calibration_for(None) is None
    assert calibration_for("unknown-instrument") is None


def test_registry_only_ships_orbitrap():
    assert set(INSTRUMENT_CALIBRATIONS) == {"orbi"}


# --- adduct corroboration odds-update -------------------------------------------------

WEIGHTS = {"+Br-": 2.28, "+NH4+": 0.83, "+(CH4N2O)H+": 0.70, "+H+": 0.0, "-H+": 0.0}


def test_corroboration_raises_probability_with_a_strong_adduct():
    # a weak-ish 0.6 assignment corroborated by a bromide adduct should rise
    p = apply_corroboration(0.6, ["+Br-"], WEIGHTS)
    assert p > 0.6
    # matches the closed-form odds update: logit(0.6) + 2.28
    z = np.log(0.6 / 0.4) + 2.28
    assert p == pytest.approx(1 / (1 + np.exp(-z)))


def test_corroboration_generic_adduct_barely_moves_it():
    # deprotonation carries ~0 log-odds -> essentially unchanged
    assert apply_corroboration(0.6, ["-H+"], WEIGHTS) == pytest.approx(0.6, abs=1e-9)


def test_corroboration_sums_multiple_adducts():
    p1 = apply_corroboration(0.5, ["+NH4+"], WEIGHTS)
    p2 = apply_corroboration(0.5, ["+NH4+", "+(CH4N2O)H+"], WEIGHTS)
    assert p2 > p1  # two corroborating adducts lift more than one


def test_corroboration_is_capped():
    # a pile of strong adducts can't exceed the cap on the log-odds shift
    big = {f"a{i}": 5.0 for i in range(10)}
    p = apply_corroboration(0.5, list(big), big, cap=DEFAULT_CORROBORATION_CAP)
    z = np.log(0.5 / 0.5) + DEFAULT_CORROBORATION_CAP
    assert p == pytest.approx(1 / (1 + np.exp(-z)))


def test_corroboration_noops_when_uncalibrated_or_empty():
    assert apply_corroboration(None, ["+Br-"], WEIGHTS) is None  # uncalibrated stays None
    assert apply_corroboration(0.7, [], WEIGHTS) == 0.7  # nothing corroborating
    assert apply_corroboration(0.7, ["+Br-"], None) == 0.7  # no weights configured
    assert apply_corroboration(0.7, ["unknown"], WEIGHTS) == 0.7  # unweighted adduct


def test_provisional_orbitrap_carries_corroboration_weights():
    cal = calibration_for("orbi")
    assert cal.corroboration_weights is not None
    assert cal.corroboration_weights["+Br-"] > cal.corroboration_weights["+NH4+"] > 0


# --- recalibrate (V2 loop: labels -> new calibration) ---------------------------------


def test_recalibrate_fits_and_reports_change():
    scores, labels = _separated_labels(n=400, seed=1)
    current = Calibration(a=1.0, b=0.0, instrument="orbi",
                          corroboration_weights={"+Br-": 2.28})
    out = recalibrate(scores, labels, instrument="orbi", source="user verifications",
                      current=current)
    assert out["calibration"].instrument == "orbi"
    assert 0.0 <= out["after_ece"] <= 1.0
    assert out["before_ece"] is not None  # current curve scored on these labels
    # a curve fit on the labels should calibrate them at least as well as an arbitrary prior
    assert out["after_ece"] <= out["before_ece"] + 1e-6
    # corroboration weights are carried forward (refit separately, not from verdicts)
    assert out["calibration"].corroboration_weights == {"+Br-": 2.28}


def test_recalibrate_stays_provisional_without_strong_evidence():
    scores, labels = _separated_labels(n=400, seed=2)
    levels = ["visual"] * len(labels)  # eyeball-only -> cannot graduate the curve
    out = recalibrate(scores, labels, levels, instrument="orbi", source="s")
    assert out["provisional"] is True
    assert out["n_strong_positives"] == 0
    assert out["calibration"].provisional is True


def test_recalibrate_graduates_with_enough_strong_positives():
    scores, labels = _separated_labels(n=400, seed=3)
    # give the positives reference-standard evidence; negatives carry none
    levels = ["reference_standard" if y == 1 else None for y in labels]
    out = recalibrate(scores, labels, levels, instrument="orbi", source="s",
                      provisional_min_strong=5)
    assert out["n_strong_positives"] >= 5
    assert out["provisional"] is False
    assert out["calibration"].provisional is False


def test_recalibrate_refuses_too_few_labels():
    with pytest.raises(InsufficientCalibrationData):
        recalibrate([0.9, 0.1, 0.8], [1, 0, 1], instrument="orbi", source="s")


def test_recalibrate_no_current_curve_has_no_before_ece():
    scores, labels = _separated_labels(n=200, seed=4)
    out = recalibrate(scores, labels, instrument="tof", source="s", current=None)
    assert out["before_ece"] is None
    assert out["calibration"].corroboration_weights is None
