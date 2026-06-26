"""Unit tests for the Lewis/Senior structural-feasibility rule (Golden Rule 2).

Contract: the rule judges NEUTRAL, closed-shell formulas (as produced by
`find_compositions` before ionization). Charge-adjusted/ionic formulas (e.g. a stored
[M-H] form) can read as odd-electron or over-saturated and are correctly flagged — so the
rule must never be applied to ion formulas. See docs/dev/assignment_confidence.md (P1).
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
    # too many H for the carbon skeleton -> negative RDBE, impossible
    assert _mask(["CH5", "C2H8", "C2H10"]) == [False, False, False]


def test_odd_electron_radicals_rejected():
    # odd total valence (non-integer RDBE) -> not a closed-shell neutral
    assert _mask(["CH3", "C2H5", "NH2"]) == [False, False, False]


def test_unknown_elements_fail_open():
    # any element outside the standard valence table -> never rejected here
    assert _mask(["C2H6Fe", "FeCl3", "C6H5MgBr"]) == [True, True, True]


def test_empty_input():
    assert _mask([]) == []


def test_single_atom_and_diatomic():
    # connectivity must not reject trivial cases that are chemically real
    assert _mask(["H2O", "CO2", "N2"]) == [True, True, True]
