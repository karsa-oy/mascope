""" 
Functions for target ions and target isotopes generation.
"""

from typing import List
import numpy as np
from IsoSpecPy import IsoThreshold
from mascope_lib.molmass import Formula
from mascope_lib.molmass.elements import ELECTRON
from mascope_server.db.id import gen_id
from mascope_server.db.models import (
    IonizationMechanism,
    TargetIon,
    TargetIsotope,
)
from mascope_server.api.models.target.compounds.target_compound_pydantic_model import (
    TargetCompoundBase,
)
from mascope_server.runtime import runtime


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
    ionization_mechanisms: List[IonizationMechanism],
) -> tuple:
    """Generate target ions and isotopes based on target compound composition and given ionization mechanisms

    :param target_compound: Target compound to use as a base for the ions
    :type target_compound: TargetCompoundBase
    :param ionization_mechanisms: List of ionization mechanisms to apply to the target compound
    :type ionization_mechanisms: List[IonizationMechanism]
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
            if mechanism == "-" or mechanism == "+":
                # Electron transfer does not apply
                continue
            if mechanism.startswith("-"):
                # Cannot abstract from empty formula
                continue
        try:
            # get and save ions
            raw_ion = Formula(
                "("
                + target_compound_formula
                + mechanism[:-1]  # remove polarity sign before parenthesis
                + ")"
                + mechanism[-1]  # add polarity sign at the end
            )
        except ValueError as e:
            # Failed to create a target ion for the combination of target compound and ionization mechanism
            runtime.logger.warning(
                f"Failed to parse ion formula for compound {target_compound_formula} and mechanism {mechanism}: {e}"
            )
            # Try to create ions with other mechanisms
            continue
        else:
            # construct and save ion row
            ion = TargetIon(
                target_ion_id=gen_id(16),
                target_compound_id=target_compound.target_compound_id,
                ionization_mechanism_id=ionization_mechanism.ionization_mechanism_id,
                target_ion_formula=raw_ion.formula + charge_string(raw_ion),
                filter_params={},
            )
            target_ions.append(ion)

            # Predict peaks of high resolution isotopes
            predicted_peaks = IsoThreshold(
                formula=raw_ion.formula, threshold=ISOTOPE_ABUNDANCE_THRESHOLD
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
    ionization_mechanisms: List[IonizationMechanism],
) -> tuple:
    """Generate target ions and isotopes based on target compound mass and given ionization mechanisms

    :param target_compound_mass: Mass of the target compound (composition not known)
    :type target_compound_mass: float
    :param target_compound: Target compound to use as a base for the ions
    :type target_compound: TargetCompoundBase
    :param ionization_mechanisms: List of ionization mechanisms to apply to the target compound
    :type ionization_mechanisms: List[IonizationMechanism]
    :return: 2-tuple of (list of ions (instances of TargetIon), list of isotopes (instances of TargetIsotope))
    :rtype: tuple
    """
    target_ions = []
    target_isotopes = []

    # generate ion and isotope records
    for ionization_mechanism in ionization_mechanisms:
        mechanism = ionization_mechanism.ionization_mechanism
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
            raw_ion = Formula("(" + mechanism[1:-1] + ")" + mechanism[-1])
            is_adduct = mechanism[0] == "+"
            if is_adduct:
                # Addition mechanism
                raw_isotopes = raw_ion.mz_spectrum().values()
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

        target_isotopes.extend(
            [
                TargetIsotope(
                    target_isotope_id=gen_id(16),
                    target_ion_id=ion.target_ion_id,
                    mz=(target_compound_mass + reagent_mz),
                    relative_abundance=reagent_rel_abu,
                )
                for reagent_mz, reagent_rel_abu in raw_isotopes
            ]
        )

    return target_ions, target_isotopes


def group_target_isotopes(masses: list, probs: list, resolution: float) -> tuple:
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
    :rtype: tuple
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
