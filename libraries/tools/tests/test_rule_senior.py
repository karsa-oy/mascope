"""Unit tests for the Senior/RDBE structural-feasibility rule (Golden Rule 2).

Contract: the rule judges NEUTRAL formulas (as produced by `find_compositions` before
ionization) and rejects ONLY the impossible (over-saturated, negative-RDBE) ones. It
deliberately FAILS OPEN on odd-electron radicals, which can be genuine in APCI/APPI.
See docs/dev/assignment_confidence.md (P1).

The rule is opt-in (`HeuristicFilterConfig.use_senior`) because it replaced a no-op
placeholder; these tests enable it explicitly, and `test_disabled_by_default` pins the
off-by-default behaviour that keeps the legacy composition search unchanged.
"""

import polars as pl

from mascope_tools.composition.heuristic_filter import rule_senior
from mascope_tools.composition.models import HeuristicFilterConfig


def _mask(formulas, use_senior=True):
    mask, _ = rule_senior(
        pl.DataFrame({"formula": formulas}),
        heuristics_config=HeuristicFilterConfig(use_senior=use_senior),
    )
    return list(mask)


def test_disabled_by_default():
    """Off by default: an impossible formula still passes, as it did pre-Rule-2."""
    formulas = ["C6H17NO4", "C6H12O6"]
    assert _mask(formulas, use_senior=False) == [True, True]
    # And the default config (no explicit use_senior) is likewise off.
    mask, _ = rule_senior(pl.DataFrame({"formula": formulas}))
    assert list(mask) == [True, True]


def test_valid_molecules_pass():
    # benzene (RDBE 4), glucose (1), caffeine (6), water, ammonia, methane, acetic acid
    assert (
        _mask(["C6H6", "C6H12O6", "C8H10N4O2", "H2O", "NH3", "CH4", "C2H4O2"])
        == [True] * 7
    )


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
