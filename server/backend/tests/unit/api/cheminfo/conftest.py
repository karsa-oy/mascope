"""
Fixtures specific to cheminfo API unit tests.
"""

import pytest

from mascope_backend.api.new.cheminfo.config import cheminfo_config
from mascope_backend.api.new.cheminfo.schema import (
    CheminfoMatchedQueryBody,
)


@pytest.fixture
def cheminfo_query_data(test_ionization_mechanisms: list):
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
    """A sample CheminfoMatchedQueryBody model for testing."""
    return CheminfoMatchedQueryBody(**cheminfo_matched_query_data)
