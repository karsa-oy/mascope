"""Canonicalization of reference formulas and masses.

Reference formulas must land in the exact same canonical Hill order as
de novo assigned formulas, or annotation lookups silently miss. Both paths
therefore share ``mascope_tools.composition``: the de novo cheminfo service
canonicalizes with ``to_hill_order(parse_composition(...))`` over an
isotope-normalized formula, and this module does the same, so a reference row
and an assigned result key on identical strings.
"""

from mascope_reference.record import ReferenceRecord
from mascope_tools.composition.utils import (
    composition_mass,
    normalize_formula_with_isotopes,
    parse_composition,
    to_hill_order,
)


# ``to_hill_order`` returns this sentinel for an empty/unparseable composition.
_EMPTY_FORMULA = "()"


def canonical_formula(formula: str) -> str | None:
    """Canonicalize a source formula to neutral Hill order.

    Returns ``None`` when the formula cannot be parsed into any element (empty
    string, an R-group placeholder, a lone charge, etc.) so callers can drop
    the record rather than store an unusable key. Isotope labels are collapsed
    to their base element, matching the de novo path which never emits isotope
    labels in an assigned neutral formula.

    :param formula: Raw formula string from a source dump.
    :return: Canonical Hill-order formula, or ``None`` if it has no elements.
    """
    if not formula:
        return None
    try:
        composition = parse_composition(normalize_formula_with_isotopes(formula))
        hill = to_hill_order(composition)
    except Exception:
        return None
    if hill == _EMPTY_FORMULA or not hill:
        return None
    return hill


def monoisotopic_mass(formula: str) -> float | None:
    """Monoisotopic mass of a neutral formula, or ``None`` if it cannot be massed.

    Computed from the (already canonical) formula rather than trusting a
    source-provided mass, so the value is always consistent with the formula
    Mascope indexes and matches against. Elements unknown to the underlying
    mass table (or malformed formulas) yield ``None`` instead of raising.

    :param formula: Neutral formula string.
    :return: Monoisotopic mass, or ``None`` on failure.
    """
    if not formula:
        return None
    try:
        mass = composition_mass(parse_composition(formula))
    except Exception:
        return None
    return mass if mass > 0 else None


def finalize(record: ReferenceRecord) -> ReferenceRecord | None:
    """Canonicalize a record's formula and (re)compute its monoisotopic mass.

    Returns a new record with ``formula`` in canonical Hill order and
    ``monoisotopic_mass`` computed from it. Returns ``None`` when the source
    formula has no parseable elements - such rows carry no usable annotation
    key and are dropped at the ingestion boundary.

    :param record: Adapter-emitted record carrying a raw source formula.
    :return: Finalized record, or ``None`` if the formula is unusable.
    """
    canonical = canonical_formula(record.formula)
    if canonical is None:
        return None
    computed = monoisotopic_mass(canonical)
    return record.model_copy(
        update={
            "formula": canonical,
            # Fall back to any source-provided mass only if we cannot compute one.
            "monoisotopic_mass": computed
            if computed is not None
            else record.monoisotopic_mass,
        }
    )
