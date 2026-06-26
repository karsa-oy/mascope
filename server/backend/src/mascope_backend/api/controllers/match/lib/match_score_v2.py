"""v2 match score (mascope_tools) — backend adapter.

Computes the consolidated, detectability-gated, SNR-aware per-ion match score
(`mascope_tools.composition.heuristic_filter.score_pattern_v2`) from one ion's
isotopologue rows as produced by `compute_match_isotopes`. Wired alongside the
legacy `Σ score_i·rel_ab` aggregation behind `MATCH_SCORE_VERSION` so the two can
be switched and compared; v1 stays byte-identical.

See tooling/score_eval/DESIGN.md. The score returned is the CALIBRATED P(correct)
(Platt curve fit on the demo golden set; refit per instrument class).

NOTE: this is a pure function (unit-tested via mascope_tools). End-to-end behaviour
in the live match pipeline must be validated with the backend test suite. The first
experiment uses a PROXY SNR derived from intensities when `signal_to_noise` isn't yet
carried on the isotope rows; real SNR is plumbed by keeping `signal_to_noise` through
`_parse_and_filter_peaks` -> `_match_assign`.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from mascope_tools.composition.heuristic_filter import calibrate_score, score_pattern_v2

# Correct matches spread wider than the calibration-anchor precision (centroiding +
# prediction error + analyte tail); added in quadrature to the fitted instrument sigma.
PRED_SIGMA_PPM = 0.5


def fit_sample_mass_accuracy(match_isotope_df: pd.DataFrame) -> tuple[float, float | None]:
    """Robust (mu, sigma) ppm of the matched isotopologues' mass error — the
    instrument's measured mass accuracy (resolution-correct, Orbitrap vs TOF).
    Returns sigma=None when there are too few matched anchors (caller falls back)."""
    me = pd.to_numeric(match_isotope_df.get("match_mz_error"), errors="coerce")
    inten = pd.to_numeric(match_isotope_df.get("sample_peak_intensity"), errors="coerce")
    me = me[(inten.fillna(0) > 0) & me.notna()]
    if len(me) < 8:
        return 0.0, None
    mu = float(me.median())
    sigma = max(float(1.4826 * (me - mu).abs().median()), 0.05)
    return mu, sigma


def sample_noise_floor(match_isotope_df: pd.DataFrame) -> float:
    """Proxy per-sample noise floor from the matched intensities (used for the proxy
    SNR until real signal_to_noise is carried on the isotope rows)."""
    inten = pd.to_numeric(match_isotope_df.get("sample_peak_intensity"), errors="coerce")
    inten = inten[inten > 0]
    return float(np.percentile(inten, 2)) if len(inten) else 1.0


def ion_score_v2(
    group: pd.DataFrame,
    *,
    sigma_ppm: float | None = None,
    mu: float = 0.0,
    noise: float = 1.0,
    calibrate: bool = True,
) -> float:
    """v2 match score for ONE ion, from its isotopologue rows (matched + unmatched).

    `group` must contain `relative_abundance`, `match_mz_error`, `sample_peak_intensity`
    (and optionally `signal_to_noise`). Sorts by predicted abundance (base first), builds
    the matched arrays, and calls `score_pattern_v2`. Returns the calibrated P(correct)
    (or the raw fit score if `calibrate=False`)."""
    g = group.sort_values("relative_abundance", ascending=False)
    pr = pd.to_numeric(g["relative_abundance"], errors="coerce").to_numpy(float)
    if pr.size == 0 or not np.isfinite(pr).any() or np.nanmax(pr) <= 0:
        return 0.0
    pr = np.nan_to_num(pr) / np.nanmax(pr)  # base-relative
    oi = pd.to_numeric(g["sample_peak_intensity"], errors="coerce").fillna(0.0).to_numpy(float)
    me = pd.to_numeric(g["match_mz_error"], errors="coerce").fillna(0.0).to_numpy(float) - mu
    snr_col = pd.to_numeric(g.get("signal_to_noise"), errors="coerce") if "signal_to_noise" in g else None
    if snr_col is not None and snr_col.notna().any():
        snr = snr_col.fillna(0.0).to_numpy(float)
    else:  # proxy SNR from intensity / per-sample noise floor
        snr = np.where(oi > 0, oi / max(noise, 1e-9), 0.0)
    sig = float(np.hypot(sigma_ppm, PRED_SIGMA_PPM)) if sigma_ppm is not None else None
    raw = score_pattern_v2(me, oi, snr, pr, sigma_ppm=sig)
    return float(calibrate_score(raw)) if calibrate else float(raw)
