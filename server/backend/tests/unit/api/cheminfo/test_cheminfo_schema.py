"""
Unit tests for Workspace Pydantic models.
Tests schema validation for workspace-related models.
"""

import pytest
from pydantic import ValidationError

from mascope_backend.api.new.cheminfo.schema import (
    CheminfoQueryBody,
    CheminfoMatchedQueryBody,
)


def assert_cheminfo_query_model(cheminfo_query_data: dict):
    """Assert the cheminfo query model"""
    cheminfo_query_model = CheminfoQueryBody(**cheminfo_query_data)
    # Test with fixture data
    assert cheminfo_query_model.mz == cheminfo_query_data["mz"]
    # Test all default values
    for key, value in cheminfo_query_data.items():
        # Check if the model value is equal to the query data value
        assert key in cheminfo_query_model.__dict__
        assert getattr(cheminfo_query_model, key) == value


def test_cheminfo_basic_query_valid(cheminfo_query_data_basic):
    """Test making a cheminfo query with valid data."""
    assert_cheminfo_query_model(cheminfo_query_data_basic)


def test_cheminfo_extended_query_valid(cheminfo_query_data_extended):
    """Test making a cheminfo query with valid data."""
    assert_cheminfo_query_model(cheminfo_query_data_extended)


def test_cheminfo_query_invalid():
    """Test validation errors for query with invalid data."""
    # Test missing required field
    with pytest.raises(ValidationError):
        CheminfoQueryBody()
    with pytest.raises(ValidationError):
        CheminfoQueryBody(mz=123.456)

    # Test invalid m/z type
    with pytest.raises(ValidationError):
        CheminfoQueryBody(mz="hundred")


def test_cheminfo_matched_query_valid(
    cheminfo_matched_query_data, cheminfo_matched_query_model
):
    """Test making a cheminfo matched query with valid data."""
    # Test with fixture data
    assert cheminfo_matched_query_model.mz == cheminfo_matched_query_data["mz"]
    # Test all default values
    for key, value in cheminfo_matched_query_data.items():
        print(key, value)
        # Check if the model value is equal to the query data value
        assert key in cheminfo_matched_query_model.__dict__
        assert getattr(cheminfo_matched_query_model, key) == value


def test_cheminfo_matched_query_invalid():
    """Test validation errors for query with invalid data."""
    # Test missing required field
    with pytest.raises(ValidationError):
        CheminfoMatchedQueryBody()

    # Test invalid m/z type
    with pytest.raises(ValidationError):
        CheminfoMatchedQueryBody(mz="hundred")
