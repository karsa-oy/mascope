"""
Unit tests for the workspace service functions.
Tests the logic in the workspace controllers.
"""

from datetime import datetime
import pytest

from mascope_backend.db.models import Workspace
import mascope_backend.api.controllers.workspace.workspace_controller as workspace_service
from mascope_backend.api.lib.exceptions.api_exceptions import ApiException
from mascope_backend.api.models.workspace.workspace_pydantic_model import (
    WorkspaceUpdate,
)


@pytest.mark.asyncio
async def test_get_workspaces(test_workspaces: list):
    """Test retrieving all workspaces with default parameters.

    This test verifies:
    1. The basic response structure (message, results, data)
    2. That the correct number of workspaces are returned
    3. That the returned data includes our test workspaces
    4. The default sorting order (by workspace_utc_created, ascending)

    :param test_workspaces: Pre-populated workspace fixtures
    :type test_workspaces: list
    """
    # Execute the controller function with default parameters
    result = await workspace_service.get_workspaces()

    # 1. Verify response structure
    assert isinstance(result, dict)
    assert "message" in result
    assert "results" in result
    assert "data" in result
    assert result["message"] == "Workspaces retrieved successfully"

    # 2. Verify workspace count
    assert result["results"] == len(test_workspaces)
    assert len(result["data"]) == len(test_workspaces)

    # 3. Verify our test workspaces are included in results
    workspace_ids = {w["workspace_id"] for w in result["data"]}
    for workspace in test_workspaces:
        assert workspace.workspace_id in workspace_ids

    # 4. Verify response data structure matches WorkspaceRead model
    first_workspace = result["data"][0]
    expected_fields = {
        "workspace_id",
        "workspace_name",
        "workspace_description",
        "workspace_utc_created",
        "workspace_utc_modified",
    }
    assert all(field in first_workspace for field in expected_fields)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "sort_field,order,expected_reversed",
    [
        ("workspace_name", "asc", False),
        ("workspace_name", "desc", True),
        ("workspace_utc_created", "asc", False),
        ("workspace_utc_created", "desc", True),
    ],
)
async def test_get_workspaces_sorting(
    test_workspaces, sort_field, order, expected_reversed
):
    """Test workspace retrieval with different sorting parameters.

    :param test_workspaces: Pre-populated workspace fixtures
    :param sort_field: Field to sort by ('workspace_name' or 'workspace_utc_created')
    :param order: Sort direction ('asc' or 'desc')
    :param expected_reversed: Whether to expect reversed order
    """
    # Execute the controller function with the specified sort parameters
    result = await workspace_service.get_workspaces(sort=sort_field, order=order)

    # Extract the field we're sorting by from the results
    if sort_field == "workspace_name":
        actual_values = [w["workspace_name"] for w in result["data"]]
        expected_values = sorted(actual_values.copy(), reverse=expected_reversed)
        assert actual_values == expected_values
    elif sort_field == "workspace_utc_created":
        # For datetime fields, verify they're in the right order
        dates = [w["workspace_utc_created"] for w in result["data"]]

        # Convert string dates to datetime objects if needed
        if dates and isinstance(dates[0], str):
            dates = [datetime.fromisoformat(d.replace("Z", "+00:00")) for d in dates]

        # Verify the dates are in the expected order
        assert dates == sorted(dates, reverse=expected_reversed)

    # Additional verification for the response
    assert result["message"] == "Workspaces retrieved successfully"
    assert len(result["data"]) == len(test_workspaces)


def _calculate_expected_count(total_count, limit, page):
    """Helper function to calculate expected count for a given page and limit."""
    if page * limit >= total_count:
        return 0  # No items on this page
    return min(limit, total_count - (page * limit))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "page,limit",
    [
        (0, 10),  # Default case, should return all workspaces if <= 10
        (0, 1),  # First page with limit 1
        (1, 1),  # Second page with limit 1
        (0, 5),  # First page with limit 5
        (100, 10),  # Page beyond available data
    ],
)
async def test_get_workspaces_pagination(test_workspaces, page, limit):
    """Test workspace retrieval with different pagination parameters.

    :param test_workspaces: Pre-populated workspace fixtures
    :param page: Page number (0-indexed)
    :param limit: Number of items per page
    """
    # Get total count first for verification
    total_result = await workspace_service.get_workspaces()
    total_count = total_result["results"]

    # Calculate expected count
    expected_items = _calculate_expected_count(total_count, limit, page)

    # Execute with pagination parameters
    result = await workspace_service.get_workspaces(page=page, limit=limit)

    # Verify result count
    assert len(result["data"]) == expected_items

    # Verify total is always accurate regardless of pagination
    assert result["results"] == total_count


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "workspace_id,should_exist",
    [
        ("unit-test-1", True),  # exist in test_workspaces
        ("unit-test-2", True),  # exist in test_workspaces
        ("nonexistent-id", False),  # not exist
        (f"{"a" * 100}", False),  # long id
        ("", False),  # empty string
    ],
)
async def test_get_workspace_existence(test_workspaces, workspace_id, should_exist):
    """Test retrieving workspaces that do and don't exist.

    :param test_workspaces: Pre-populated workspace fixtures
    :param workspace_id: ID to test with
    :param should_exist: Whether the workspace should exist or not
    """
    if should_exist:
        # Positive case - workspace should exist
        result = await workspace_service.get_workspace(workspace_id)

        # Verify response structure
        assert isinstance(result, dict)
        assert "message" in result
        assert "data" in result

        # Verify workspace data
        workspace_data = result["data"]
        assert workspace_data["workspace_id"] == workspace_id
        assert (
            f"Workspace '{workspace_data["workspace_name"]}' retrieved successfully"
            in result["message"]
        )

        # Verify all expected fields are present
        expected_fields = {
            "workspace_id",
            "workspace_name",
            "workspace_description",
            "workspace_utc_created",
            "workspace_utc_modified",
        }
        assert all(field in workspace_data for field in expected_fields)
    else:
        # Negative case - workspace should not exist
        with pytest.raises(ApiException) as exc_info:
            await workspace_service.get_workspace(workspace_id)
        assert (
            f"Workspace with ID '{workspace_id}' not found"
            in exc_info.value.user_message
        )
        assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_create_workspace(
    workspace_create_model, mock_sio_workspace, async_session_factory
):
    """Test creating a new workspace.

    This test verifies:
    1. A new workspace can be created with valid data
    2. The response structure is correct
    3. The workspace is actually saved to the database
    4. Socket.IO events are emitted properly

    :param workspace_create_model: Sample workspace creation data
    :param mock_sio_workspace: Mocked Socket.IO for event verification
    :param async_session_factory: Factory for creating database sessions
    """
    # Execute the controller function
    result = await workspace_service.create_workspace(workspace_create_model)

    # Verify response structure
    assert isinstance(result, dict)
    assert "message" in result
    assert "data" in result
    assert (
        f"Workspace '{workspace_create_model.workspace_name}' created successfully"
        in result["message"]
    )

    # Verify workspace data in response
    workspace_data = result["data"]
    assert workspace_data["workspace_name"] == workspace_create_model.workspace_name
    assert (
        workspace_data["workspace_description"]
        == workspace_create_model.workspace_description
    )
    assert "workspace_id" in workspace_data
    assert "workspace_utc_created" in workspace_data

    # Verify workspace exists in database
    async with async_session_factory() as session:
        db_workspace = await session.get(Workspace, workspace_data["workspace_id"])
        assert db_workspace is not None
        assert db_workspace.workspace_name == workspace_create_model.workspace_name
        assert (
            db_workspace.workspace_description
            == workspace_create_model.workspace_description
        )

    # Verify Socket.IO event was emitted
    mock_sio_workspace.emit.assert_called_once_with("workspace_reload", namespace="/")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "workspace_id,should_exist",
    [
        ("unit-test-1", True),  # existing workspace
        ("nonexistent-id", False),  # non-existent workspace
    ],
)
async def test_update_workspace(
    test_workspaces,
    workspace_update_model,
    workspace_id,
    should_exist,
    mock_sio_workspace,
    async_session_factory,
):
    """Test updating an existing workspace.

    This test verifies:
    1. An existing workspace can be updated with valid data
    2. Appropriate error is raised for non-existent workspaces
    3. The response structure is correct
    4. Socket.IO events are emitted properly
    5. Database is updated correctly

    :param test_workspaces: Pre-populated workspace fixtures
    :param workspace_update_model: Sample workspace update data
    :param workspace_id: ID of the workspace to update
    :param should_exist: Whether the workspace should exist
    :param mock_sio_workspace: Mocked Socket.IO for event verification
    :param async_session_factory: Factory for creating database sessions
    """
    if should_exist:
        # Positive case - workspace should exist and be updated
        result = await workspace_service.update_workspace(
            workspace_id, workspace_update_model
        )

        # Verify response structure
        assert isinstance(result, dict)
        assert "message" in result
        assert "data" in result
        assert "updated successfully" in result["message"]

        # Verify workspace data in response
        workspace_data = result["data"]
        assert workspace_data["workspace_id"] == workspace_id
        assert workspace_data["workspace_name"] == workspace_update_model.workspace_name
        assert (
            workspace_data["workspace_description"]
            == workspace_update_model.workspace_description
        )
        assert "workspace_utc_modified" in workspace_data

        # Verify Socket.IO events were emitted
        assert mock_sio_workspace.emit.call_count == 1
        mock_sio_workspace.emit.assert_any_call("workspace_reload", namespace="/")

        # Verify workspace was actually updated in the database
        async with async_session_factory() as session:
            updated_workspace = await session.get(Workspace, workspace_id)
            assert updated_workspace is not None
            assert (
                updated_workspace.workspace_name
                == workspace_update_model.workspace_name
            )
            assert (
                updated_workspace.workspace_description
                == workspace_update_model.workspace_description
            )
    else:
        # Negative case - workspace should not exist
        with pytest.raises(ApiException) as exc_info:
            await workspace_service.update_workspace(
                workspace_id, workspace_update_model
            )

        assert (
            f"Workspace with ID '{workspace_id}' not found"
            in exc_info.value.user_message
        )
        assert exc_info.value.status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "update_field,update_value",
    [
        ("workspace_name", "Only Name Updated"),
        ("workspace_description", "Only Description Updated"),
    ],
)
async def test_partial_update_workspace(
    test_workspaces, update_field, update_value, async_session_factory
):
    """Test partial updates to a workspace.

    This test verifies:
    1. Partial updates (only name or only description) work correctly
    2. Original values are preserved for fields not included in the update
    3. Database state is correctly updated

    :param test_workspaces: Pre-populated workspace fixtures
    :param update_field: Field to update ('workspace_name' or 'workspace_description')
    :param update_value: Value to set for the updated field
    :param async_session_factory: Factory for creating database sessions
    """
    # Get a fresh copy of the workspace to avoid state conflicts between test runs
    workspace_id = test_workspaces[0].workspace_id

    async with async_session_factory() as session:
        workspace = await session.get(Workspace, workspace_id)
        original_name = workspace.workspace_name
        original_description = workspace.workspace_description

    # Create a partial update model with just one field
    partial_update = {update_field: update_value}
    update_model = WorkspaceUpdate(**partial_update)

    # Execute update
    result = await workspace_service.update_workspace(workspace_id, update_model)

    # Verify response
    assert "updated successfully" in result["message"]

    # Check database state after update
    async with async_session_factory() as session:
        updated_workspace = await session.get(Workspace, workspace_id)

        if update_field == "workspace_name":
            # Name should be updated, description preserved
            assert updated_workspace.workspace_name == update_value
            assert updated_workspace.workspace_description == original_description
            # Verify response matches database
            assert result["data"]["workspace_name"] == update_value
            assert result["data"]["workspace_description"] == original_description
        else:
            # Description should be updated, name preserved
            assert updated_workspace.workspace_description == update_value
            assert updated_workspace.workspace_name == original_name
            # Verify response matches database
            assert result["data"]["workspace_description"] == update_value
            assert result["data"]["workspace_name"] == original_name


@pytest.mark.asyncio
async def test_update_both_fields_workspace(
    test_workspaces, mock_sio_workspace, async_session_factory
):
    """Test updating both name and description simultaneously.

    This test verifies:
    1. Multiple fields can be updated in a single operation
    2. All specified fields are updated correctly
    3. Database state reflects all changes

    :param test_workspaces: Pre-populated workspace fixtures
    :param mock_sio_workspace: Mocked Socket.IO for event verification
    :param async_session_factory: Factory for creating database sessions
    """
    workspace_id = test_workspaces[0].workspace_id
    update_data = {
        "workspace_name": "Both Fields Updated",
        "workspace_description": "Updated Together",
    }

    update_model = WorkspaceUpdate(**update_data)
    result = await workspace_service.update_workspace(workspace_id, update_model)

    # Verify response
    assert "updated successfully" in result["message"]
    assert result["data"]["workspace_name"] == update_data["workspace_name"]
    assert (
        result["data"]["workspace_description"] == update_data["workspace_description"]
    )

    # Verify database state
    async with async_session_factory() as session:
        updated_workspace = await session.get(Workspace, workspace_id)
        assert updated_workspace.workspace_name == update_data["workspace_name"]
        assert (
            updated_workspace.workspace_description
            == update_data["workspace_description"]
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "workspace_id,should_exist",
    [
        ("unit-test-2", True),  # existing workspace
        ("nonexistent-id", False),  # non-existent workspace
    ],
)
async def test_delete_workspace(
    test_workspaces,
    workspace_id,
    should_exist,
    mock_sio_workspace,
    async_session_factory,
):
    """Test deleting a workspace.

    This test verifies:
    1. An existing workspace can be deleted
    2. Appropriate error is raised for non-existent workspaces
    3. The response structure is correct
    4. Socket.IO events are emitted properly
    5. The workspace is actually removed from the database

    :param test_workspaces: Pre-populated workspace fixtures
    :param workspace_id: ID of the workspace to delete
    :param should_exist: Whether the workspace should exist
    :param mock_sio_workspace: Mocked Socket.IO for event verification
    :param async_session_factory: Factory for creating database sessions
    """
    if should_exist:
        # Get the workspace name before deletion for verification
        async with async_session_factory() as session:
            workspace = await session.get(Workspace, workspace_id)
            workspace_name = workspace.workspace_name

        # Positive case - workspace should exist and be deleted
        result = await workspace_service.delete_workspace(workspace_id)

        # Verify response structure
        assert isinstance(result, dict)
        assert "message" in result
        assert f"Workspace '{workspace_name}' deleted successfully" in result["message"]

        # Verify Socket.IO events were emitted
        assert mock_sio_workspace.emit.call_count == 1
        mock_sio_workspace.emit.assert_any_call("workspace_reload", namespace="/")

        # Verify workspace was actually deleted from the database
        async with async_session_factory() as session:
            deleted_workspace = await session.get(Workspace, workspace_id)
            assert deleted_workspace is None
    else:
        # Negative case - workspace should not exist
        with pytest.raises(ApiException) as exc_info:
            await workspace_service.delete_workspace(workspace_id)

        assert (
            f"Workspace with ID '{workspace_id}' not found"
            in exc_info.value.user_message
        )
        assert exc_info.value.status_code == 404
