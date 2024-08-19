""" 
Functions for target ions and target isotopes generation.
"""

from typing import List
from mascope_lib.molmass import Formula
from mascope_server.db.id import gen_id
from mascope_server.db.models import (
    IonizationMechanism,
    TargetIon,
    TargetIsotope,
)
from mascope_server.api.models.target.compounds.target_compound_pydantic_model import (
    TargetCompoundBase,
)
import mascope_runtime as runtime

logger = runtime.logger.service("backend")


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
            logger.warning(
                "Failed to parse ion formula for compound %s and mechanism %s: %s",
                target_compound_formula,
                mechanism,
                e,
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

            # construct and save isotope rows
            raw_isotopes = raw_ion.mz_spectrum().values()
            target_isotopes.extend(
                [
                    TargetIsotope(
                        target_isotope_id=gen_id(16),
                        target_ion_id=ion.target_ion_id,
                        mz=mz,
                        relative_abundance=rel_abu,
                    )
                    for mz, rel_abu in raw_isotopes
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

    # generate and create ion records
    for ionization_mechanism in ionization_mechanisms:
        mechanism = ionization_mechanism.ionization_mechanism
        # construct and save ion row
        ion = TargetIon(
            target_ion_id=gen_id(16),
            target_compound_id=target_compound.target_compound_id,
            ionization_mechanism_id=ionization_mechanism.ionization_mechanism_id,
            target_ion_formula=(f"{target_compound_mass:.4f}" + mechanism),
            filter_params={},
        )

        target_ions.append(ion)
        # construct and save isotope rows
        raw_ion = Formula("(" + mechanism[1:-1] + ")" + mechanism[-1])
        is_adduct = mechanism[0] == "+"
        if is_adduct:
            raw_isotopes = raw_ion.mz_spectrum().values()
        else:
            raw_isotopes = [
                (-raw_ion.mz, 1.0)  # pylint: disable=invalid-unary-operand-type
            ]

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
