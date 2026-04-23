"""
Unit tests for Dataset Pydantic models.
Tests schema validation for dataset-related models.
"""

import pytest
from pydantic import ValidationError

from mascope_backend.api.models.dataset.dataset_pydantic_model import (
    GetDatasetsQueryParams,
    DatasetCreate,
    DatasetUpdate,
)


def test_dataset_create_valid(dataset_data, dataset_create_model):
    """Test creating a dataset with valid data."""
    # Test with fixture data
    assert dataset_create_model.dataset_name == dataset_data["dataset_name"]
    assert (
        dataset_create_model.dataset_description
        == dataset_data["dataset_description"]
    )

    # Test with minimal required data
    dataset = DatasetCreate(dataset_name="Test Dataset")
    assert dataset.dataset_name == "Test Dataset"
    assert dataset.dataset_description is None

    # Test with all fields
    dataset = DatasetCreate(
        dataset_name="Test Dataset",
        dataset_description="This is a test dataset",
    )
    assert dataset.dataset_name == "Test Dataset"
    assert dataset.dataset_description == "This is a test dataset"


def test_dataset_create_invalid():
    """Test validation errors when creating a dataset with invalid data."""
    # Test missing required field
    with pytest.raises(ValidationError):
        DatasetCreate()

    # Test empty name
    with pytest.raises(ValidationError):
        DatasetCreate(dataset_name="")


def test_dataset_update_valid():
    """Test updating a dataset with valid data."""
    # Test empty update (no fields required)
    dataset = DatasetUpdate()
    assert dataset.dataset_name is None
    assert dataset.dataset_description is None

    # Test updating only name
    dataset = DatasetUpdate(dataset_name="Updated Dataset")
    assert dataset.dataset_name == "Updated Dataset"
    assert dataset.dataset_description is None

    # Test updating only description
    dataset = DatasetUpdate(dataset_description="Updated description")
    assert dataset.dataset_name is None
    assert dataset.dataset_description == "Updated description"


def test_query_params_defaults():
    """Test default values for query parameters."""
    params = GetDatasetsQueryParams()
    assert params.sort == "dataset_utc_created"
    assert params.order == "asc"
    assert params.page is None
    assert params.limit is None


def test_query_params_custom():
    """Test setting custom values for query parameters."""
    params = GetDatasetsQueryParams(
        sort="dataset_name", order="desc", page=2, limit=50
    )
    assert params.sort == "dataset_name"
    assert params.order == "desc"
    assert params.page == 2
    assert params.limit == 50
