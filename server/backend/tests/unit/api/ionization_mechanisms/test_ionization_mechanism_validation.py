"""Ionization mechanism formula validation.

The mechanism modification formula is validated (strictly) via
mascope_tools.composition.utils.assert_valid_formula, which raises on invalid
characters and unknown elements rather than silently ignoring them.
"""

import pytest
from pydantic import ValidationError

from mascope_backend.api.models.ionization_mechanisms.ionization_mechanism_pydantic_model import (
    IonizationMechanismCreate,
)


@pytest.mark.parametrize(
    "mechanism",
    [
        "+H+",  # protonation
        "-H+",  # deprotonation
        "+Br-",  # bromide adduct
        "+NO3-",  # nitrate adduct
        "+^NO3-",  # 15N-labelled nitrate adduct (custom element)
        "+(CH4N2O)H+",  # parenthesised adduct
        "+",  # electron abstraction
        "-",  # electron capture
    ],
)
def test_valid_mechanisms_accepted(mechanism):
    assert IonizationMechanismCreate(ionization_mechanism=mechanism)


@pytest.mark.parametrize(
    "mechanism",
    [
        "+Zz+",  # unknown element
        "+H!+",  # invalid character
        "+(H+",  # unbalanced parenthesis
        "H+",  # missing leading operation
        "+H",  # missing trailing polarity
        "+-",  # invalid sign combination
        "++",  # empty modification formula (used to hang ion generation)
        "--",  # empty modification formula
    ],
)
def test_invalid_mechanisms_rejected(mechanism):
    with pytest.raises(ValidationError):
        IonizationMechanismCreate(ionization_mechanism=mechanism)
