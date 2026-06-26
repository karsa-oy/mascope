"""Unit tests for the Senior/RDBE structural-feasibility rule (Golden Rule 2).

Contract: the rule judges NEUTRAL formulas (as produced by `find_compositions` before
ionization) and rejects ONLY the impossible (over-saturated, negative-RDBE) ones. It
deliberately FAILS OPEN on odd-electron radicals, which can be genuine in APCI/APPI.
See docs/dev/assignment_confidence.md (P1).
"""

import polars as pl

from mascope_tools.composition.heuristic_filter import rule_senior


def _mask(formulas):
    mask, _ = rule_senior(pl.DataFrame({"formula": formulas}))
    return list(mask)


def test_valid_molecules_pass():
    # benzene (RDBE 4), glucose (1), caffeine (6), water, ammonia, methane, acetic acid
    assert _mask(
        ["C6H6", "C6H12O6", "C8H10N4O2", "H2O", "NH3", "CH4", "C2H4O2"]
    ) == [True] * 7


def test_oversaturated_formulas_rejected():
    # too many H for the carbon skeleton -> negative RDBE, impossible for any structure
    assert _mask(["CH5", "C2H8", "C2H10", "C6H17NO4"]) == [False, False, False, False]


def test_odd_electron_radicals_fail_open():
    # non-integer RDBE marks an open-shell radical; these can be genuine (APCI/APPI), so
    # the rule passes them rather than rejecting (only impossible formulas are cut)
    assert _mask(["CH3", "C2H5", "NH2", "C10H15O5", "C9H15O6", "Br"]) == [True] * 6


def test_unknown_elements_fail_open():
    # any element outside the standard valence table -> never rejected here
    assert _mask(["C2H6Fe", "FeCl3", "C6H5MgBr"]) == [True, True, True]


def test_empty_input():
    assert _mask([]) == []


def test_single_atom_and_diatomic():
    # connectivity must not reject trivial cases that are chemically real
    assert _mask(["H2O", "CO2", "N2"]) == [True, True, True]
