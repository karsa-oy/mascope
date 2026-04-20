"""Compare Mascope Tools composition candidates with ChemInfo query results."""

import httpx
import pytest

from mascope_backend.api.new.cheminfo.config import cheminfo_config
from mascope_backend.api.new.cheminfo.utils import (
    to_cheminfo_ionization_format,
    to_custom_element_format,
    to_explicit_isotope_format,
)
from mascope_tools.composition.finder import find_compositions
from mascope_tools.composition.utils import (
    normalize_formula_with_isotopes,
    parse_composition,
    to_hill_order,
)


class TestCompositionAssignmentAgainstChemInfo:
    """Validate that Mascope Tools and ChemInfo return the same composition set."""

    TEST_CASES = [
        # Basic test cases
        (62.99619, "HNO3", ""),  # -
        (90.03169, "C3H6O3", ""),  # -
        (124.9244, "CH2O2", ""),  # +Br-
        (168.9506, "C3H6O3", ""),  # +Br-
        (227.00313, "C3H5N3O9", ""),  # -
        (384.11231, "C10H15N2O10", ""),  # +(CH4N2O)H+
        (396.07757, "C13H23N3O6", ""),  # +Br-
        (456.36089, "C30H48O3", ""),  # -, Testosterone undecanoate
        # Extended test cases, covering non-default parameters
        (141.92850, "CH3I", "I0-1"),  # -, Methyl iodide
        (195.90023, "CF3I", "I0-1 F0-3"),  # -, Trifluoroiodomethane
        (157.99919, "HSO4", "S0-1"),  # +(CH4N2O)H+
        (78.9189, "Br", "Br0-1"),
        (80.9168, "Br", "[81Br]0-1"),
        (62.9854, "O3^N", "^N0-1"),
        (539.75763, "C15H12Br4O2", "Br0-4"),  # -, Tetrabromobisphenol A (TBBA)
    ]

    # Keep only mechanisms that both ChemInfo query and mascope_tools.find_compositions
    # can handle directly without backend-specific custom-element translation.
    IONIZATION_MECHANISMS = [
        "-H+",
        "+Br-",
        "+NO3-",
        "+H+",
        "+(CH4N2O)H+",
        "+",
        "-",
    ]

    @staticmethod
    def _normalize_formula(formula: str) -> str:
        """Normalize formulas for cross-system comparisons."""
        if formula is None or formula == "":
            return "()"
        if formula == "Ionization peak":
            return "()"

        # Convert explicit isotope labels to custom labels when available,
        # then normalize to canonical Hill notation.
        custom_formula = to_custom_element_format(formula)
        normalized_formula = normalize_formula_with_isotopes(custom_formula)
        return to_hill_order(parse_composition(normalized_formula))

    @classmethod
    def _build_formula_ranges(cls, formula_ranges_addition: str) -> str:
        """Build the formula ranges string for queries, combining defaults with any
        test-specific additions."""
        formula_ranges = cheminfo_config.DEFAULT_FORMULA_RANGE
        if formula_ranges_addition:
            formula_ranges = f"{formula_ranges} {formula_ranges_addition}"
        return formula_ranges

    @classmethod
    def _fetch_cheminfo_formulas(cls, mz: float, formula_ranges: str) -> set[str]:
        """Fetch candidate formulas from ChemInfo for a given m/z and formula ranges."""
        explicit_ranges, _ = to_explicit_isotope_format(formula_ranges)
        ionizations = ",".join(
            [to_cheminfo_ionization_format(i) for i in cls.IONIZATION_MECHANISMS]
        )

        params = {
            "mass": mz,
            "ionizations": ionizations,
            "precision": cheminfo_config.DEFAULT_MZ_PRECISION,
            "ranges": explicit_ranges,
            "allowNeutral": "false",
        }

        with httpx.Client(timeout=cheminfo_config.REQUEST_TIMEOUT) as client:
            response = client.get(
                f"{cheminfo_config.BASE_URL}/v1/mfFromMonoisotopicMass",
                params=params,
            )
            response.raise_for_status()
            payload = response.json()

        return {
            cls._normalize_formula((row.get("mf") or "()"))
            for row in payload.get("result", [])
        }

    @classmethod
    def _find_mascope_formulas(cls, mz: float, formula_ranges: str) -> set[str]:
        """Fetch candidate formulas from Mascope Tools for a given m/z and formula ranges."""
        explicit_ranges, _ = to_explicit_isotope_format(formula_ranges)
        params = {
            "monoisotopic_mass": mz,
            "target_monoisotopic_mass": mz,
            "mass_range_ppm": cheminfo_config.DEFAULT_MZ_PRECISION,
            "element_count_ranges": explicit_ranges,
            "ionizations": ",".join(cls.IONIZATION_MECHANISMS),
            # Keep this high enough so strict set equality is meaningful.
            "max_result_rows": 1000,
        }

        result = find_compositions(params)
        return {
            cls._normalize_formula(row.get("formula", ""))
            for row in result.get("results", [])
            if row.get("formula")
        }

    @pytest.mark.parametrize(
        "mz, expected_formula, formula_ranges_addition", TEST_CASES
    )
    def test_composition_set_matches_cheminfo(
        self,
        mz: float,
        expected_formula: str,
        formula_ranges_addition: str,
    ):
        """Compare full formula sets returned by ChemInfo and Mascope Tools."""
        formula_ranges = self._build_formula_ranges(formula_ranges_addition)

        cheminfo_formulas = self._fetch_cheminfo_formulas(mz, formula_ranges)
        mascope_formulas = self._find_mascope_formulas(mz, formula_ranges)
        expected_normalized = self._normalize_formula(expected_formula)

        assert expected_normalized in cheminfo_formulas, (
            f"Expected formula {expected_formula!r} is missing from ChemInfo results for m/z {mz}."
        )
        assert expected_normalized in mascope_formulas, (
            f"Expected formula {expected_formula!r} is missing from Mascope Tools results for m/z {mz}."
        )

        missing_from_mascope = sorted(cheminfo_formulas - mascope_formulas)
        extra_in_mascope = sorted(mascope_formulas - cheminfo_formulas)

        assert mascope_formulas == cheminfo_formulas, (
            f"Formula set mismatch for m/z {mz}. "
            f"Missing in Mascope: {missing_from_mascope}. "
            f"Extra in Mascope: {extra_in_mascope}."
        )
