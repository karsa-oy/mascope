"""#2 — Match-score evaluation harness (baseline + regression gate).

Scores the demo golden dataset with `mascope_tools` and reports the four numbers
that define whether a scorer is good (DESIGN.md §5.3):

  reproducibility  scoring is deterministic (re-run → identical scores)
  ranking          per peak, does the TRUE formula outrank its near-mass decoys?
                   (top-1 rate + ROC-AUC over candidate pools from make_candidates.py)
  calibration      does score ≈ P(correct)?  (reliability curve + ECE)
  score dist.      distribution of the true assignments' scores (the baseline)

It is both the DECISION MECHANISM (which scorer/params win) and a CI REGRESSION
GATE: pass `--baseline <json>` and it exits non-zero if ranking/AUC regress.

Scoring is done at the ION level — `predict_isotopes(ion[:-1], charge)` — against
each file's observed peaks. NOTE (v1 limitation): the "observed peaks" are the
bundle's matched-target peaks (`expected/peaks.parquet`), a proxy for the full
spectrum; a decoy isotopologue landing on an un-matched real peak is missed. A
full-spectrum peak list (Phase A.5) tightens ranking/calibration; the baseline and
reproducibility numbers are exact regardless.

    python score_eval.py <bundle_dir> [--ppm 5] [--baseline base.json] [--out base.json]
"""

from __future__ import annotations

import argparse
import json
import sys

import numpy as np
import pandas as pd

MZ_PPM = 5.0
INT_TOL = 0.4  # mascope_tools ISOTOPE_MATCHING_INTENSITY_TOLERANCE


def score_ion(mzs: np.ndarray, ints: np.ndarray, ion: str, *, ppm: float) -> float | None:
    """Score one ion formula (e.g. 'C10H13O+') against a sorted observed peak list,
    mirroring peaky's validated local_scoring matching loop. Returns the
    mascope_tools score, or None if the monoisotopic peak isn't present."""
    from mascope_tools.composition.heuristic_filter import predict_isotopes, score_pattern

    sign = ion[-1] if ion and ion[-1] in "+-" else ""
    if not sign:
        return None
    charge = 1 if sign == "+" else -1
    try:
        pred_mz, pred_int, _ = predict_isotopes(ion[:-1], charge, None)
    except Exception:
        return None
    if len(pred_mz) == 0:
        return None
    pred_rel = pred_int / pred_int[0]
    obs_mz = np.zeros_like(pred_mz)
    obs_int = np.zeros_like(pred_mz)
    obs_mz_err = np.zeros_like(pred_mz)
    obs_int_err = np.zeros_like(pred_mz)
    base_int = None
    for i, pmz in enumerate(pred_mz):
        d = pmz * ppm * 1e-6
        lo = np.searchsorted(mzs, pmz - d, "left")
        hi = np.searchsorted(mzs, pmz + d, "right")
        if lo >= hi:
            continue
        k = lo + int(np.argmin(np.abs(mzs[lo:hi] - pmz)))
        if i == 0:
            base_int = ints[k]
            obs_int[0] = ints[k]
            obs_mz[0] = mzs[k]
            obs_mz_err[0] = abs(mzs[k] - pmz) / pmz * 1e6
            continue
        if not base_int:
            continue
        rel_obs = ints[k] / base_int
        ierr = abs(pred_rel[i] - rel_obs) / pred_rel[i]
        if ierr <= INT_TOL:
            obs_int[i] = ints[k]
            obs_mz[i] = mzs[k]
            obs_mz_err[i] = abs(mzs[k] - pmz) / pmz * 1e6
            obs_int_err[i] = ierr
    if base_int is None:
        return None
    return float(score_pattern(obs_mz, obs_mz_err, obs_int, obs_int_err, pred_rel))


def score_ion_v2(
    mzs: np.ndarray,
    ints: np.ndarray,
    ion: str,
    *,
    ppm: float,
    noise: float,
    k_detect: float = 3.0,
    miss_penalty: float = 0.3,
    sigma_ppm: float = 2.0,
) -> float | None:
    """Detectability-gated score (DESIGN.md §4). Unlike v1, a predicted
    isotopologue that is ABSENT but *should have been visible* (expected height
    `rel·base ≥ k_detect·noise`, i.e. SNR ≥ ~3) is penalized rather than ignored —
    this is the fix for over-crediting incomplete envelopes. Mass uses a Gaussian
    likelihood normalised by `sigma_ppm` (instrument accuracy); aggregation is a
    predicted-abundance-weighted geometric mean (harsh: a missing detectable peak
    drags the score down). Satellite peaks should be removed from `mzs/ints` by
    the caller."""
    from mascope_tools.composition.heuristic_filter import predict_isotopes

    sign = ion[-1] if ion and ion[-1] in "+-" else ""
    if not sign:
        return None
    charge = 1 if sign == "+" else -1
    try:
        pred_mz, pred_int, _ = predict_isotopes(ion[:-1], charge, None)
    except Exception:
        return None
    if len(pred_mz) == 0:
        return None
    pred_rel = pred_int / pred_int[0]

    base_int = None
    logL, wsum = 0.0, 0.0
    for i, pmz in enumerate(pred_mz):
        d = pmz * ppm * 1e-6
        lo = np.searchsorted(mzs, pmz - d, "left")
        hi = np.searchsorted(mzs, pmz + d, "right")
        matched = hi > lo
        if i == 0:
            if not matched:
                return None  # monoisotopic must be present
            k = lo + int(np.argmin(np.abs(mzs[lo:hi] - pmz)))
            base_int = ints[k]
            ppm_err = abs(mzs[k] - pmz) / pmz * 1e6
            L = np.exp(-0.5 * (ppm_err / sigma_ppm) ** 2)
        elif matched:
            k = lo + int(np.argmin(np.abs(mzs[lo:hi] - pmz)))
            ppm_err = abs(mzs[k] - pmz) / pmz * 1e6
            rel_obs = ints[k] / base_int
            ierr = abs(pred_rel[i] - rel_obs) / pred_rel[i]
            L_mz = np.exp(-0.5 * (ppm_err / sigma_ppm) ** 2)
            L_int = max(0.0, 1.0 - ierr / INT_TOL)
            L = L_mz * L_int
        else:
            # absent: evidence-against only if it should have been detectable
            expected = pred_rel[i] * base_int
            if expected >= k_detect * noise:
                L = miss_penalty
            else:
                continue  # below noise floor -> not evidence, exclude
        L = max(L, 1e-6)
        logL += pred_rel[i] * np.log(L)
        wsum += pred_rel[i]
    if base_int is None or wsum == 0:
        return None
    return float(np.exp(logL / wsum))  # abundance-weighted geometric mean


def _roc_auc(y_true: np.ndarray, y_score: np.ndarray) -> float:
    """Rank-based ROC-AUC (P[true scored above a random decoy]); no sklearn dep."""
    pos, neg = y_score[y_true == 1], y_score[y_true == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    order = np.argsort(y_score, kind="mergesort")
    ranks = np.empty(len(y_score), float)
    ranks[order] = np.arange(1, len(y_score) + 1)
    # average ranks for ties
    s = y_score[order]
    i = 0
    while i < len(s):
        j = i
        while j + 1 < len(s) and s[j + 1] == s[i]:
            j += 1
        if j > i:
            ranks[order[i : j + 1]] = (i + 1 + j + 1) / 2
        i = j + 1
    return float((ranks[y_true == 1].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


def _ece(scores: np.ndarray, correct: np.ndarray, bins: int = 10) -> float:
    edges = np.linspace(0, 1, bins + 1)
    ece = 0.0
    for b in range(bins):
        m = (scores >= edges[b]) & (scores < edges[b + 1] if b < bins - 1 else scores <= 1.0)
        if m.sum():
            ece += m.mean() * abs(correct[m].mean() - scores[m].mean())
    return float(ece)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("bundle_dir")
    ap.add_argument("--ppm", type=float, default=MZ_PPM)
    ap.add_argument("--scorer", choices=["v1", "v2"], default="v1",
                    help="v1 = current mascope_tools; v2 = detectability-gated")
    ap.add_argument("--baseline", help="JSON to compare against (regression gate)")
    ap.add_argument("--out", help="write metrics JSON here")
    a = ap.parse_args()

    peaks = pd.read_parquet(f"{a.bundle_dir}/expected/peaks.parquet")
    peaks = peaks.assign(mz=peaks["mz"].astype(float))
    has_snr = "signal_to_noise" in peaks.columns
    has_sat = "is_satellite" in peaks.columns
    print(f"scorer={a.scorer}  signal_to_noise={'present' if has_snr else 'PROXY (from heights)'}"
          f"  satellites={'excluded' if has_sat else 'n/a'}")

    # per-file observed peak arrays (+ a noise floor for the v2 detectability gate).
    # Satellites (signal artifacts near intense peaks) are dropped from the observed
    # set when flagged. noise = median(height/SNR) when SNR is exported, else a low
    # height percentile as a per-file floor proxy.
    obs = {}
    for f, g in peaks.sort_values("mz").groupby("filename"):
        if has_sat:
            g = g[~g["is_satellite"].astype(bool)]
        h = g["height"].to_numpy(float)
        if has_snr:
            snr = g["signal_to_noise"].to_numpy(float)
            ok = snr > 0
            noise = float(np.median(h[ok] / snr[ok])) if ok.any() else float(np.min(h) if len(h) else 1.0)
        else:
            noise = float(np.percentile(h, 2)) if len(h) else 1.0
        obs[f] = (g["mz"].to_numpy(float), h, noise)

    cand_path = f"{a.bundle_dir}/expected/candidates.parquet"
    try:
        cands = pd.read_parquet(cand_path)
    except Exception:
        print(f"!! {cand_path} not found — run make_candidates.py first.")
        return 2

    # score every candidate
    def score_all() -> np.ndarray:
        out = np.full(len(cands), np.nan)
        for idx, r in enumerate(cands.itertuples()):
            rec = obs.get(r.filename)
            if rec is None:
                continue
            mzs, ints, noise = rec
            if a.scorer == "v2":
                s = score_ion_v2(mzs, ints, r.candidate_ion, ppm=a.ppm, noise=noise)
            else:
                s = score_ion(mzs, ints, r.candidate_ion, ppm=a.ppm)
            if s is not None:
                out[idx] = s
        return out

    s1 = score_all()
    s2 = score_all()
    reproducible = bool(np.array_equal(np.nan_to_num(s1, nan=-1), np.nan_to_num(s2, nan=-1)))
    cands = cands.assign(score=s1)

    # ---- ranking: per anchor, is the true candidate the argmax? ----
    top1, top1_contested, n_contested = [], [], 0
    for (_, _), g in cands.groupby(["filename", "anchor_mz"]):
        g = g.dropna(subset=["score"])
        if g.empty or not g["is_true"].any():
            continue
        win_true = bool(g.loc[g["score"].idxmax(), "is_true"])
        top1.append(win_true)
        if len(g) > 1:  # contested = has at least one decoy
            n_contested += 1
            top1_contested.append(win_true)

    auc = _roc_auc(cands["is_true"].to_numpy(int), np.nan_to_num(cands["score"].to_numpy(), nan=0.0))

    # ---- calibration over the candidate pool ----
    valid = cands.dropna(subset=["score"])
    ece = _ece(valid["score"].to_numpy(), valid["is_true"].to_numpy(int))

    # ---- baseline score distribution of the TRUE assignments ----
    true_scores = valid.loc[valid["is_true"], "score"].to_numpy()

    metrics = {
        "n_anchors": int(len(top1)),
        "n_contested": int(n_contested),
        "reproducible": reproducible,
        "rank_top1_all": round(float(np.mean(top1)), 4) if top1 else None,
        "rank_top1_contested": round(float(np.mean(top1_contested)), 4) if top1_contested else None,
        "roc_auc": round(auc, 4),
        "ece": round(ece, 4),
        "true_score_median": round(float(np.median(true_scores)), 4) if len(true_scores) else None,
        "true_score_p10": round(float(np.percentile(true_scores, 10)), 4) if len(true_scores) else None,
    }

    print("=== match-score evaluation (mascope_tools baseline) ===")
    for k, v in metrics.items():
        print(f"  {k:<22} {v}")

    if a.out:
        json.dump(metrics, open(a.out, "w"), indent=2)
        print(f"\nwrote {a.out}")

    if a.baseline:
        base = json.load(open(a.baseline))
        regressed = []
        for key in ("rank_top1_contested", "roc_auc"):
            b, n = base.get(key), metrics.get(key)
            if b is not None and n is not None and n < b - 1e-9:
                regressed.append(f"{key}: {b} -> {n}")
        if not metrics["reproducible"]:
            regressed.append("reproducibility: scoring is non-deterministic")
        if regressed:
            print("\nREGRESSION vs baseline:\n  " + "\n  ".join(regressed))
            return 1
        print("\nno regression vs baseline.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
