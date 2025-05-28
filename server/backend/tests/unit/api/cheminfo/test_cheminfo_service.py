"""
Unit tests for the cheminfo service functions.
"""

import pytest

from mascope_backend.api.new.cheminfo.service import (
    retrieve_cheminfo_by_mz,
)


def assert_cheminfo_query_result_format(result: dict):
    """Assert that the cheminfo query result has the expected format and is not empty."""
    assert isinstance(result, dict)
    assert "message" in result
    assert "results" in result
    assert "total" in result
    assert "page" in result
    assert "data" in result

    assert result["results"] > 0
    assert result["total"] > 0


def assert_cheminfo_result_row_format(result: dict):
    """Assert that a single row of the cheminfo result has the expected format."""
    assert isinstance(result, dict)
    assert "target_compound_formula" in result
    assert "target_compound_unsaturation" in result
    assert "ionization_mechanism" in result
    assert "target_isotope_mz" in result
    assert "target_isotope_mz_error_ppm" in result


@pytest.mark.parametrize(
    "mz, expected_formula, formula_ranges_addition",
    [
        # Basic test cases
        (62.99564, "HNO3", ""),
        (90.03169, "C3H6O3", ""),
        (124.9244, "CH2O2", ""),
        (168.9506, "C3H6O3", ""),
        # Extended test cases, covering non-default parameters
        (78.9189, "Br", "Br0-1"),
        (80.9168, "[81Br]", "[81Br]0-1"),
    ],
)
@pytest.mark.asyncio
async def test_retrieve_cheminfo_by_mz(
    mz, expected_formula, formula_ranges_addition, cheminfo_query_data: dict
):
    """Test retrieving cheminfo data by m/z values for basic list.

    This test checks that the cheminfo service can retrieve data for a list of m/z values,
    validates the result format, and ensures that the expected formulae are present in the results.
    """
    cheminfo_query_data["mz"] = mz
    cheminfo_query_data["formula_ranges"] = (
        f"{cheminfo_query_data['formula_ranges']} {formula_ranges_addition}"
    )
    result = await retrieve_cheminfo_by_mz(**cheminfo_query_data)
    assert_cheminfo_query_result_format(result)

    result_formulae = []

    for data_row in result["data"]:
        assert_cheminfo_result_row_format(data_row)
        result_formulae.append(data_row["target_compound_formula"])

    # Check if the expected formulae were found in the results
    assert expected_formula in result_formulae
