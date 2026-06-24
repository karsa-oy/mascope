"""
Reproducibility comparison: produced peaks vs. golden expected outputs.

The core :func:`compare_peaks` is pure DataFrame logic shared by the
``mascope demo verify`` command and the end-to-end reproducibility test, so the
two can never drift. It takes the golden ``expected`` peaks (shipped in the
bundle) and the ``actual`` peaks produced by re-running the pipeline, and
reports every difference outside the manifest's tolerances.

Obtaining the ``actual`` peaks requires a live, freshly-rebuilt demo stack;
that export seam is wired by the caller (see ``docs/demo_dataset.md``). This
module only owns the comparison.
"""

from typing import Any


# Default tolerances if a manifest omits them.
DEFAULT_TOLERANCES: dict[str, float] = {
    "mz_ppm": 1.0,
    "intensity_rel": 0.01,
    "area_rel": 0.02,
}


def compare_peaks(
    expected: "Any",
    actual: "Any",
    tolerances: dict[str, float] | None = None,
    *,
    mz_col: str = "mz",
    intensity_col: str = "height",
    area_col: str = "area",
    compound_col: str = "target_compound_formula",
) -> list[str]:
    """
    Compare produced peaks against golden peaks within tolerances.

    Each expected peak is matched to the nearest actual peak by m/z. A match
    outside ``mz_ppm`` counts as missing. For matched peaks, intensity and area
    are compared by relative difference. Finally the set of matched compound
    formulae is compared for equality.

    :param expected: Golden peaks (``pandas.DataFrame``).
    :param actual: Produced peaks (``pandas.DataFrame``).
    :param tolerances: Dict with ``mz_ppm``, ``intensity_rel``, ``area_rel``.
                       Missing keys fall back to :data:`DEFAULT_TOLERANCES`.
    :param mz_col: Column name for m/z in both frames.
    :param intensity_col: Column name for peak height/intensity.
    :param area_col: Column name for peak area.
    :param compound_col: Column name for the matched compound formula.
    :return: List of human-readable difference messages (empty = reproduced).
    """
    import pandas as pd  # local import: keep CLI import-light

    tol = {**DEFAULT_TOLERANCES, **(tolerances or {})}
    problems: list[str] = []

    exp = expected.sort_values(mz_col).reset_index(drop=True)
    act = actual.sort_values(mz_col).reset_index(drop=True)

    if act.empty:
        return [f"no peaks produced (expected {len(exp)})"]

    act_mz = act[mz_col].to_numpy()

    for _, erow in exp.iterrows():
        emz = float(erow[mz_col])
        # nearest actual peak by m/z
        idx = int((pd.Series(act_mz) - emz).abs().idxmin())
        amz = float(act_mz[idx])
        ppm = abs(amz - emz) / emz * 1e6
        if ppm > tol["mz_ppm"]:
            problems.append(
                f"m/z {emz:.5f}: no match within {tol['mz_ppm']} ppm "
                f"(nearest {amz:.5f}, {ppm:.2f} ppm)"
            )
            continue

        arow = act.iloc[idx]
        _check_rel(problems, emz, "intensity", erow, arow, intensity_col, tol["intensity_rel"])
        _check_rel(problems, emz, "area", erow, arow, area_col, tol["area_rel"])

    # Compound-set equality (ignore unmatched/NaN).
    exp_cmp = _formula_set(exp, compound_col)
    act_cmp = _formula_set(act, compound_col)
    for missing in sorted(exp_cmp - act_cmp):
        problems.append(f"compound not matched in actual: {missing}")
    for extra in sorted(act_cmp - exp_cmp):
        problems.append(f"unexpected compound matched: {extra}")

    return problems


def _check_rel(
    problems: list[str],
    mz: float,
    label: str,
    erow: "Any",
    arow: "Any",
    col: str,
    rel_tol: float,
) -> None:
    """Append a problem if ``col`` differs by more than ``rel_tol`` (relative)."""
    if col not in erow or col not in arow:
        return
    ev, av = erow[col], arow[col]
    if ev is None or av is None:
        return
    try:
        ev, av = float(ev), float(av)
    except (TypeError, ValueError):
        return
    denom = abs(ev) if ev else 1.0
    rel = abs(av - ev) / denom
    if rel > rel_tol:
        problems.append(
            f"m/z {mz:.5f}: {label} differs by {rel * 100:.2f}% "
            f"(expected {ev:.4g}, got {av:.4g}, tol {rel_tol * 100:.1f}%)"
        )


def _formula_set(frame: "Any", col: str) -> set[str]:
    """Return the set of non-null formula strings in ``col`` (empty if absent)."""
    if col not in frame:
        return set()
    return set(frame[col].dropna().astype(str)) - {""}
