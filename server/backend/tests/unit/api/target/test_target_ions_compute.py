import json
import os

import pytest

from mascope_backend.api.controllers.target.lib.compute.target_ions_compute import (
    generate_target_ions_from_composition,
    generate_target_ions_from_mass,
)
from mascope_backend.db import (
    IonizationMechanism,
    TargetCompound,
    TargetIon,
    TargetIsotope,
)


HERE = os.path.dirname(__file__)
with open(os.path.join(HERE, "ions.json"), "r") as f:
    EXPECTED_IONS = json.load(f)
with open(os.path.join(HERE, "isotopes.json"), "r") as f:
    EXPECTED_ISOTOPES = json.load(f)


def summarize_isotopes(target_isotopes: list[TargetIsotope]) -> dict[str, dict]:
    """Create a summary per ion: monoisotopic m/z, relative abundance, and count."""

    grouped: dict[str, list[TargetIsotope]] = {}
    for isotope in target_isotopes:
        grouped.setdefault(isotope.target_ion_id, []).append(isotope)

    summary: dict[str, dict] = {}
    for ion_id, isotopes in grouped.items():
        M0 = max(isotopes, key=lambda iso: iso.relative_abundance)
        summary[ion_id] = {
            "mz_M0": M0.mz,
            "ra_M0": M0.relative_abundance,
            "num_isotopes": len(isotopes),
        }

    return summary


def assert_isotope_links(
    target_ions: list[TargetIon], target_isotopes: list[TargetIsotope]
) -> None:
    """Ensure isotopes and ions reference each other correctly."""

    ion_ids = {ion.target_ion_id for ion in target_ions}
    assert all(isotope.target_ion_id in ion_ids for isotope in target_isotopes)
    isotope_ids = {isotope.target_ion_id for isotope in target_isotopes}
    assert all(ion.target_ion_id in isotope_ids for ion in target_ions)


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

        # Validate ion formulas against pre-computed expectations
        expected_ions = EXPECTED_IONS[target_compound.target_compound_formula]
        actual_ions = [ion.target_ion_formula for ion in target_ions]
        assert sorted(actual_ions) == sorted(expected_ions)

        # Map ion ids to formulas for isotope checks
        ion_id_to_formula = {
            ion.target_ion_id: ion.target_ion_formula for ion in target_ions
        }

        # Build isotope summaries keyed by ion formula
        isotope_summary_by_formula: dict[str, dict] = {}
        for ion_id, summary in summarize_isotopes(target_isotopes).items():
            isotope_summary_by_formula[ion_id_to_formula[ion_id]] = summary

        expected_isotopes = {
            ion_formula: EXPECTED_ISOTOPES[ion_formula] for ion_formula in expected_ions
        }

        # Validate isotope formulas match expectations
        assert set(isotope_summary_by_formula.keys()) == set(expected_isotopes.keys())

        # Validate isotope summaries
        for ion_formula, actual in isotope_summary_by_formula.items():
            expected = expected_isotopes[ion_formula]
            assert actual["num_isotopes"] == expected["num_isotopes"]
            assert actual["mz_M0"] == pytest.approx(
                expected["mz_M0"], rel=1e-6, abs=1e-6
            )
            assert actual["ra_M0"] == pytest.approx(
                expected["ra_M0"], rel=1e-6, abs=1e-6
            )

        # Link integrity
        assert_isotope_links(target_ions, target_isotopes)


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
        # Generic checks: ensure some ions and isotopes were generated
        assert len(target_ions) > 0, "No target ions generated"
        assert len(target_isotopes) > 0, "No target isotopes generated"
        # Link integrity
        assert_isotope_links(target_ions, target_isotopes)
