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
    INSTRUMENT_CALIBRATIONS,
    MIN_CALIBRATION_LABELS,
    Calibration,
    InsufficientCalibrationData,
    apply_calibration,
    calibration_error,
    calibration_for,
    fit_calibration,
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
