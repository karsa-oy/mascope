"""
Functions for target ions and target isotopes generation.
"""

import re

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
            counts,
        ) in mechanism_formula._elements.items():  # pylint: disable=protected-access
            if (
                element
                not in compound_formula._elements  # pylint: disable=protected-access
            ):
                raise SkipIonizationMechanism(
                    f"Element {element} from mechanism formula {mechanism_formula.formula} "
                    f"not in compound formula {compound_formula.formula}"
                )
            count = counts[0]
            if (
                compound_formula._elements[element][  # pylint: disable=protected-access
                    0
                ]
                < count
            ):
                raise SkipIonizationMechanism(
                    f"Cannot subtract {count} of element {element} from compound formula "
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
    raw_ion is used to extract custom element isotopic patterns if needed.

    :param raw_ion: Formula instance of the ion
    :type raw_ion: Formula
    :param ion_formula: Ion formula string
    :type ion_formula: str
    :raises ValueError: If a custom element is unknown.
    :return: 3-tuple lists of
        (m/z values, relative abundances, isotope formulae)
    :rtype: tuple[list[float], list[float], list[str]]
    """
    custom_elements = []
    if "^" in ion_formula:
        # Find custom element properties
        elements = raw_ion._elements  # pylint: disable=protected-access
        for symbol in elements:
            if symbol.startswith("^"):
                try:
                    element = ELEMENTS[symbol]
                except KeyError as e:
                    raise UnknownCustomElement(symbol) from e
                custom_elements.append(symbol)
                isotope_masses = [iso.mz for iso in element.isotopes.values()]
                isotope_abundances = [
                    iso.abundance for iso in element.isotopes.values()
                ]
                isotope_counts = [
                    raw_ion._elements[symbol][0]  # pylint: disable=protected-access
                ]
                # Remove custom element notation for isotope prediction
                pattern = rf"{re.escape(symbol)}\d*"
                ion_formula = re.sub(pattern, "", ion_formula)
                # Parse the ion formula again without custom elements
                ion_formula = Formula(ion_formula).formula

    iso_params = {
        "formula": ion_formula,
        "threshold": ISOTOPE_ABUNDANCE_THRESHOLD,
        "get_confs": True,
    }
    if len(custom_elements) > 0:
        # Use custom isotope abundances and masses for custom elements
        iso_params["atomCounts"] = (
            isotope_counts  # pylint: disable=possibly-used-before-assignment
        )
        iso_params["isotopeMasses"] = [isotope_masses]
        iso_params["isotopeProbabilities"] = [
            isotope_abundances  # pylint: disable=possibly-used-before-assignment
        ]

    predicted_peaks = IsoThreshold(**iso_params)
    # Masses are corrected for the electron charge
    masses_high_res = [
        (float(m) - ELECTRON.mass * raw_ion.charge) / abs(raw_ion.charge)
        for m in predicted_peaks.masses
    ]
    # Probabilities are basically relative abundances
    probs_high_res = [float(p) for p in predicted_peaks.probs]
    # Build isotope formulae
    isotope_labels = extract_isotope_labels(ion_formula, predicted_peaks)
    charge = charge_string(raw_ion)
    isotope_formulae = [
        replace_atom_with_isotope(ion_formula, label) + charge
        for label in isotope_labels
    ]

    return masses_high_res, probs_high_res, isotope_formulae


def generate_target_ions_from_mass(
    target_compound_mass: float,
    target_compound: TargetCompoundBase,
    ionization_mechanisms: list[IonizationMechanism],
) -> tuple[list[TargetIon], list[TargetIsotope]]:
    """Generate target ions and isotopes based on target compound mass and given
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
