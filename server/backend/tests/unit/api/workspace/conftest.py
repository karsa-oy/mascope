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
def mock_sio_workspace(mock_sio_factory):
    """Mock Socket.IO for the workspace controller.

    This fixture uses the mock_sio_factory to create a properly configured
    Socket.IO mock specifically for the workspace controller. It patches
    the exact import path where the workspace controller accesses Socket.IO.

    :param mock_sio_factory: Factory function for creating Socket.IO mocks
    :type mock_sio_factory: callable from mock_sio_factory fixture
    :return: Configured AsyncMock for Socket.IO in the workspace controller
    :rtype: MagicMock
    """
    return mock_sio_factory(
        "mascope_backend.api.controllers.workspace.workspace_controller"
    )
