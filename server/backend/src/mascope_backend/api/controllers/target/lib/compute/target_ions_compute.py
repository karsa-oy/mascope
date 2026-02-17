"""
Functions for target ions and target isotopes generation.
"""

import re
from itertools import combinations_with_replacement, product as cartesian_product
from math import comb

import numpy as np
from IsoSpecPy import IsoThreshold

from mascope_backend.api.models.target.compounds.target_compound_pydantic_model import (
    TargetCompoundBase,
)
from mascope_backend.db import (
    IonizationMechanism,
    TargetIon,
    TargetIsotope,
)
from mascope_backend.db.id import gen_id
from mascope_backend.runtime import runtime
from mascope_molmass import Formula
from mascope_molmass.elements import ELECTRON, ELEMENTS
from mascope_tools.composition.utils import normalize_formula_with_isotopes
from mascope_tools.composition.heuristic_filter import extract_isotope_labels
from mascope_tools.composition.finder import replace_atom_with_isotope

# Threshold for high resolution isotope peaks prediction
# We store "all" isotopes in the database, filter by abundance later if needed
ISOTOPE_ABUNDANCE_THRESHOLD = 0.00001  # 0.001 %
# Low/TOF resolution constant
RESOLUTION_LOW = 1e4


class SkipIonizationMechanism(Exception):
    """Exception to skip an ionization mechanism when generating target ions."""

    pass


class UnknownIonizationMechanism(Exception):
    """Exception for unknown ionization mechanisms."""

    pass


class UnknownCustomElement(Exception):
    """Exception for unknown custom elements in formulas."""

    pass


def charge_string(raw_ion: Formula) -> str:
    """Get charge string (+/-) based on ion formula

    :param raw_ion: Formula instance of the ion
    :type raw_ion: Formula
    :return: Charge string, either + or -
    :rtype: str

    Examples
    --------
    >>> from mascope_molmass import Formula
    >>> charge_string(Formula("H+"))
    '+'
    >>> charge_string(Formula("Cl-"))
    '-'
    >>> charge_string(Formula("H2O"))
    ''
    """
    charge_str = ""
    if raw_ion.charge == -1:
        charge_str = "-"
    elif raw_ion.charge == +1:
        charge_str = "+"
    else:
        charge_str = ""
    return charge_str


def generate_target_ions_from_composition(
    target_compound: TargetCompoundBase,
    ionization_mechanisms: list[IonizationMechanism],
) -> tuple[list[TargetIon], list[TargetIsotope]]:
    """Generate target ions and isotopes based on target compound composition and given ionization mechanisms

    Leverages mascope_molmass.Formula to compute ion formulas (compound formula + ionization mechanism),
    potentially including custom elements (e.g. ^N). Predicts isotopic patterns using IsoSpecPy.

    :param target_compound: Target compound to use as a base for the ions
    :type target_compound: TargetCompoundBase
    :param ionization_mechanisms: List of ionization mechanisms to apply to the target compound
    :type ionization_mechanisms: list[IonizationMechanism]
    :return: 2-tuple of (list of ions (instances of TargetIon), list of isotopes (instances of TargetIsotope))
    :rtype: tuple
    """
    target_ions = []
    target_isotopes = []

    # generate and create ion records
    target_compound_formula = target_compound.target_compound_formula.rstrip()
    for ionization_mechanism in ionization_mechanisms:
        mechanism = ionization_mechanism.ionization_mechanism

        try:
            compound_formula = _get_compound_formula(target_compound_formula, mechanism)
            raw_ion = _get_raw_ion(mechanism, compound_formula)
        except (SkipIonizationMechanism, ValueError) as e:
            runtime.logger.debug(
                f"Skipping ionization mechanism {mechanism} for compound {target_compound_formula}: {e}"
            )
            continue
        except UnknownIonizationMechanism as e:
            runtime.logger.warning(
                f"Failed to parse ion formula for compound {target_compound_formula} "
                f"and mechanism {mechanism}: {e}"
            )
            # Try to create ions with other mechanisms
            continue

        # Strip brackets [] and charge from formula
        ion_formula = raw_ion._formula_nocharge  # pylint: disable=protected-access
        # Remove potential explicit isotopes in the formula
        ion_formula = Formula(normalize_formula_with_isotopes(ion_formula)).formula

        # construct and save ion row
        runtime.logger.debug(
            f"Generated ion formula {raw_ion.formula} for compound {compound_formula} with mechanism {mechanism}"
        )
        ion = TargetIon(
            target_ion_id=gen_id(16),
            target_compound_id=target_compound.target_compound_id,
            ionization_mechanism_id=ionization_mechanism.ionization_mechanism_id,
            target_ion_formula=ion_formula + charge_string(raw_ion),
            filter_params={},
        )
        target_ions.append(ion)

        predicted_isotopes = dict()
        # Predict high resolution isotopes
        predicted_isotopes["HIGH"] = predict_isotopes(raw_ion, ion_formula)
        # Group for low resolution
        predicted_isotopes["LOW"] = group_target_isotopes(
            *predicted_isotopes["HIGH"], RESOLUTION_LOW
        )
        # Store target isotopes
        for resolution, (masses, probs, formulae) in predicted_isotopes.items():
            target_isotopes.extend(
                [
                    TargetIsotope(
                        target_isotope_id=gen_id(16),
                        target_ion_id=ion.target_ion_id,
                        mz=mz,
                        relative_abundance=rel_abu,
                        resolution=resolution,
                        target_isotope_formula=form,
                    )
                    for mz, rel_abu, form in zip(masses, probs, formulae)
                ]
            )

    return target_ions, target_isotopes


def _get_compound_formula(
    target_compound_formula: str, ionization_mechanism: str
) -> Formula | None:
    """Get compound formula as Formula instance, handling special cases.

    :param target_compound_formula: Target compound formula string
    :type target_compound_formula: str
    :param ionization_mechanism: Ionization mechanism string
    :type ionization_mechanism: str
    :raises SkipIonizationMechanism: If the ionization mechanism cannot be applied:
        - Electron transfer on empty formula
        - Abstraction from empty formula
    :return: Compound formula as Formula instance, or None for empty formula "()"
    :rtype: Formula | None
    """
    runtime.logger.debug(
        f"Processing compound formula '{target_compound_formula}' with ionization mechanism '{ionization_mechanism}'"
    )
    # Handle the special case when generating ions for empty formula "()"
    if target_compound_formula == "()":
        compound_formula = None
        if ionization_mechanism == "-" or ionization_mechanism == "+":
            # Electron transfer does not apply
            raise SkipIonizationMechanism(
                "Electron transfer does not apply to empty formula"
            )
        if ionization_mechanism.startswith("-"):
            # Cannot subtract from empty formula
            raise SkipIonizationMechanism(
                "Subtraction mechanisms do not apply to empty formula"
            )
    elif ionization_mechanism.startswith("-"):
        # For subtraction mechanisms, ensure the compound formula can support it
        compound_formula = Formula(target_compound_formula)
        mechanism_formula = Formula(ionization_mechanism[1:])
        for (
            element,
            iso_counts,
        ) in mechanism_formula._elements.items():  # pylint: disable=protected-access
            # Check if element to be subtracted exists in compound formula
            if (
                element
                not in compound_formula._elements  # pylint: disable=protected-access
            ):
                raise SkipIonizationMechanism(
                    f"Element {element} from mechanism formula {mechanism_formula.formula} "
                    f"not in compound formula {compound_formula.formula}"
                )
            # Check if there are enough atoms of the element to be subtracted
            mech_count = sum(iso_counts.values())
            compound_count = sum(
                compound_formula._elements[  # pylint: disable=protected-access
                    element
                ].values()
            )
            if mech_count > compound_count:
                raise SkipIonizationMechanism(
                    f"Cannot subtract {mech_count} of element {element} from compound formula "
                    f"{compound_formula.formula}"
                )
    else:
        compound_formula = Formula(target_compound_formula)

    return compound_formula


def _get_raw_ion(ionization_mechanism: str, compound_formula: Formula) -> Formula:
    """Get raw ion Formula based on ionization mechanism and compound formula.
    Leverage molmass.Formula addition and subtraction operators

    :param ionization_mechanism: Ionization mechanism string
    :type ionization_mechanism: str
    :param compound_formula: Compound formula as Formula instance
    :type compound_formula: Formula
    :raises UnknownIonizationMechanism: If the ionization mechanism is unknown.
    :return: Raw ion as Formula instance
    :rtype: Formula
    """
    if len(ionization_mechanism) > 1:
        # Parse mechanism into Formula, excluding the operation sign (+/-)
        mechanism_formula = Formula(ionization_mechanism[1:])
        operation = ionization_mechanism[0]
    else:
        # For electron transfer, the entire mechanism (+/-) is used
        mechanism_formula = Formula(ionization_mechanism)
        # Electron is added for "-" and subtracted for "+"
        operation = "+"

    if operation == "+":
        # Addition mechanism
        if compound_formula is None:
            # Special case: empty formula "()"
            raw_ion = mechanism_formula
        else:
            raw_ion = compound_formula + mechanism_formula
    elif operation == "-":
        # Subtraction mechanism
        raw_ion = compound_formula - mechanism_formula
    else:
        raise UnknownIonizationMechanism(ionization_mechanism)

    return raw_ion


def predict_isotopes(
    raw_ion: Formula, ion_formula: str
) -> tuple[list[float], list[float], list[str]]:
    """Predicts isotope masses and abundances for a given ion formula using IsoSpecPy.

    Handles custom elements (e.g., ^N for isotopically labelled nitrogen) by:
    1. Computing isotope pattern for the non-custom part using IsoSpecPy
    2. Multiplying with custom element isotope distributions

    :param raw_ion: Formula instance of the ion
    :type raw_ion: Formula
    :param ion_formula: Ion formula string
    :type ion_formula: str
    :raises UnknownCustomElement: If a custom element is unknown.
    :return: 3-tuple lists of (m/z values, relative abundances, isotope formulae)
    :rtype: tuple[list[float], list[float], list[str]]
    """
    custom_elements = _extract_custom_elements(raw_ion, ion_formula)
    base_formula = _remove_custom_elements_from_formula(ion_formula, custom_elements)

    # Compute isotope pattern for the base (non-custom) part
    base_masses, base_probs, base_labels = _compute_base_isotope_pattern(base_formula)

    # Combine with custom element isotope patterns if present
    if custom_elements:
        masses, probs, formulae = _combine_with_custom_elements(
            base_formula, base_masses, base_probs, base_labels, custom_elements
        )
    else:
        masses = base_masses
        probs = base_probs
        formulae = [
            replace_atom_with_isotope(base_formula, label) for label in base_labels
        ]

    # Correct masses for electron charge and add charge string to formulae
    charge = raw_ion.charge
    masses = [(m - ELECTRON.mass * charge) / abs(charge) for m in masses]
    charge_str = charge_string(raw_ion)
    formulae = [f + charge_str for f in formulae]

    return masses, probs, formulae


def _extract_custom_elements(raw_ion: Formula, ion_formula: str) -> dict[str, dict]:
    """Extract custom element data from a formula.

    :param raw_ion: Formula instance containing element data
    :param ion_formula: Ion formula string to check for custom elements
    :return: Dict mapping custom element symbols to their properties
    :raises UnknownCustomElement: If a custom element is not in ELEMENTS
    """
    custom_elements = {}

    if "^" not in ion_formula:
        return custom_elements

    elements = raw_ion._elements  # pylint: disable=protected-access
    for symbol in elements:
        if not symbol.startswith("^"):
            continue

        try:
            element = ELEMENTS[symbol]
        except KeyError as e:
            raise UnknownCustomElement(symbol) from e

        isotope_keys = list(element.isotopes.keys())
        custom_elements[symbol] = {
            "count": elements[symbol][0],
            "regular_symbol": symbol[1:],  # Remove ^ prefix
            "lightest_mass_number": isotope_keys[0],
            "isotopes": [
                {
                    "mass": iso.mz,
                    "abundance": iso.abundance,
                    "mass_number": iso.massnumber,
                }
                for iso in element.isotopes.values()
            ],
        }

    return custom_elements


def _remove_custom_elements_from_formula(
    ion_formula: str, custom_elements: dict[str, dict]
) -> str:
    """Remove custom elements from formula string for IsoSpecPy calculation.

    Examples
    --------
    >>> _remove_custom_elements_from_formula("HN^NO6", {"^N": {}})
    'HNO6'
    >>> _remove_custom_elements_from_formula("[18O]C2H4^N", {"^N": {}})
    'C2H4[18O]'
    >>> _remove_custom_elements_from_formula("C6H12O6", {})
    'C6H12O6'
    >>> _remove_custom_elements_from_formula("", {})
    ''

    :param ion_formula: Original ion formula string
    :param custom_elements: Dict of custom element data
    :return: Formula string with custom elements removed, normalized
    """
    result = ion_formula
    for symbol in custom_elements:
        pattern = rf"{re.escape(symbol)}\d*"
        result = re.sub(pattern, "", result)

    if result:
        result = Formula(result).formula

    return result


def _compute_base_isotope_pattern(
    formula: str,
) -> tuple[list[float], list[float], list[str]]:
    """Compute isotope pattern for a formula using IsoSpecPy.

    :param formula: Chemical formula string (without custom elements)
    :return: 3-tuple of (masses, probabilities, isotope labels)
    """
    if not formula:
        # Empty formula (e.g., just custom elements with nothing else)
        return [0.0], [1.0], [""]

    predicted_peaks = IsoThreshold(
        formula=formula,
        threshold=ISOTOPE_ABUNDANCE_THRESHOLD,
        get_confs=True,
    )

    masses = [float(m) for m in predicted_peaks.masses]
    probs = [float(p) for p in predicted_peaks.probs]
    labels = extract_isotope_labels(formula, predicted_peaks)

    return masses, probs, labels


def _combine_with_custom_elements(
    base_formula: str,
    base_masses: list[float],
    base_probs: list[float],
    base_labels: list[str],
    custom_elements: dict[str, dict],
) -> tuple[list[float], list[float], list[str]]:
    """Multiply base isotope pattern with custom element isotope distributions.

    For custom elements with multiple atoms (e.g., ^N2), enumerates all isotope
    combinations following multinomial distribution. For multiple custom elements
    (e.g., ^H and ^N), computes the Cartesian product of their combinations.

    Duplicate formulas (from different isotope paths yielding same composition)
    are merged by summing probabilities.

    :param base_formula: Formula string for the base (non-custom) part
    :param base_masses: Base isotope masses
    :param base_probs: Base isotope probabilities
    :param base_labels: Base isotope labels (e.g., "M0", "17O")
    :param custom_elements: Dict of custom element data
    :return: 3-tuple of combined (masses, probabilities, formulae)
    """
    # Generate isotope combinations for each custom element
    custom_combinations = [
        _generate_isotope_combinations(custom_data)
        for custom_data in custom_elements.values()
    ]

    # Compute Cartesian product of all custom element combinations
    all_custom_combos = list(cartesian_product(*custom_combinations))

    # Use dict to merge duplicate formulas
    # Key: normalized formula, Value: (mass, accumulated_prob)
    formula_data: dict[str, tuple[float, float]] = {}

    for base_mass, base_prob, base_label in zip(base_masses, base_probs, base_labels):
        # Convert label to proper formula (e.g., "M0" -> "O3", "17O" -> "[17O]O2")
        base_isotope_formula = (
            replace_atom_with_isotope(base_formula, base_label) if base_formula else ""
        )

        for custom_combo in all_custom_combos:
            # Multiply all custom element contributions
            total_mass = base_mass + sum(c[0] for c in custom_combo)
            total_prob = base_prob
            for c in custom_combo:
                total_prob *= c[1]

            if total_prob < ISOTOPE_ABUNDANCE_THRESHOLD:
                continue

            # Concatenate custom element formulae
            custom_formula = "".join(c[2] for c in custom_combo)

            # Combine and normalize using Formula to merge elements (e.g. NN -> N2)
            # Then reorder to put isotope labels at the front
            raw_combined = custom_formula + base_isotope_formula
            normalized = _reorder_isotopes_first(
                Formula(raw_combined).formula if raw_combined else ""
            )

            # Merge duplicates by summing probabilities
            if normalized in formula_data:
                existing_mass, existing_prob = formula_data[normalized]
                # Use probability-weighted average mass (masses should be nearly identical)
                new_prob = existing_prob + total_prob
                new_mass = (
                    existing_mass * existing_prob + total_mass * total_prob
                ) / new_prob
                formula_data[normalized] = (new_mass, new_prob)
            else:
                formula_data[normalized] = (total_mass, total_prob)

    # Convert back to lists
    combined_formulae = list(formula_data.keys())
    combined_masses = [formula_data[f][0] for f in combined_formulae]
    combined_probs = [formula_data[f][1] for f in combined_formulae]

    return combined_masses, combined_probs, combined_formulae


def _reorder_isotopes_first(formula: str) -> str:
    """Reorder formula to put isotope labels (e.g., [15N], [18O]) at the beginning.

    :param formula: Chemical formula string
    :return: Formula with isotope labels moved to the front

    Examples
    --------
    >>> _reorder_isotopes_first("HN[15N]O6")
    '[15N]HNO6'
    >>> _reorder_isotopes_first("[18O]C2H4[15N]")
    '[18O][15N]C2H4'
    >>> _reorder_isotopes_first("C6H12O6")
    'C6H12O6'
    >>> _reorder_isotopes_first("")
    ''
    """
    if not formula or "[" not in formula:
        return formula

    # Extract all isotope labels like [15N], [18O], [2H], [15N]2, etc.
    isotope_pattern = r"\[\d+[A-Za-z]+\]\d*"
    isotopes = re.findall(isotope_pattern, formula)
    remaining = re.sub(isotope_pattern, "", formula)

    return "".join(isotopes) + remaining


def _generate_isotope_combinations(
    custom_data: dict,
) -> list[tuple[float, float, str]]:
    """Generate all isotope combinations for a custom element.

    For n atoms with k isotopes, generates all distributions following
    multinomial probability. E.g., ^N2 with 2% 14N / 98% 15N yields:
    - N2: 0.02**2 = 0.04%
    - [15N]N: 2 * 0.02 * 0.98 = 3.92%
    - [15N]2: 0.98**2 = 96.04%

    :param custom_data: Dict with 'count', 'regular_symbol', 'lightest_mass_number', 'isotopes'
    :return: List of (mass, probability, formula) tuples

    Examples
    --------
    Single atom with two isotopes (like ^N with 2% 14N / 98% 15N):

    >>> data = {
    ...     "count": 1,
    ...     "regular_symbol": "N",
    ...     "lightest_mass_number": 14,
    ...     "isotopes": [
    ...         {"mass": 14.003, "abundance": 0.02, "mass_number": 14},
    ...         {"mass": 15.000, "abundance": 0.98, "mass_number": 15},
    ...     ],
    ... }
    >>> result = _generate_isotope_combinations(data)
    >>> len(result)
    2
    >>> result[0]  # Light isotope (14N)
    (14.003, 0.02, 'N')
    >>> result[1]  # Heavy isotope (15N)
    (15.0, 0.98, '[15N]')

    Two atoms - multinomial distribution (^N2):

    >>> data2 = {
    ...     "count": 2,
    ...     "regular_symbol": "N",
    ...     "lightest_mass_number": 14,
    ...     "isotopes": [
    ...         {"mass": 14.003, "abundance": 0.02, "mass_number": 14},
    ...         {"mass": 15.000, "abundance": 0.98, "mass_number": 15},
    ...     ],
    ... }
    >>> result2 = _generate_isotope_combinations(data2)
    >>> len(result2)  # N2, [15N]N, [15N]2
    3
    >>> result2[0]  # N2: 0.02^2 = 0.0004
    (28.006, 0.0004, 'N2')
    >>> result2[1][1]  # [15N]N: 2 * 0.02 * 0.98 = 0.0392
    0.0392
    >>> result2[1][2]  # Formula shows heavy isotope first
    '[15N]N'
    >>> result2[2][0], round(result2[2][1], 4), result2[2][2]  # [15N]2: 0.98^2 = 0.9604
    (30.0, 0.9604, '[15N]2')
    """
    count = custom_data["count"]
    symbol = custom_data["regular_symbol"]
    isotopes = custom_data["isotopes"]
    lightest = custom_data["lightest_mass_number"]

    results = []
    for combo in combinations_with_replacement(range(len(isotopes)), count):
        # Count occurrences of each isotope index
        counts_per_isotope = {i: combo.count(i) for i in set(combo)}

        # Mass = sum of (isotope_mass × count)
        mass = sum(isotopes[i]["mass"] * c for i, c in counts_per_isotope.items())

        # Probability = multinomial_coeff × product(abundance^count)
        prob = _multinomial_coeff(count, list(counts_per_isotope.values()))
        for i, c in counts_per_isotope.items():
            prob *= isotopes[i]["abundance"] ** c

        # Build formula: heavy isotopes first (descending mass), then light
        formula_parts = []
        for i, c in sorted(
            counts_per_isotope.items(),
            key=lambda x: isotopes[x[0]]["mass_number"],
            reverse=True,
        ):
            if c == 0:
                continue
            mass_num = isotopes[i]["mass_number"]
            count_str = str(c) if c > 1 else ""
            if mass_num == lightest:
                formula_parts.append(f"{symbol}{count_str}")
            else:
                formula_parts.append(f"[{mass_num}{symbol}]{count_str}")

        results.append((mass, prob, "".join(formula_parts)))

    return results


def _multinomial_coeff(n: int, counts: list[int]) -> int:
    """Calculate multinomial coefficient n! / (k1! * k2! * ...).

    Examples
    --------
    >>> _multinomial_coeff(4, [2, 2])  # 4! / (2! * 2!) = 6
    6
    >>> _multinomial_coeff(3, [1, 1, 1])  # 3! / (1! * 1! * 1!) = 6
    6
    >>> _multinomial_coeff(5, [3, 2])  # 5! / (3! * 2!) = 10
    10
    """
    result = 1
    remaining = n
    for k in counts:
        result *= comb(remaining, k)
        remaining -= k
    return result


def generate_target_ions_from_mass(
    target_compound_mass: float,
    target_compound: TargetCompoundBase,
    ionization_mechanisms: list[IonizationMechanism],
) -> tuple[list[TargetIon], list[TargetIsotope]]:
    """TODO: deprecate this function in favor of composition-based generation

    Generate target ions and isotopes based on target compound mass and given
    ionization mechanisms

    :param target_compound_mass: Mass of the target compound (composition not known)
    :type target_compound_mass: float
    :param target_compound: Target compound to use as a base for the ions
    :type target_compound: TargetCompoundBase
    :param ionization_mechanisms: List of ionization mechanisms to apply to the target compound
    :type ionization_mechanisms: list[IonizationMechanism]
    :return: 2-tuple of (
        list of ions (instances of TargetIon),
        list of isotopes (instances of TargetIsotope)
        )
    :rtype: tuple
    """
    target_ions = []
    target_isotopes = []

    # generate ion and isotope records
    for ionization_mechanism in ionization_mechanisms:
        mechanism = ionization_mechanism.ionization_mechanism
        polarity = ionization_mechanism.ionization_mechanism_polarity
        # construct ion
        ion = TargetIon(
            target_ion_id=gen_id(16),
            target_compound_id=target_compound.target_compound_id,
            ionization_mechanism_id=ionization_mechanism.ionization_mechanism_id,
            target_ion_formula=(f"{target_compound_mass:.4f}" + mechanism),
            filter_params={},
        )
        target_ions.append(ion)

        # construct isotopes
        if len(mechanism) > 1:
            # Addition or abstraction mechanism
            # Calculate isotopic pattern of the ionization mechanism
            raw_ion = Formula("(" + mechanism[1:-1] + ")" + polarity)
            is_adduct = mechanism[0] == "+"
            if is_adduct:
                # Addition mechanism
                raw_isotopes = [
                    (isotope.mz, isotope.fraction)
                    for isotope in raw_ion.spectrum().values()
                ]
            else:
                # Abstraction mechanism, no knowledge of the isotopic pattern
                raw_isotopes = [
                    (-raw_ion.mz, 1.0)  # pylint: disable=invalid-unary-operand-type
                ]
        else:
            # Special case: electron transfer
            is_addition = mechanism[0] == "-"
            me = 0.00054858  # mass of an electron [Da]
            raw_isotopes = [(me if is_addition else -me, 1.0)]
        # Store high resolution isotopes
        target_isotopes.extend(
            [
                TargetIsotope(
                    target_isotope_id=gen_id(16),
                    target_ion_id=ion.target_ion_id,
                    mz=(target_compound_mass + mz),
                    relative_abundance=fraction,
                    resolution="HIGH",
                    # Use the ion formula as placeholder
                    target_isotope_formula=ion.target_ion_formula,
                )
                for mz, fraction in raw_isotopes
            ]
        )
        # Store low resolution isotopes
        target_isotopes.extend(
            [
                TargetIsotope(
                    target_isotope_id=gen_id(16),
                    target_ion_id=ion.target_ion_id,
                    mz=(target_compound_mass + reagent_mz),
                    relative_abundance=reagent_rel_abu,
                    resolution="LOW",
                    # Use the ion formula as placeholder
                    target_isotope_formula=ion.target_ion_formula,
                )
                for reagent_mz, reagent_rel_abu in raw_isotopes
            ]
        )

    return target_ions, target_isotopes


def group_target_isotopes(
    masses: list, probs: list, formulae: list, resolution: float
) -> tuple[list, list, list]:
    """
    Group target isotope m/z, relative abundance (probs), and isotope formulae
    to produce lower resolution isotopes.

    The width of the group/bin is defined as dmz = FWHM / 2 = m/z / resolution / 2.

    The isotope formulae are concatenated with "/" separator for all isotopes
    that fall within the same bin.

    :param masses: High resolution target isotope m/z
    :type masses: list
    :param probs: High resolution target isotope relative abundance
    :type probs: list
    :param formulae: High resolution target isotope formulae
    :type formulae: list
    :param resolution: Resolution value
    :type resolution: float
    :return: Tuple with lists of grouped "mz", "relative_abundance",
            "target_isotope_formula" values
    :rtype: tuple[list, list, list]
    """
    # Convert to numpy arrays to simplify computations
    mz = np.array(masses)
    intensity = np.array(probs)
    formula = np.array(formulae)

    # Sort by m/z to ensure proper binning
    sorted_indices = np.argsort(mz)
    mz = mz[sorted_indices]
    intensity = intensity[sorted_indices]
    formula = formula[sorted_indices]

    mz_grouped = []
    intensity_grouped = []
    formula_grouped = []
    i = 0
    while i < mz.size:
        # Calculate bin width for the current m/z
        dmz = mz[i] / resolution / 2

        # Determine bin size
        bin_mask = (mz >= mz[i]) & (mz < mz[i] + dmz)

        # Extract values within the current bin
        mz_bin = mz[bin_mask]
        intensity_bin = intensity[bin_mask]
        formula_bin = formula[bin_mask]

        # Final isotope intensity
        intensity_total = np.sum(intensity_bin)

        # Calculate center of mass for mz in the bin
        if intensity_total > 0:
            mz_bin_center = np.sum(mz_bin * intensity_bin) / intensity_total
        else:
            mz_bin_center = np.mean(mz_bin)

        # Store grouped values
        mz_grouped.append(mz_bin_center)
        intensity_grouped.append(intensity_total)
        formula_grouped.append("/".join(formula_bin.tolist()))

        # Move to the next bin, skipping all processed values
        i += np.sum(bin_mask)

    return mz_grouped, intensity_grouped, formula_grouped
