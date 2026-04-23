"""
Fixtures specific to dataset API unit tests.
"""

import pytest

from mascope_backend.api.models.dataset.dataset_pydantic_model import (
    DatasetCreate,
    DatasetUpdate,
)


@pytest.fixture
def dataset_data():
    """Sample dataset data for testing."""
    return {
        "dataset_name": "Unit Test Dataset",
        "dataset_description": "A dataset for unit testing",
    }


@pytest.fixture
def dataset_create_model(dataset_data):
    """A sample DatasetCreate model for testing."""
    return DatasetCreate(**dataset_data)


@pytest.fixture
def dataset_update_model():
    """A sample DatasetUpdate model for testing."""
    return DatasetUpdate(
        dataset_name="Updated Unit Test Dataset",
        dataset_description="Updated dataset for unit testing",
    )


@pytest.fixture
def mock_emit_dataset(mock_emit_record_factory):
    """Mock emit_record_* functions for the dataset controller.

    This fixture uses the mock_emit_record_factory to create properly configured
    mocks for emit_record_created, emit_record_updated, and emit_record_deleted
    functions in the dataset controller.

    The returned object has three AsyncMock attributes:
    - created: Mock for emit_record_created
    - updated: Mock for emit_record_updated
    - deleted: Mock for emit_record_deleted

    :param mock_emit_record_factory: Factory function for creating emit_record mocks
    :type mock_emit_record_factory: callable from mock_emit_record_factory fixture
    :return: MagicMock with created, updated, deleted AsyncMock attributes
    :rtype: MagicMock
    """
    return mock_emit_record_factory(
        "mascope_backend.api.controllers.dataset.dataset_controller"
    )
