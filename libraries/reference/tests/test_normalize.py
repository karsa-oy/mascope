"""Formula/mass canonicalization tests."""

import pytest

from mascope_reference.normalize import (
    canonical_formula,
    finalize,
    monoisotopic_mass,
)
from mascope_reference.record import ReferenceRecord


def _record(formula: str, **kw) -> ReferenceRecord:
    return ReferenceRecord(
        formula=formula,
        source="test",
        source_native_id="1",
        license="test",
        **kw,
    )


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("C6H12O6", "C6H12O6"),
        ("H2O", "H2O"),
        # Element order is normalized to Hill (C, H, then alphabetical).
        ("O2C1H4", "CH4O2"),
        # Isotope labels collapse to the base element, matching the de novo path.
        ("[13C]C5H12O6", "C6H12O6"),
    ],
)
def test_canonical_formula_normalizes(raw, expected):
    assert canonical_formula(raw) == expected


@pytest.mark.parametrize("raw", ["", "()", "123", "-", "+"])
def test_canonical_formula_rejects_unusable(raw):
    assert canonical_formula(raw) is None


def test_monoisotopic_mass_matches_known_values():
    assert monoisotopic_mass("H2O") == pytest.approx(18.0106, abs=1e-3)
    assert monoisotopic_mass("C6H12O6") == pytest.approx(180.0634, abs=1e-3)


def test_monoisotopic_mass_unknown_element_is_none():
    # 'Xx' is not a real element; mass computation fails softly.
    assert monoisotopic_mass("Xx2") is None


def test_finalize_canonicalizes_and_computes_mass():
    result = finalize(_record("[13C]C5H12O6"))
    assert result is not None
    assert result.formula == "C6H12O6"
    assert result.monoisotopic_mass == pytest.approx(180.0634, abs=1e-3)


def test_finalize_drops_unusable_formula():
    assert finalize(_record("")) is None


def test_finalize_keeps_source_provided_mass_when_uncomputable():
    # Formula parses to a (fake) element that cannot be massed; the source's own
    # mass is retained as a fallback rather than nulled.
    record = _record("Xx2", monoisotopic_mass=123.45)
    result = finalize(record)
    assert result is not None
    assert result.monoisotopic_mass == pytest.approx(123.45)
