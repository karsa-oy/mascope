"""Target compound formula validation.

Mass-based target compounds (a bare numeric mass instead of a chemical formula)
are no longer supported; the pydantic models reject them at the API boundary.
"""

import pytest
from pydantic import ValidationError

from mascope_backend.api.models.target.compounds.target_compound_pydantic_model import (
    TargetCompoundBase,
    TargetCompoundMatches,
    TargetCompoundUpdate,
)


@pytest.mark.parametrize(
    "formula",
    ["C6H12O6", "H2O", "CH4N2O", "H^NO3", "(HNO3)2", "()"],
)
def test_chemical_formulas_are_accepted(formula):
    assert TargetCompoundBase(target_compound_formula=formula)
    assert TargetCompoundMatches(target_compound_formula=formula)


@pytest.mark.parametrize(
    "mass_formula",
    ["136.1252", "60", "0", "  42.0 ", "1e3", "18.01056"],
)
def test_mass_only_formulas_are_rejected(mass_formula):
    # Base creation model
    with pytest.raises(ValidationError):
        TargetCompoundBase(target_compound_formula=mass_formula)
    # Match request model (inherits the validator)
    with pytest.raises(ValidationError):
        TargetCompoundMatches(target_compound_formula=mass_formula)


@pytest.mark.parametrize(
    "formula",
    ["NaN", "InN", "CoInS"],
)
def test_formulas_that_float_would_misparse_are_accepted(formula):
    # float("NaN"/"InN"...) parses "NaN" as not-a-number but the old float()
    # guard rejected "NaN" (a valid Na+N formula); the numeric-pattern guard
    # only rejects actual numeric masses.
    assert TargetCompoundBase(target_compound_formula=formula)


def test_update_model_rejects_mass_but_allows_none():
    # Formula is optional on update; None is allowed (formula left unchanged)
    assert TargetCompoundUpdate(target_compound_id="x").target_compound_formula is None
    with pytest.raises(ValidationError):
        TargetCompoundUpdate(target_compound_id="x", target_compound_formula="12.3")
