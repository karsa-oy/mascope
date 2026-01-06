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


# Threshold for high resolution isotope peaks prediction, r.a.>1%
ISOTOPE_ABUNDANCE_THRESHOLD = 0.01
# Low/TOF resolution constant
RESOLUTION_LOW = 1e4


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
        # Handle the special case when generating ions for empty formula "()"
        if target_compound_formula == "()":
            compound_formula = None
            if mechanism == "-" or mechanism == "+":
                # Electron transfer does not apply
                continue
            if mechanism.startswith("-"):
                # Cannot abstract from empty formula
                continue
        else:
            compound_formula = Formula(target_compound_formula)

        # Parse mechanism into Formula, excluding the operation sign (+/-)
        # For electron transfer, the entire mechanism (+/-) is used
        mechanism_formula = (
            Formula(mechanism[1:]) if len(mechanism) > 1 else Formula(mechanism)
        )

        try:
            # Construct raw ion formula based on the compound formula and ionization mechanism
            # Leverage molmass.Formula addition and subtraction operators
            operation = mechanism[0]
            if operation == "+":
                # Addition mechanism
                if compound_formula is None:
                    # Special case: empty formula "()"
                    raw_ion = mechanism_formula
                else:
                    raw_ion = compound_formula + mechanism_formula
            elif operation == "-":
                # Abstraction mechanism
                raw_ion = compound_formula - mechanism_formula
            else:
                raise ValueError(f"Unknown ionization mechanism: {mechanism}")
        except ValueError as e:
            # Failed to create a target ion for the combination of target compound
            # and ionization mechanism
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

        custom_elements = []
        if "^" in ion_formula:
            # Find custom element properties
            elements = raw_ion._elements  # pylint: disable=protected-access
            for symbol in elements:
                if symbol.startswith("^"):
                    try:
                        element = ELEMENTS[symbol]
                    except KeyError as e:
                        raise ValueError(f"Unknown custom element: {symbol}") from e
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

        # Predict peaks of high resolution isotopes
        if len(custom_elements) > 0:
            predicted_peaks = IsoThreshold(
                formula=ion_formula,
                threshold=ISOTOPE_ABUNDANCE_THRESHOLD,
                atomCounts=isotope_counts,  # pylint: disable=possibly-used-before-assignment
                isotopeMasses=[
                    isotope_masses  # pylint: disable=possibly-used-before-assignment
                ],
                isotopeProbabilities=[
                    isotope_abundances  # pylint: disable=possibly-used-before-assignment
                ],
            )
        else:
            predicted_peaks = IsoThreshold(
                formula=ion_formula, threshold=ISOTOPE_ABUNDANCE_THRESHOLD
            )
        # Extract high resolution masses and probabilities, correct masses for the electron charge
        masses_high_res = [
            (float(m) - ELECTRON.mass * raw_ion.charge) / abs(raw_ion.charge)
            for m in predicted_peaks.masses
        ]
        probs_high_res = [float(p) for p in predicted_peaks.probs]

        # Calculate low resolution isotope peaks
        masses_low_res, probs_low_res = group_target_isotopes(
            masses_high_res, probs_high_res, RESOLUTION_LOW
        )

        # Store high resolution isotopes
        target_isotopes.extend(
            [
                TargetIsotope(
                    target_isotope_id=gen_id(16),
                    target_ion_id=ion.target_ion_id,
                    mz=mz,
                    relative_abundance=rel_abu,
                    resolution="HIGH",
                )
                for mz, rel_abu in zip(masses_high_res, probs_high_res)
            ]
        )
        # Store low resolution isotopes
        target_isotopes.extend(
            [
                TargetIsotope(
                    target_isotope_id=gen_id(16),
                    target_ion_id=ion.target_ion_id,
                    mz=mz,
                    relative_abundance=rel_abu,
                    resolution="LOW",
                )
                for mz, rel_abu in zip(masses_low_res, probs_low_res)
            ]
        )

    return target_ions, target_isotopes


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
    masses: list, probs: list, resolution: float
) -> tuple[list, list]:
    """
    Group target isotope m/z and relative abundance (probs) to produce lower resolution isotopes.

    The width of the group/bin is defined as dmz = FWHM / 2 = m/z / resolution / 2.

    :param masses: High resolution target isotope m/z
    :type masses: list
    :param probs: High resolution target isotope relative abundance
    :type probs: list
    :param resolution: Resolution value
    :type resolution: float
    :return: Tuple with lists of grouped "mz", "relative_abundance" values
    :rtype: tuple[list, list]
    """
    # Convert to numpy arrays to simplify computations
    mz = np.array(masses)
    intensity = np.array(probs)

    # Sort by m/z to ensure proper binning
    sorted_indices = np.argsort(mz)
    mz = mz[sorted_indices]
    intensity = intensity[sorted_indices]

    # Init grouped m/z and intensity lists
    mz_grouped = []
    intensity_grouped = []

    i = 0
    while i < mz.size:
        # Calculate bin width for the current m/z
        dmz = mz[i] / resolution / 2

        # Determine bin size
        bin_mask = (mz >= mz[i]) & (mz < mz[i] + dmz)

        # Extract values within the current bin
        mz_bin = mz[bin_mask]
        intensity_bin = intensity[bin_mask]

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

        # Move to the next bin, skipping all processed values
        i += np.sum(bin_mask)

    return mz_grouped, intensity_grouped
