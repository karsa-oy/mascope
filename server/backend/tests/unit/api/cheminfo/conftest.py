"""
Fixtures specific to cheminfo API unit tests.
"""

import pytest

from mascope_backend.api.new.cheminfo.schema import (
    CheminfoMatchedQueryBody,
)
from mascope_backend.api.new.cheminfo.config import cheminfo_config


@pytest.fixture
def cheminfo_query_data_basic(test_ionization_mechanisms: list):
    """Sample query data for testing."""
    return {
        "mz": 123.456,
        "mz_precision": cheminfo_config.DEFAULT_MZ_PRECISION,
        "formula_ranges": cheminfo_config.DEFAULT_FORMULA_RANGE,
        "ionization_mechanism_ids": [
            im.ionization_mechanism_id for im in test_ionization_mechanisms
        ],
    }


@pytest.fixture
def cheminfo_query_data_extended(test_ionization_mechanisms: list):
    """Sample query data for testing."""
    return {
        "mz": 123.456,
        "mz_precision": cheminfo_config.DEFAULT_MZ_PRECISION,
        "formula_ranges": f"{cheminfo_config.DEFAULT_FORMULA_RANGE} Br0-1 [81Br]0-1",
        "ionization_mechanism_ids": [
            im.ionization_mechanism_id for im in test_ionization_mechanisms
        ],
    }


@pytest.fixture
def mzs_to_query_basic():
    """Sample m/z values with formulae for testing.

    This fixture provides a basic list of m/z values and their corresponding
    formulae for testing cheminfo queries, with default query parameters.
    """
    return [
        (62.99564, "HNO3"),
        (90.03169, "C3H6O3"),
    ]


@pytest.fixture
def mzs_to_query_extended():
    """Sample m/z values with formulae for testing.

    This fixture provides a more extensive list of m/z values and their corresponding
    formulae for testing cheminfo queries, including some edge cases, requiring
    non-default query parameters.
    """
    return [
        (78.9189, "Br"),
        (80.9168, "[81Br]"),
        (124.9244, "CH2O2"),
        (168.9506, "C3H6O3"),
    ]


@pytest.fixture
def cheminfo_matched_query_data(test_ionization_mechanisms: list):
    """Sample query data for testing."""
    return {
        "mz": 123.456,
        "mz_precision": cheminfo_config.DEFAULT_MZ_PRECISION,
        "formula_ranges": cheminfo_config.DEFAULT_FORMULA_RANGE,
        "ionization_mechanism_ids": [
            im.ionization_mechanism_id for im in test_ionization_mechanisms
        ],
        "match_params": None,
    }


@pytest.fixture
def cheminfo_matched_query_model(cheminfo_matched_query_data: dict):
    """A sample CheminfoQueryBody model for testing."""
    return CheminfoMatchedQueryBody(**cheminfo_matched_query_data)


@pytest.fixture
def mock_sio_cheminfo(mock_sio_factory):
    """Mock Socket.IO for the cheminfo service.

    :param mock_sio_factory: Factory function for creating Socket.IO mocks
    :type mock_sio_factory: callable from mock_sio_factory fixture
    :return: Configured AsyncMock for Socket.IO in the cheminfo service
    :rtype: MagicMock
    """
    return mock_sio_factory("mascope_backend.api.new.cheminfo.service")
