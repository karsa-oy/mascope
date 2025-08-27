import pytest

from mascope_backend.db.models import (
    IonizationMechanism,
    TargetCompound,
    TargetIon,
    TargetIsotope,
)
from mascope_backend.api.controllers.target.ions.target_ions_controller import (
    create_target_ions,
)

from test_target_ions_compute import (
    assert_target_ions,
    assert_target_isotopes,
    assert_target_ion_formulae,
)


@pytest.mark.asyncio
async def test_create_target_ions_by_composition(
    test_target_compounds_by_composition: list[TargetCompound],
    test_ionization_mechanisms: list[IonizationMechanism],
) -> None:
    """Test creating target ions from target compounds defined by composition.

    :param test_target_compounds_by_composition: List of target compounds defined by composition.
    :type test_target_compounds_by_composition: list[TargetCompound]
    :param test_ionization_mechanisms: List of ionization mechanisms to use for creating target ions.
    :type test_ionization_mechanisms: list[IonizationMechanism]

    :return: None
    """
    for target_compound in test_target_compounds_by_composition:
        target_ions_data = await create_target_ions(
            target_compound, test_ionization_mechanisms, independent_transaction=True
        )

        assert "created_ions" in target_ions_data
        assert "created_isotopes" in target_ions_data

        # Validate created ions
        created_ions = target_ions_data["created_ions"]
        assert isinstance(created_ions, list)
        assert_target_ions(
            target_compound,
            test_ionization_mechanisms,
            [TargetIon(**ion) for ion in created_ions],
        )
        assert_target_ion_formulae(
            target_compound,
            test_ionization_mechanisms,
            [TargetIon(**ion) for ion in created_ions],
        )

        # Validate created isotopes
        created_isotopes = target_ions_data["created_isotopes"]
        assert isinstance(created_isotopes, list)
        assert_target_isotopes(
            [TargetIon(**ion) for ion in created_ions],
            [TargetIsotope(**isotope) for isotope in created_isotopes],
        )


@pytest.mark.asyncio
async def test_create_target_ions_by_mass(
    test_target_compounds_by_mass: list[tuple[float, TargetCompound]],
    test_ionization_mechanisms: list[IonizationMechanism],
) -> None:
    """Test creating target ions from target compounds defined by mass.

    :param test_target_compounds_by_mass: List of target compounds defined by mass. Tuples of (mass, TargetCompound).
    :type test_target_compounds_by_mass: list[tuple[float, TargetCompound]]
    :param test_ionization_mechanisms: List of ionization mechanisms to use for creating target ions.
    :type test_ionization_mechanisms: list[IonizationMechanism]

    :return: None
    """
    for target_compound_mass, target_compound in test_target_compounds_by_mass:
        target_ions_data = await create_target_ions(
            target_compound,
            test_ionization_mechanisms,
            target_compound_mass=target_compound_mass,
            independent_transaction=True,
        )

        assert "created_ions" in target_ions_data
        assert "created_isotopes" in target_ions_data

        # Validate created ions
        created_ions = target_ions_data["created_ions"]
        assert isinstance(created_ions, list)
        assert_target_ions(
            target_compound,
            test_ionization_mechanisms,
            [TargetIon(**ion) for ion in created_ions],
        )

        # Validate created isotopes
        created_isotopes = target_ions_data["created_isotopes"]
        assert isinstance(created_isotopes, list)
        assert_target_isotopes(
            [TargetIon(**ion) for ion in created_ions],
            [TargetIsotope(**isotope) for isotope in created_isotopes],
        )
