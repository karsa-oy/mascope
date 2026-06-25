"""Parity: ``mascope_tools`` ``predict_isotopes`` vs the molmass ``Formula.spectrum()``
ground-truth, for non-labelled ions AND labelled custom-element ('^N') ions.

molmass (an independent isotope-pattern implementation) is the reference the backend
already trusts. This guards the self-contained custom-element convolution in
``predict_isotopes`` against drift, and the non-labelled cases guard against
regressions in the standard IsoSpec path.

We assert parity on the chemically significant peaks (>= 1.5% relative, which
includes the ~2% 14N satellite of a labelled reagent). Trace peaks below that are
threshold/grouping-convention dependent between IsoSpec and molmass and are not
asserted -- they are negligible for scoring (mass-dominated 0.6/0.2/0.2).
"""
import numpy as np
import pytest

pytest.importorskip("mascope_molmass")
from mascope_molmass import Formula  # noqa: E402

from mascope_tools.composition.config import ELECTRON_MASS  # noqa: E402
from mascope_tools.composition.heuristic_filter import predict_isotopes  # noqa: E402

SIGNIFICANT = 0.015  # relative-abundance floor for asserted peaks
MZ_TOL = 0.003
INT_TOL = 0.04

# (tools ion formula without charge sign, charge, equivalent molmass formula)
CASES = [
    ("C6H12O6", -1, "C6H12O6"),        # non-labelled (regression)
    ("C6H12BrO6", -1, "C6H12BrO6"),    # bromine envelope (M+2 ~ base)
    ("C5H8O6^N", -1, "C5H8^NO6"),      # 15N-nitrate adduct ion
    ("C10H15O3^N", -1, "C10H15^NO3"),  # another 15N case
    ("C3H4O3^N2", -1, "C3H4^N2O3"),    # two labelled atoms (multinomial)
    ("C8H10O3^N", 1, "C8H10^NO3"),     # positive charge
]


def _tools_envelope(ion: str, charge: int):
    mz, pr, _ = predict_isotopes(ion, charge)
    mz, pr = np.asarray(mz, float), np.asarray(pr, float)
    assert mz.size > 0, f"{ion}: predict_isotopes returned empty"
    return mz, pr / pr.max()


def _molmass_envelope(mm_formula: str, charge: int):
    gt = [(e.mass, e.fraction) for e in Formula(mm_formula).spectrum().values()]
    gmax = max(f for _, f in gt)
    # neutral mass -> m/z to compare on the same axis as tools
    return [((m - ELECTRON_MASS * charge) / abs(charge), f / gmax) for m, f in gt]


@pytest.mark.parametrize("ion,charge,mm", CASES)
def test_predict_isotopes_matches_molmass(ion, charge, mm):
    mz, rel = _tools_envelope(ion, charge)
    gt = _molmass_envelope(mm, charge)

    # every significant molmass peak has a matching tools peak (mass + intensity)
    for gmz, gf in gt:
        if gf < SIGNIFICANT:
            continue
        j = int(np.argmin(np.abs(mz - gmz)))
        assert abs(mz[j] - gmz) < MZ_TOL, f"{ion}: no tools peak near {gmz:.4f}"
        assert abs(rel[j] - gf) < INT_TOL, (
            f"{ion}: intensity at {gmz:.4f}: tools {rel[j]:.3f} vs molmass {gf:.3f}"
        )

    # and tools predicts no spurious significant peak that molmass lacks
    gt_mz = np.array([m for m, _ in gt])
    for k in np.where(rel >= SIGNIFICANT)[0]:
        assert np.min(np.abs(gt_mz - mz[k])) < MZ_TOL, (
            f"{ion}: tools predicts spurious peak at {mz[k]:.4f} ({rel[k]:.3f})"
        )


def test_15n_satellite_present_and_base_is_15n():
    """The defining 15N behaviour: the dominant (base) peak is the 15N form, with a
    ~2% 14N satellite ~0.997 Da below it (purity default 0.98)."""
    mz, rel = _tools_envelope("C5H8O6^N", -1)
    base = int(np.argmax(rel))
    satellite = np.where((mz < mz[base] - 0.9) & (mz > mz[base] - 1.1))[0]
    assert satellite.size == 1, "expected exactly one 14N satellite below the base"
    assert 0.01 < rel[satellite[0]] < 0.035, "14N satellite should be ~2%"
