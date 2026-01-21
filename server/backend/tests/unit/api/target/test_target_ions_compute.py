import pytest

from mascope_backend.db import (
    IonizationMechanism,
    TargetCompound,
    TargetIon,
    TargetIsotope,
)

from mascope_backend.api.controllers.target.lib.compute.target_ions_compute import (
    SkipIonizationMechanism,
    UnknownIonizationMechanism,
    _get_compound_formula,
    _get_raw_ion,
    generate_target_ions_from_composition,
    generate_target_ions_from_mass,
)

from mascope_molmass import Formula


def assert_target_ions(
    target_compound: TargetCompound,
    ionization_mechanisms: list[IonizationMechanism],
    target_ions: list[TargetIon],
) -> None:
    """Assert that target ions were created correctly for a target compound.

    :param target_compound: The target compound for which ions were generated.
    :type target_compound: TargetCompound
    :param ionization_mechanisms: List of ionization mechanisms used for generating target ions.
    :type ionization_mechanisms: list[IonizationMechanism]
    :param target_ions: List of target ions generated for the target compound.
    :type target_ions: list[TargetIon]

    :return: None
    """
    # Check that at least one ion was created for the compound
    assert any(
        ion.target_compound_id == target_compound.target_compound_id
        for ion in target_ions
    )
    # Check that each ion is for the correct target compound
    assert all(
        ion.target_compound_id == target_compound.target_compound_id
        for ion in target_ions
    )
    # Check there is a corresponding ionization mechanism for each created ion
    assert all(
        ion.ionization_mechanism_id
        in [im.ionization_mechanism_id for im in ionization_mechanisms]
        for ion in target_ions
    )
    # Check that a target ion was created for each ionization mechanism
    try:
        assert len(target_ions) == len(ionization_mechanisms)
        assert all(
            im.ionization_mechanism_id
            in [ion.ionization_mechanism_id for ion in target_ions]
            for im in ionization_mechanisms
        )
    except AssertionError:
        skipped_mechanisms = 0
        generated_im_ids = {ion.ionization_mechanism_id for ion in target_ions}
        for ionization_mechanism in ionization_mechanisms:
            if ionization_mechanism.ionization_mechanism_id in generated_im_ids:
                continue
            try:
                compound_formula = _get_compound_formula(
                    target_compound.target_compound_formula,
                    ionization_mechanism.ionization_mechanism,
                )
                _get_raw_ion(
                    ionization_mechanism.ionization_mechanism, compound_formula
                )
            except (
                SkipIonizationMechanism,
                UnknownIonizationMechanism,
                ValueError,
            ):
                skipped_mechanisms += 1
                continue
            pytest.fail(
                f"Ionization mechanism {ionization_mechanism.ionization_mechanism} should have produced an ion"
            )
        # Check that the number of target ions matches the number of ionization mechanisms minus skipped ones
        assert len(target_ions) == len(ionization_mechanisms) - skipped_mechanisms


def assert_target_ion_formulae(
    target_compound: TargetCompound,
    ionization_mechanisms: list[IonizationMechanism],
    target_ions: list[TargetIon],
) -> None:
    """Assert that target ions have the correct formulas based on the target compound and ionization mechanisms.

    :param target_compound: The target compound for which ions were generated.
    :type target_compound: TargetCompound
    :param ionization_mechanisms: List of ionization mechanisms used for generating target ions.
    :type ionization_mechanisms: list[IonizationMechanism]
    :param target_ions: List of target ions generated for the target compound.
    :type target_ions: list[TargetIon]

    :return: None
    """
    # Handle special case of null formula "()"
    if target_compound.target_compound_formula == "()":
        return
    # Check that the target ions have the correct formulas
    for ion in target_ions:
        for im in ionization_mechanisms:
            if im.ionization_mechanism_id == ion.ionization_mechanism_id:
                if im.ionization_mechanism in ["+", "-"]:
                    # For electron abstraction/addition, the formula remains unchanged
                    # Strip [] and charge from formula
                    ion_base_formula = Formula(ion.target_ion_formula)._formula_nocharge
                    assert (
                        ion_base_formula
                        == (Formula(target_compound.target_compound_formula)).formula
                    )
                    if im.ionization_mechanism == "+":
                        # Ion should have a positive charge
                        assert ion.target_ion_formula.endswith("+")
                    else:
                        # Ion should have a negative charge
                        assert ion.target_ion_formula.endswith("-")
                elif im.ionization_mechanism.startswith("+"):
                    # For adducts, the formula is modified by adding the adduct
                    assert (
                        Formula(ion.target_ion_formula).formula
                        == (
                            Formula(target_compound.target_compound_formula)
                            + Formula(im.ionization_mechanism[1:])
                        ).formula
                    )
                elif im.ionization_mechanism.startswith("-"):
                    # For abstraction, the formula is modified by removing the abstracted group
                    assert (
                        Formula(ion.target_ion_formula).formula
                        == (
                            Formula(target_compound.target_compound_formula)
                            - Formula(im.ionization_mechanism[1:])
                        ).formula
                    )


def assert_target_isotopes(
    target_ions: list[TargetIon], target_isotopes: list[TargetIsotope]
) -> None:
    """Assert that target isotopes were created correctly for the target ions.

    :param target_ions: List of target ions for which isotopes were generated.
    :type target_ions: list[TargetIon]
    :param target_isotopes: List of target isotopes generated for the target ions.
    :type target_isotopes: list[TargetIsotope]

    :return: None
    """
    ## Check each isotope has a corresponding ion
    assert all(
        isotope.target_ion_id in [ion.target_ion_id for ion in target_ions]
        for isotope in target_isotopes
    )
    ## Check each ion has corresponding isotope(s)
    assert all(
        ion.target_ion_id in [isotope.target_ion_id for isotope in target_isotopes]
        for ion in target_ions
    )


@pytest.mark.asyncio
async def test_generate_target_ions_from_composition(
    test_target_compounds_by_composition: list[TargetCompound],
    test_ionization_mechanisms: list[IonizationMechanism],
) -> None:
    """Test generating target ions from target compounds defined by composition.

    :param test_target_compounds_by_composition: List of target compounds defined by composition.
    :type test_target_compounds_by_composition: list[TargetCompound]
    :param test_ionization_mechanisms: List of ionization mechanisms to use for generating target ions.
    :type test_ionization_mechanisms: list[IonizationMechanism]

    :return: None
    """
    for target_compound in test_target_compounds_by_composition:
        target_ions, target_isotopes = generate_target_ions_from_composition(
            target_compound, test_ionization_mechanisms
        )
        assert_target_ions(target_compound, test_ionization_mechanisms, target_ions)
        assert_target_isotopes(target_ions, target_isotopes)


@pytest.mark.asyncio
async def test_generate_target_ions_from_mass(
    test_target_compounds_by_mass: list[tuple[float, TargetCompound]],
    test_ionization_mechanisms: list[IonizationMechanism],
) -> None:
    """Test generating target ions from target compounds defined by mass.

    :param test_target_compounds_by_mass: List of target compounds defined by mass.
    :type test_target_compounds_by_mass: list[tuple[float, TargetCompound]]
    :param test_ionization_mechanisms: List of ionization mechanisms to use for generating target ions.
    :type test_ionization_mechanisms: list[IonizationMechanism]

    :return: None
    """
    for target_compound_mass, target_compound in test_target_compounds_by_mass:
        target_ions, target_isotopes = generate_target_ions_from_mass(
            target_compound_mass, target_compound, test_ionization_mechanisms
        )
        assert_target_ions(target_compound, test_ionization_mechanisms, target_ions)
        assert_target_isotopes(target_ions, target_isotopes)
