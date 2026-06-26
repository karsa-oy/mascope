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


def load_filestore_peaks(bundle_dir: str, filename: str, _cache: dict = {}) -> "pd.DataFrame | None":
    """Full detected-peak list for a sample from its `peak_timeseries.zarr` in the
    filestore: m/z, summed height, real `signal_to_noise`, and `is_satellite`. This
    is the COMPLETE spectrum (not the matched-target subset) WITH SNR — so it
    replaces both the matched-peak proxy and the proxy noise floor. None if absent."""
    if filename in _cache:
        return _cache[filename]
    import glob

    import xarray as xr

    hits = glob.glob(
        f"{bundle_dir}/snapshot/filestore/**/{filename}/peak_timeseries.zarr",
        recursive=True,
    )
    if not hits:
        _cache[filename] = None
        return None
    ds = xr.open_zarr(hits[0])
    df = (
        pd.DataFrame(
            {
                "mz": ds["mz"].values.astype(float),
                "height": ds["sum_peak_heights"].values.astype(float),
                "snr": ds["signal_to_noise"].values.astype(float),
                "is_satellite": ds["is_satellite"].values.astype(bool),
            }
        )
        .sort_values("mz")
        .reset_index(drop=True)
    )
    _cache[filename] = df
    return df


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
    snrs: "np.ndarray | None",
    ion: str,
    *,
    ppm: float,
    noise: float = 0.0,
    k_detect: float = 3.0,
    miss_penalty: float = 0.3,
    sigma_ppm: float = 2.0,
) -> float | None:
    """Detectability-gated score (DESIGN.md §4). Unlike v1, a predicted
    isotopologue that is ABSENT but *should have been visible* is penalized rather
    than ignored — the fix for over-crediting incomplete envelopes. "Should have
    been visible" uses the base peak's real SNR when available: expected
    SNR(isotopologue i) = rel_i · SNR_base ≥ k_detect; else falls back to a noise
    floor (rel_i·base ≥ k_detect·noise). Mass uses a Gaussian likelihood normalised
    by `sigma_ppm`; aggregation is a predicted-abundance-weighted geometric mean
    (harsh: a missing detectable peak drags the score down). Satellites are dropped
    from `mzs/ints/snrs` by the caller."""
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

    base_int = base_snr = None
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
            base_snr = float(snrs[k]) if snrs is not None else None
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
            if base_snr is not None:
                detectable = pred_rel[i] * base_snr >= k_detect
            else:
                detectable = pred_rel[i] * base_int >= k_detect * noise
            if detectable:
                L = miss_penalty
            else:
                continue  # below detection -> not evidence, exclude
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
    ap.add_argument("--k-detect", type=float, default=3.0, help="v2: min expected SNR to call an absent isotopologue 'missing'")
    ap.add_argument("--miss-penalty", type=float, default=0.3, help="v2: likelihood for a detectable-but-absent isotopologue")
    ap.add_argument("--sigma-ppm", type=float, default=2.0, help="v2: mass-error Gaussian width")
    ap.add_argument("--baseline", help="JSON to compare against (regression gate)")
    ap.add_argument("--out", help="write metrics JSON here")
    a = ap.parse_args()

    cand_path = f"{a.bundle_dir}/expected/candidates.parquet"
    filenames = pd.read_parquet(cand_path, columns=["filename"])["filename"].unique() \
        if __import__("os").path.exists(cand_path) else []

    # Observed peaks per file: prefer the FULL spectrum + real SNR from the
    # filestore's peak_timeseries.zarr (satellites dropped); fall back to the
    # matched-target peaks in expected/peaks.parquet (proxy, noise from heights).
    matched = pd.read_parquet(f"{a.bundle_dir}/expected/peaks.parquet")
    matched = matched.assign(mz=matched["mz"].astype(float))
    obs = {}
    n_fs = 0
    for f in filenames:
        df = load_filestore_peaks(a.bundle_dir, f)
        if df is not None:
            df = df[~df["is_satellite"]]
            obs[f] = (df["mz"].to_numpy(float), df["height"].to_numpy(float),
                      df["snr"].to_numpy(float), 0.0)
            n_fs += 1
        else:
            g = matched[matched["filename"] == f].sort_values("mz")
            h = g["height"].to_numpy(float)
            noise = float(np.percentile(h, 2)) if len(h) else 1.0
            obs[f] = (g["mz"].to_numpy(float), h, None, noise)
    src = "filestore peak_timeseries.zarr (real SNR, full spectrum)" if n_fs else \
        "matched-target proxy (no SNR)"
    print(f"scorer={a.scorer}  peaks: {n_fs}/{len(filenames)} files from {src}")

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
            mzs, ints, snrs, noise = rec
            if a.scorer == "v2":
                s = score_ion_v2(mzs, ints, snrs, r.candidate_ion, ppm=a.ppm, noise=noise,
                                 k_detect=a.k_detect, miss_penalty=a.miss_penalty,
                                 sigma_ppm=a.sigma_ppm)
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
