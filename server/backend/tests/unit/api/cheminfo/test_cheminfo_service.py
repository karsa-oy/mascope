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


@pytest.mark.asyncio
async def test_retrieve_cheminfo_by_mz_basic(
    cheminfo_query_data_basic: dict,
    mzs_to_query_basic: list[float],
):
    """Test retrieving cheminfo data by m/z values for basic list.

    This test checks that the cheminfo service can retrieve data for a list of m/z values,
    validates the result format, and ensures that the expected formulae are present in the results.
    """
    for mz, expected_formula in mzs_to_query_basic:
        cheminfo_query_data_basic["mz"] = mz
        result = await retrieve_cheminfo_by_mz(**cheminfo_query_data_basic)
        assert_cheminfo_query_result_format(result)

        result_formulae = []

        for data_row in result["data"]:
            assert_cheminfo_result_row_format(data_row)
            result_formulae.append(data_row["target_compound_formula"])

        # Check if the expected formulae were found in the results
        assert expected_formula in result_formulae


@pytest.mark.asyncio
async def test_retrieve_cheminfo_by_mz_extended(
    cheminfo_query_data_extended: dict,
    mzs_to_query_extended: list[float],
):
    """Test retrieving cheminfo data by m/z values for extended list.

    This test checks that the cheminfo service can retrieve data for a list of m/z values,
    validates the result format, and ensures that the expected formulae are present in the results.
    """
    for mz, expected_formula in mzs_to_query_extended:
        cheminfo_query_data_extended["mz"] = mz
        result = await retrieve_cheminfo_by_mz(**cheminfo_query_data_extended)
        assert_cheminfo_query_result_format(result)

        result_formulae = []

        for data_row in result["data"]:
            # Check if the result contains expected fields
            assert_cheminfo_result_row_format(data_row)
            result_formulae.append(data_row["target_compound_formula"])

        # Check if the expected formulae were found in the results
        assert expected_formula in result_formulae
