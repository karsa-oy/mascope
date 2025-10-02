"""
Unit tests for Workspace Pydantic models.
Tests schema validation for workspace-related models.
"""

import pytest
from pydantic import ValidationError

from mascope_backend.api.models.workspace.workspace_pydantic_model import (
    WorkspaceCreate,
    WorkspaceUpdate,
    GetWorkspacesQueryParams,
)


def test_workspace_create_valid(workspace_data, workspace_create_model):
    """Test creating a workspace with valid data."""
    # Test with fixture data
    assert workspace_create_model.workspace_name == workspace_data["workspace_name"]
    assert (
        workspace_create_model.workspace_description
        == workspace_data["workspace_description"]
    )

    # Test with minimal required data
    workspace = WorkspaceCreate(workspace_name="Test Workspace")
    assert workspace.workspace_name == "Test Workspace"
    assert workspace.workspace_description is None

    # Test with all fields
    workspace = WorkspaceCreate(
        workspace_name="Test Workspace",
        workspace_description="This is a test workspace",
    )
    assert workspace.workspace_name == "Test Workspace"
    assert workspace.workspace_description == "This is a test workspace"


def test_workspace_create_invalid():
    """Test validation errors when creating a workspace with invalid data."""
    # Test missing required field
    with pytest.raises(ValidationError):
        WorkspaceCreate()

    # Test empty name
    with pytest.raises(ValidationError):
        WorkspaceCreate(workspace_name="")


def test_workspace_update_valid():
    """Test updating a workspace with valid data."""
    # Test empty update (no fields required)
    workspace = WorkspaceUpdate()
    assert workspace.workspace_name is None
    assert workspace.workspace_description is None

    # Test updating only name
    workspace = WorkspaceUpdate(workspace_name="Updated Workspace")
    assert workspace.workspace_name == "Updated Workspace"
    assert workspace.workspace_description is None

    # Test updating only description
    workspace = WorkspaceUpdate(workspace_description="Updated description")
    assert workspace.workspace_name is None
    assert workspace.workspace_description == "Updated description"


def test_query_params_defaults():
    """Test default values for query parameters."""
    params = GetWorkspacesQueryParams()
    assert params.sort == "workspace_utc_created"
    assert params.order == "asc"
    assert params.page is None
    assert params.limit is None


def test_query_params_custom():
    """Test setting custom values for query parameters."""
    params = GetWorkspacesQueryParams(
        sort="workspace_name", order="desc", page=2, limit=50
    )
    assert params.sort == "workspace_name"
    assert params.order == "desc"
    assert params.page == 2
    assert params.limit == 50
