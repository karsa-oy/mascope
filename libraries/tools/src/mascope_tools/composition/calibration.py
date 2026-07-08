"""Confidence calibration (assignment-confidence Phase 2).

A fit score, and the arbitration *evidence* (fit x plausibility), rank assignments
well but are not probabilities: a raw 0.85 is not "85% likely correct". Calibration
maps a raw score to a **calibrated probability of being correct** via Platt scaling
([Platt 1999][platt]) -- a logistic curve ``P = sigmoid(a*score + b)`` fit on assignments
whose truth is known (true identifications vs near-mass decoys).

Two design commitments make this safe to ship before the datasets are final:

1. **A calibration is a provenance-carrying object, not a bare constant.** A
   :class:`Calibration` records the instrument it was fit for, how many positive/negative
   labels went into it, its held-out calibration error, when and from what dataset it was
   fit, and whether it is still ``provisional``. "We don't have good data yet" becomes
   metadata, not a hidden risk.
2. **Never fabricate a probability we cannot back up.** When no calibration exists for an
   instrument (e.g. TOF today), :func:`calibration_for` returns ``None`` and callers must
   report the assignment as *uncalibrated* (surfacing the raw evidence + a flag) rather
   than emit an instrument-mismatched probability.

**Where the labels come from (the reference-dataset link).** The positive labels are
*confident identifications* -- most strongly, compounds confirmed by a reference standard
(Schymanski Level 1). That is exactly what the reference dataset encodes, so a per-instrument
calibration is "how well the score predicts reference-confirmed identity on this instrument".
The negatives are near-mass decoys (`tooling/score_eval`). This is also the basis of the
*user self-calibration* flow: a user runs known standards on their instrument, Mascope scores
them plus decoys, and fits that instrument's curve -- persisted per instrument (a later step;
today the registry ships one provisional Orbitrap curve).

[platt]: https://en.wikipedia.org/wiki/Platt_scaling
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Sequence

import numpy as np


@dataclass(frozen=True)
class Calibration:
    """A fitted score -> P(correct) curve with its provenance.

    ``a``/``b`` are the Platt parameters (``P = sigmoid(a*score + b)``). The rest is
    provenance so a calibrated number is auditable and its trust level is explicit.

    ``corroboration_weights`` are the per-adduct log-odds by which co-occurring adducts of
    the same compound update ``p_correct`` (see :func:`apply_corroboration`), measured on the
    golden set (``tooling/score_eval/corroboration_benchmark.py``). They ride on the same
    per-instrument object because, like the Platt curve, they encode this instrument's reagent
    chemistry and are refit alongside it. ``None``/empty means no corroboration adjustment.
    """

    a: float
    b: float
    instrument: str | None = None  # instrument class this was fit for (e.g. "orbi")
    n_pos: int = 0  # confident (correct) labels used
    n_neg: int = 0  # decoy (incorrect) labels used
    ece: float | None = None  # held-out expected calibration error (lower = better)
    fit_utc: str | None = None  # when it was fit (ISO-8601)
    source: str | None = None  # dataset / reference provenance it was fit from
    provisional: bool = True  # True until fit on a curated, sufficient dataset
    # {adduct notation -> log-odds boost}; e.g. {"+Br-": 2.28, "+NH4+": 0.83}
    corroboration_weights: Mapping[str, float] | None = field(default=None)

    def params(self) -> tuple[float, float]:
        return (self.a, self.b)


# A corroboration boost is capped so a compound seen via many adducts can't drive p_correct
# arbitrarily to 1 (the per-adduct LRs assume rough independence, which weakens as they stack).
DEFAULT_CORROBORATION_CAP = 3.0


def apply_corroboration(
    p_correct: float | None,
    observed_adducts: Sequence[str],
    weights: Mapping[str, float] | None,
    *,
    cap: float = DEFAULT_CORROBORATION_CAP,
) -> float | None:
    """Update a calibrated probability with adduct co-occurrence, as a bounded Bayesian odds
    update: ``logit(p') = logit(p) + clamp(sum(weights[a] for a in observed_adducts), -cap, cap)``.

    ``observed_adducts`` are the OTHER adducts (beyond the winner's own) via which the same
    compound was independently assigned; each contributes its measured log-odds. Generic adducts
    (protonation/deprotonation) carry ~0, distinctive ones (e.g. bromide) carry more, so a strong
    corroborator lifts a weak assignment while a generic one barely moves a strong one. Returns
    ``p_correct`` unchanged when it is ``None`` (uncalibrated), or when there are no weights or no
    observed corroborating adducts."""
    if p_correct is None or not weights or not observed_adducts:
        return p_correct
    delta = float(sum(weights.get(a, 0.0) for a in observed_adducts))
    if delta == 0.0:
        return p_correct
    delta = max(-cap, min(cap, delta))
    p = min(max(float(p_correct), 1e-9), 1 - 1e-9)
    z = np.log(p / (1.0 - p)) + delta
    return float(1.0 / (1.0 + np.exp(-z)))


def apply_calibration(score, calibration: "Calibration | tuple[float, float]"):
    """Map a raw score (or array) to a calibrated probability via
    ``sigmoid(a*score + b)``. Accepts a :class:`Calibration` or a raw ``(a, b)`` pair."""
    a, b = calibration.params() if isinstance(calibration, Calibration) else calibration
    return 1.0 / (1.0 + np.exp(-(a * np.asarray(score, float) + b)))


def calibration_error(
    probs: Sequence[float], is_correct: Sequence[bool], *, bins: int = 10
) -> float:
    """Expected calibration error: the average gap between predicted probability and
    observed correctness, over equal-width probability bins (weighted by bin count).
    0 = perfectly calibrated."""
    p = np.asarray(probs, float)
    y = np.asarray(is_correct, float)
    if len(p) == 0:
        return float("nan")
    edges = np.linspace(0.0, 1.0, bins + 1)
    ece = 0.0
    for k in range(bins):
        hi = p <= edges[k + 1] if k == bins - 1 else p < edges[k + 1]
        m = (p >= edges[k]) & hi
        if m.any():
            ece += m.mean() * abs(y[m].mean() - p[m].mean())
    return float(ece)


def _platt_fit(scores: np.ndarray, labels: np.ndarray) -> tuple[float, float]:
    """Fit ``P = sigmoid(a*score + b)`` by minimising log-loss (Platt scaling)."""
    from scipy.optimize import minimize

    s = np.asarray(scores, float)
    y = np.asarray(labels, float)

    def nll(p: np.ndarray) -> float:
        z = p[0] * s + p[1]
        # numerically stable log-loss
        return float(
            np.where(y == 1, np.logaddexp(0.0, -z), np.logaddexp(0.0, z)).mean()
        )

    res = minimize(nll, np.array([3.0, -1.5]), method="Nelder-Mead")
    return float(res.x[0]), float(res.x[1])


# Fewer than this many labelled points (or a single class) is too little to fit a
# meaningful curve; callers should keep the assignment uncalibrated instead.
MIN_CALIBRATION_LABELS = 30


class InsufficientCalibrationData(ValueError):
    """Raised when there are too few / single-class labels to fit a calibration."""


def fit_calibration(
    scores: Sequence[float],
    is_correct: Sequence[bool],
    *,
    instrument: str | None = None,
    source: str | None = None,
    provisional: bool = True,
    holdout: float = 0.5,
    seed: int = 0,
) -> Calibration:
    """Fit a :class:`Calibration` from labelled ``(score, is_correct)`` pairs.

    Platt-fits ``(a, b)`` on a random train split and reports the **held-out** ECE as the
    curve's quality, so a calibration carries an honest, out-of-sample calibration error.
    ``instrument`` / ``source`` / ``provisional`` are recorded as provenance.

    :raises InsufficientCalibrationData: fewer than ``MIN_CALIBRATION_LABELS`` labels, or
        only one class present (nothing to separate).
    """
    from datetime import datetime, timezone

    s = np.asarray(scores, float)
    y = np.asarray(is_correct, int)
    mask = np.isfinite(s)
    s, y = s[mask], y[mask]
    if len(s) < MIN_CALIBRATION_LABELS or y.sum() == 0 or (y == 0).sum() == 0:
        raise InsufficientCalibrationData(
            f"need >= {MIN_CALIBRATION_LABELS} labels of both classes "
            f"(got n={len(s)}, pos={int(y.sum())}, neg={int((y == 0).sum())})"
        )
    rng = np.random.default_rng(seed)
    idx = rng.permutation(len(s))
    n_test = max(1, int(len(s) * holdout))
    test, train = idx[:n_test], idx[n_test:]
    # Guard: if the split leaves a single class in train, fit on all data instead.
    if y[train].sum() == 0 or (y[train] == 0).sum() == 0:
        train = idx
    a, b = _platt_fit(s[train], y[train])
    ece = calibration_error(apply_calibration(s[test], (a, b)), y[test])
    return Calibration(
        a=a,
        b=b,
        instrument=instrument,
        n_pos=int(y.sum()),
        n_neg=int((y == 0).sum()),
        ece=round(float(ece), 4) if np.isfinite(ece) else None,
        fit_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        source=source,
        provisional=provisional,
    )


# ---------------------------------------------------------------------------
# Per-instrument registry.
#
# Ships one PROVISIONAL Orbitrap curve fit from the demo golden set (evidence =
# fit x plausibility of the arbitrated winners vs near-mass decoys); see
# tooling/score_eval/arbitration_eval.py --fit-calibration. There is deliberately
# NO TOF curve: no curated TOF golden set exists yet, so TOF stays uncalibrated and
# callers must report its assignments as such rather than borrow the Orbitrap curve.
# The long-term store is per-instrument and user-refittable (a DB-backed follow-up).
# ---------------------------------------------------------------------------

# Provisional Orbitrap calibration of the arbitration evidence, fit on the demo bundle
# (Br neg + Ur pos) via `arbitration_eval.py --fit-calibration` over all candidates
# (true vs decoy). PRELIMINARY -- a placeholder until a curated reference dataset replaces
# it; refit with `fit_calibration` and update here (or, later, the per-instrument store).
# Held-out ECE 0.029; e.g. evidence 0.3 -> P 0.16, 0.6 -> 0.52, 0.9 -> 0.86.
# Per-adduct corroboration log-odds, measured on the same demo goldens via the offset-decoy
# benchmark (real adduct offset vs anchor-swap null; tooling/score_eval/corroboration_benchmark.py
# and _corroboration_metrics.json). Distinctive reagent adducts corroborate strongly, generic
# protonation/deprotonation ~0. PROVISIONAL, instrument+library specific -- refit per deployment.
PROVISIONAL_ORBITRAP_CORROBORATION = {
    "+Br-": 2.28,
    "+NH4+": 0.83,
    "+(CH4N2O)H+": 0.70,
    "+H+": 0.0,
    "-H+": 0.0,
    "-H-": 0.0,
}

PROVISIONAL_ORBITRAP = Calibration(
    a=5.7380,
    b=-3.3625,
    instrument="orbi",
    n_pos=17329,
    n_neg=81754,
    ece=0.0289,
    fit_utc=None,
    source="demo goldens (Br/Ur, preliminary)",
    provisional=True,
    corroboration_weights=PROVISIONAL_ORBITRAP_CORROBORATION,
)

INSTRUMENT_CALIBRATIONS: dict[str, Calibration] = {"orbi": PROVISIONAL_ORBITRAP}


def calibration_for(instrument: str | None) -> Calibration | None:
    """The calibration for an instrument class, or ``None`` when none exists.

    ``None`` is a first-class answer: the caller MUST then treat the assignment as
    uncalibrated (report the raw evidence + an ``uncalibrated`` flag) rather than apply
    another instrument's curve. Unknown / missing instruments return ``None``."""
    if not instrument:
        return None
    return INSTRUMENT_CALIBRATIONS.get(str(instrument).lower())
