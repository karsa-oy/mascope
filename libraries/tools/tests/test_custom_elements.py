"""Tests for the shared custom-element registry and the classic-Hill formatter.

These consolidate chemistry knowledge that previously lived in the mascope_molmass
fork, so they guard the contract the Mascope backend now depends on.
"""

import pytest

from mascope_tools.composition.custom_elements import (
    CUSTOM_ELEMENTS,
    CustomElement,
    is_custom_element,
)
from mascope_tools.composition.utils import (
    CARET_ISOTOPES,
    parse_formula_tokens,
    to_hill_notation,
    to_hill_order,
)


def test_registry_has_labelled_nitrogen():
    ce = CUSTOM_ELEMENTS["^N"]
    assert isinstance(ce, CustomElement)
    assert ce.base_element == "N"
    assert ce.default_purity == 0.98
    # lightest first: 14N then labelled 15N
    assert [mn for _, mn in ce.isotopes] == [14, 15]
    assert ce.labelled_massnumber == 15
    assert ce.pyteomics_isotope == "N[15]"


def test_is_custom_element():
    assert is_custom_element("^N")
    assert not is_custom_element("N")
    assert not is_custom_element("[15N]")


def test_caret_isotopes_derived_from_registry():
    # The pyteomics mass-mapping is derived from the registry, not hard-coded.
    assert CARET_ISOTOPES == {"^N": "N[15]"}


@pytest.mark.parametrize(
    "formula,expected",
    [
        ("C6H12O6", {"C": 6, "H": 12, "O": 6}),
        ("[15N]BrHO3", {"[15N]": 1, "Br": 1, "H": 1, "O": 3}),
        ("HN^NO6", {"H": 1, "N": 1, "^N": 1, "O": 6}),
        ("", {}),
    ],
)
def test_parse_formula_tokens(formula, expected):
    assert parse_formula_tokens(formula) == expected


@pytest.mark.parametrize(
    "formula,expected",
    [
        # carbon present: C, H, then alphabetical
        ("CH4N2O", "CH4N2O"),
        # no carbon: ALL elements alphabetical (H is NOT forced second)
        ("BrHO3", "BrHO3"),
        ("H2OBr", "BrH2O"),
        # caret custom element sorts after regular elements
        ("O3^N", "O3^N"),
        ("H^NO3", "HO3^N"),
        # bracket isotope sorts as its base element; plain before isotopic
        ("[15N]BrHO3", "BrH[15N]O3"),
        ("[13C]C5H12O6", "C5[13C]H12O6"),
    ],
)
def test_to_hill_notation_matches_classic_hill(formula, expected):
    assert to_hill_notation(parse_formula_tokens(formula)) == expected


def test_to_hill_notation_differs_from_to_hill_order_without_carbon():
    # Documents the intentional difference: to_hill_order forces H second,
    # classic Hill keeps everything alphabetical when no carbon is present.
    counts = parse_formula_tokens("BrHO3")
    assert to_hill_notation(counts) == "BrHO3"
    assert to_hill_order(dict(counts)) == "HBrO3"
