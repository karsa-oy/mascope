"""
Fixtures specific to workspace API unit tests.
"""

import pytest

from mascope_backend.api.models.workspace.workspace_pydantic_model import (
    WorkspaceCreate,
    WorkspaceUpdate,
)


@pytest.fixture
def workspace_data():
    """Sample workspace data for testing."""
    return {
        "workspace_name": "Unit Test Workspace",
        "workspace_description": "A workspace for unit testing",
    }


@pytest.fixture
def workspace_create_model(workspace_data):
    """A sample WorkspaceCreate model for testing."""
    return WorkspaceCreate(**workspace_data)


@pytest.fixture
def workspace_update_model():
    """A sample WorkspaceUpdate model for testing."""
    return WorkspaceUpdate(
        workspace_name="Updated Unit Test Workspace",
        workspace_description="Updated workspace for unit testing",
    )


@pytest.fixture
def mock_emit_workspace(mock_emit_record_factory):
    """Mock emit_record_* functions for the workspace controller.

    This fixture uses the mock_emit_record_factory to create properly configured
    mocks for emit_record_created, emit_record_updated, and emit_record_deleted
    functions in the workspace controller.

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
        "mascope_backend.api.controllers.workspace.workspace_controller"
    )
