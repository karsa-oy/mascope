"""
Reproducibility comparison: produced peaks vs. golden expected outputs.

The core :func:`compare_peaks` is pure DataFrame logic shared by the
``mascope demo verify`` command and the end-to-end reproducibility test, so the
two can never drift. It takes the golden ``expected`` peaks (shipped in the
bundle) and the ``actual`` peaks produced by re-running the pipeline, and
reports every difference outside the manifest's tolerances.

Each peak is identified by a **stable key** - by default ``(filename,
target_isotope_id)`` - that survives a rebuild (the raw filename is unique and
the target isotope comes from the restored seed), unlike ``sample_item_id``
which is regenerated on every ingestion. The comparison is a keyed merge on that
key: every expected peak must have an actual peak with the same key whose m/z and
intensity are within tolerance, and there must be no unexpected extra peaks.

Obtaining the ``actual`` peaks requires a live, freshly-rebuilt demo stack;
that export seam is ``mascope_backend.db.scripts.export_goldens``. This module
only owns the comparison.
"""

from typing import Any


# Canonical default tolerances: written into a freshly built bundle's manifest
# and used as the fallback when a manifest omits them. The m/z tolerance is
# sub-ppm because the demo data is high-resolution Orbitrap - the Thermo reader
# reproduces matched-peak m/z to sub-0.1 ppm (see libraries/thermo), so 1 ppm
# would be far too loose to catch a real mass-accuracy regression.
DEFAULT_TOLERANCES: dict[str, float] = {
    "mz_ppm": 0.1,
    "intensity_rel": 0.01,
    "area_rel": 0.02,
}


def compare_peaks(
    expected: "Any",
    actual: "Any",
    tolerances: dict[str, float] | None = None,
    *,
    key_cols: tuple[str, ...] = ("filename", "target_isotope_id"),
    mz_col: str = "mz",
    intensity_col: str = "height",
    formula_col: str = "target_isotope_formula",
) -> list[str]:
    """
    Compare produced peaks against golden peaks by stable key, within tolerances.

    Expected and actual are joined on ``key_cols``. For each peak present in both,
    m/z is compared in ppm and intensity by relative difference. Peaks present in
    only one side are reported as missing/unexpected.

    :param expected: Golden peaks (``pandas.DataFrame``).
    :param actual: Produced peaks (``pandas.DataFrame``).
    :param tolerances: Dict with ``mz_ppm`` and ``intensity_rel``. Missing keys
                       fall back to :data:`DEFAULT_TOLERANCES`.
    :param key_cols: Columns forming the stable per-peak key.
    :param mz_col: Column name for m/z in both frames.
    :param intensity_col: Column name for peak height/intensity.
    :param formula_col: Column name for the isotope formula (used only to make
                        missing/unexpected messages readable).
    :return: List of human-readable difference messages (empty = reproduced).
    """
    import numpy as np  # local import: keep CLI import-light

    tol = {**DEFAULT_TOLERANCES, **(tolerances or {})}
    keys = list(key_cols)
    problems: list[str] = []

    # Duplicate keys make the join ambiguous - flag rather than silently pick one.
    for label, frame in (("expected", expected), ("actual", actual)):
        dupes = int(frame.duplicated(keys).sum())
        if dupes:
            problems.append(f"{label} has {dupes} duplicate key(s) on {keys}")
    exp = expected.drop_duplicates(keys)
    act = actual.drop_duplicates(keys)

    merged = exp.merge(
        act, on=keys, how="outer", suffixes=("_exp", "_act"), indicator=True
    )

    # Peaks on only one side.
    f_exp = f"{formula_col}_exp" if formula_col != keys[-1] else formula_col
    f_act = f"{formula_col}_act" if formula_col != keys[-1] else formula_col
    for _, row in merged[merged["_merge"] == "left_only"].iterrows():
        problems.append(f"missing peak: {_key_str(keys, row)} ({row.get(f_exp, '')})")
    for _, row in merged[merged["_merge"] == "right_only"].iterrows():
        problems.append(
            f"unexpected peak: {_key_str(keys, row)} ({row.get(f_act, '')})"
        )

    # Peaks on both sides: vectorized m/z + intensity tolerance checks.
    both = merged[merged["_merge"] == "both"]
    if not both.empty:
        emz = both[f"{mz_col}_exp"].to_numpy(dtype=float)
        amz = both[f"{mz_col}_act"].to_numpy(dtype=float)
        with np.errstate(divide="ignore", invalid="ignore"):
            ppm = np.where(emz != 0, np.abs(amz - emz) / np.abs(emz) * 1e6, 0.0)
        for _, row, e, a, p in _violations(both, ppm > tol["mz_ppm"], emz, amz, ppm):
            problems.append(
                f"{_key_str(keys, row)}: m/z off by {p:.2f} ppm "
                f"(expected {e:.5f}, got {a:.5f}, tol {tol['mz_ppm']} ppm)"
            )

        ev = both[f"{intensity_col}_exp"].to_numpy(dtype=float)
        av = both[f"{intensity_col}_act"].to_numpy(dtype=float)
        denom = np.where(ev != 0, np.abs(ev), 1.0)
        rel = np.abs(av - ev) / denom
        int_tol = tol["intensity_rel"]
        for _, row, e, a, r in _violations(both, rel > int_tol, ev, av, rel):
            problems.append(
                f"{_key_str(keys, row)}: intensity differs by {r * 100:.2f}% "
                f"(expected {e:.4g}, got {a:.4g}, tol {int_tol * 100:.1f}%)"
            )

    return problems


def _violations(frame, mask, expected_vals, actual_vals, metric_vals):
    """Yield ``(idx, row, expected, actual, metric)`` for rows failing ``mask``."""
    idxs = mask.nonzero()[0]
    for i in idxs:
        yield (
            i,
            frame.iloc[i],
            float(expected_vals[i]),
            float(actual_vals[i]),
            float(metric_vals[i]),
        )


def _key_str(keys: list[str], row: "Any") -> str:
    """Render a peak's key columns as ``col=value`` pairs for messages."""
    return ", ".join(f"{k}={row[k]}" for k in keys)
