"""
Integration tests for the Workspace API endpoints.
Tests CRUD operations through the API to verify that endpoints work correctly.
"""

import time
from fastapi import status


# ============= Role-Based Access Control Tests =============


def test_rbac_guest_permissions(guest_client, editor_client, workspace_create_data):
    """
    Test Role-Based Access Control (RBAC) for guest users.

    Verifies guests can view workspaces but cannot create, update, or delete them.
    """
    # Have an editor create a workspace for testing guest access
    create_response = editor_client.post("/api/workspaces", json=workspace_create_data)
    assert create_response.status_code == 201
    workspace_id = create_response.json()["data"]["workspace_id"]

    # READ operations - should succeed
    # List workspaces
    assert guest_client.get("/api/workspaces").status_code == 200

    # Get single workspace
    assert guest_client.get(f"/api/workspaces/{workspace_id}").status_code == 200

    # WRITE operations - should be forbidden
    # Create workspace
    assert (
        guest_client.post("/api/workspaces", json=workspace_create_data).status_code
        == status.HTTP_403_FORBIDDEN
    )

    # Update workspace
    assert (
        guest_client.patch(
            f"/api/workspaces/{workspace_id}",
            json={"workspace_name": "Guest Update Attempt"},
        ).status_code
        == status.HTTP_403_FORBIDDEN
    )

    # Delete workspace
    assert (
        guest_client.delete(f"/api/workspaces/{workspace_id}").status_code
        == status.HTTP_403_FORBIDDEN
    )


def test_rbac_editor_permissions(
    editor_client, workspace_create_data, workspace_update_data
):
    """
    Test Role-Based Access Control (RBAC) for editor users.

    Verifies editors can perform all CRUD operations on workspaces.
    """
    # Create workspace
    create_response = editor_client.post("/api/workspaces", json=workspace_create_data)
    assert create_response.status_code == 201
    workspace_id = create_response.json()["data"]["workspace_id"]

    # Read operations
    assert editor_client.get("/api/workspaces").status_code == 200
    assert editor_client.get(f"/api/workspaces/{workspace_id}").status_code == 200

    # Update workspace
    assert (
        editor_client.patch(
            f"/api/workspaces/{workspace_id}", json=workspace_update_data
        ).status_code
        == 200
    )

    # Delete workspace
    assert editor_client.delete(f"/api/workspaces/{workspace_id}").status_code == 200


# ============= Create Operations =============


def test_create_workspace(editor_client, workspace_create_data):
    """Test creating a workspace with valid data."""
    # Create workspace
    response = editor_client.post("/api/workspaces", json=workspace_create_data)

    # Check response status and structure
    assert response.status_code == 201
    data = response.json()
    assert all(k in data for k in ["data", "message"])
    assert "workspace_id" in data["data"]

    # Validate response data
    workspace = data["data"]
    assert workspace["workspace_name"] == workspace_create_data["workspace_name"]
    assert (
        workspace["workspace_description"]
        == workspace_create_data["workspace_description"]
    )
    assert workspace["workspace_utc_created"] is not None
    assert workspace["workspace_utc_modified"] is None


def test_create_workspace_validation(editor_client):
    """Test validation during workspace creation."""
    # Missing required field
    assert editor_client.post("/api/workspaces", json={}).status_code == 422

    # Invalid data type (number instead of string)
    assert (
        editor_client.post("/api/workspaces", json={"workspace_name": 123}).status_code
        == 422
    )

    # Empty string
    assert (
        editor_client.post("/api/workspaces", json={"workspace_name": ""}).status_code
        == 422
    )


# ============= Read Operations =============


def test_get_workspaces(guest_client, editor_client, workspace_create_data):
    """Test retrieving workspace list."""
    # Create a workspace first
    create_response = editor_client.post("/api/workspaces", json=workspace_create_data)
    workspace_id = create_response.json()["data"]["workspace_id"]

    # Get workspaces with guest client
    response = guest_client.get("/api/workspaces")
    assert response.status_code == 200

    # Verify response structure and content
    data = response.json()
    assert all(k in data for k in ["data", "results", "message"])

    # Find created workspace in results
    workspace_found = any(
        w["workspace_id"] == workspace_id
        and w["workspace_name"] == workspace_create_data["workspace_name"]
        and w["workspace_description"] == workspace_create_data["workspace_description"]
        for w in data["data"]
    )
    assert workspace_found, f"Workspace with ID {workspace_id} not found in results"


def test_get_single_workspace(editor_client, workspace_create_data):
    """Test retrieving a single workspace by ID."""
    # Create workspace
    create_response = editor_client.post("/api/workspaces", json=workspace_create_data)
    workspace_id = create_response.json()["data"]["workspace_id"]

    # Retrieve workspace
    response = editor_client.get(f"/api/workspaces/{workspace_id}")
    assert response.status_code == 200

    # Verify response data
    data = response.json()["data"]
    assert data["workspace_id"] == workspace_id
    assert data["workspace_name"] == workspace_create_data["workspace_name"]
    assert (
        data["workspace_description"] == workspace_create_data["workspace_description"]
    )
    assert data["workspace_utc_created"] is not None
    assert data["workspace_utc_modified"] is None


def test_get_workspaces_pagination(editor_client, workspace_create_data):
    """Test pagination for workspace list endpoint."""
    # Create multiple workspaces
    for i in range(5):
        payload = {**workspace_create_data, "workspace_name": f"Workspace {i+1}"}
        editor_client.post("/api/workspaces", json=payload)

    # Get first page (2 items)
    first_page = editor_client.get("/api/workspaces?page=0&limit=2").json()
    assert len(first_page["data"]) == 2

    # Get second page (2 items)
    second_page = editor_client.get("/api/workspaces?page=1&limit=2").json()
    assert len(second_page["data"]) <= 2

    # Verify pages don't overlap
    if second_page["data"]:
        first_ids = {w["workspace_id"] for w in first_page["data"]}
        second_ids = {w["workspace_id"] for w in second_page["data"]}
        assert not (first_ids & second_ids), "Pages should not overlap"


def test_get_workspaces_sorting(editor_client, workspace_create_data):
    """Test sorting for workspace list endpoint."""
    # Create workspaces with specific names for sorting test
    names = ["C Workspace", "A Workspace", "B Workspace"]
    for name in names:
        payload = {**workspace_create_data, "workspace_name": name}
        editor_client.post("/api/workspaces", json=payload)

    # Test ascending sort
    asc_response = editor_client.get(
        "/api/workspaces?sort=workspace_name&order=asc"
    ).json()
    asc_names = [
        w["workspace_name"]
        for w in asc_response["data"]
        if w["workspace_name"] in names
    ]

    # Check ascending order
    for i in range(len(asc_names) - 1):
        if i + 1 < len(asc_names):
            assert asc_names[i] <= asc_names[i + 1]

    # Test descending sort
    desc_response = editor_client.get(
        "/api/workspaces?sort=workspace_name&order=desc"
    ).json()
    desc_names = [
        w["workspace_name"]
        for w in desc_response["data"]
        if w["workspace_name"] in names
    ]

    # Check descending order
    for i in range(len(desc_names) - 1):
        if i + 1 < len(desc_names):
            assert desc_names[i] >= desc_names[i + 1]


# ============= Update Operations =============


def test_update_workspace(editor_client, workspace_create_data, workspace_update_data):
    """Test updating a workspace."""
    # Create workspace
    create_response = editor_client.post("/api/workspaces", json=workspace_create_data)
    workspace = create_response.json()["data"]
    workspace_id = workspace["workspace_id"]
    creation_time = workspace["workspace_utc_created"]

    # Ensure timestamps will be different
    time.sleep(1)

    # Update workspace
    update_response = editor_client.patch(
        f"/api/workspaces/{workspace_id}", json=workspace_update_data
    )
    assert update_response.status_code == 200

    # Verify updated data
    updated = update_response.json()["data"]
    assert updated["workspace_id"] == workspace_id
    assert updated["workspace_name"] == workspace_update_data["workspace_name"]
    assert (
        updated["workspace_description"]
        == workspace_update_data["workspace_description"]
    )
    assert updated["workspace_utc_created"] == creation_time
    assert updated["workspace_utc_modified"] is not None

    # Verify changes persisted
    get_response = editor_client.get(f"/api/workspaces/{workspace_id}")
    get_data = get_response.json()["data"]
    assert get_data["workspace_name"] == workspace_update_data["workspace_name"]
    assert (
        get_data["workspace_description"]
        == workspace_update_data["workspace_description"]
    )


def test_update_workspace_partial(editor_client, workspace_create_data):
    """Test partial updates to a workspace."""
    # Create workspace
    create_response = editor_client.post("/api/workspaces", json=workspace_create_data)
    workspace_id = create_response.json()["data"]["workspace_id"]

    # Update only name
    name_update = {"workspace_name": "Updated Name Only"}
    name_response = editor_client.patch(
        f"/api/workspaces/{workspace_id}", json=name_update
    )
    assert name_response.status_code == 200

    # Verify only name changed
    name_data = name_response.json()["data"]
    assert name_data["workspace_name"] == "Updated Name Only"
    assert (
        name_data["workspace_description"]
        == workspace_create_data["workspace_description"]
    )

    # Update only description
    desc_update = {"workspace_description": "Updated description only"}
    desc_response = editor_client.patch(
        f"/api/workspaces/{workspace_id}", json=desc_update
    )
    assert desc_response.status_code == 200

    # Verify only description changed
    desc_data = desc_response.json()["data"]
    assert desc_data["workspace_name"] == "Updated Name Only"  # From previous update
    assert desc_data["workspace_description"] == "Updated description only"


# ============= Delete Operations =============


def test_delete_workspace(editor_client, workspace_create_data):
    """Test deleting a workspace."""
    # Create workspace
    create_response = editor_client.post("/api/workspaces", json=workspace_create_data)
    workspace_id = create_response.json()["data"]["workspace_id"]

    # Delete workspace
    delete_response = editor_client.delete(f"/api/workspaces/{workspace_id}")
    assert delete_response.status_code == 200
    assert "message" in delete_response.json()

    # Verify workspace is gone
    get_response = editor_client.get(f"/api/workspaces/{workspace_id}")
    assert get_response.status_code == 404


def test_workspace_delete_cascades_to_sample_batches(
    editor_client, workspace_create_data, sample_batch_create_data
):
    """
    Test that deleting a workspace cascades to delete associated sample batches.

    Verifies:
    1. A workspace can be created
    2. A sample batch can be created in that workspace
    3. The sample batch can be retrieved
    4. Deleting the workspace causes the sample batch to be deleted as well
    """
    # Step 1: Create a workspace
    create_workspace_response = editor_client.post(
        "/api/workspaces", json=workspace_create_data
    )
    assert create_workspace_response.status_code == 201, "Failed to create workspace"

    workspace_id = create_workspace_response.json()["data"]["workspace_id"]

    # Step 2: Create a sample batch in the workspace
    # Update the sample batch data with the workspace_id
    sample_batch_data = {**sample_batch_create_data, "workspace_id": workspace_id}

    create_batch_response = editor_client.post(
        "/api/sample/batches", json=sample_batch_data
    )
    assert create_batch_response.status_code == 201, "Failed to create sample batch"

    sample_batch_id = create_batch_response.json()["data"]["sample_batch_id"]

    # Step 3: Verify the sample batch exists and is linked to the workspace
    get_batch_response = editor_client.get(f"/api/sample/batches/{sample_batch_id}")
    assert get_batch_response.status_code == 200, "Failed to get sample batch"
    assert (
        get_batch_response.json()["data"]["workspace_id"] == workspace_id
    ), "Sample batch not linked to correct workspace"

    # Step 4: Delete the workspace
    delete_workspace_response = editor_client.delete(f"/api/workspaces/{workspace_id}")
    assert delete_workspace_response.status_code == 200, "Failed to delete workspace"

    # Step 5: Verify the sample batch is also deleted (should return 404)
    get_deleted_batch_response = editor_client.get(
        f"/api/sample/batches/{sample_batch_id}"
    )
    assert (
        get_deleted_batch_response.status_code == 404
    ), "Sample batch was not deleted with workspace"

    # Step 6: Verify workspace is deleted (should return 404)
    get_deleted_workspace_response = editor_client.get(
        f"/api/workspaces/{workspace_id}"
    )
    assert (
        get_deleted_workspace_response.status_code == 404
    ), "Workspace was not deleted"


# ============= Error Handling Tests =============


def test_nonexistent_workspace_operations(editor_client, workspace_update_data):
    """Test operations on non-existent workspaces."""
    nonexistent_id = "nonexistent123"

    # All operations should return 404
    assert editor_client.get(f"/api/workspaces/{nonexistent_id}").status_code == 404
    assert (
        editor_client.patch(
            f"/api/workspaces/{nonexistent_id}", json=workspace_update_data
        ).status_code
        == 404
    )
    assert editor_client.delete(f"/api/workspaces/{nonexistent_id}").status_code == 404


# ============= End-to-End Workflow Tests =============


def test_workspace_lifecycle(
    editor_client, workspace_create_data, workspace_update_data
):
    """Test complete workspace lifecycle from creation to deletion."""
    # 1. Create workspace
    create_response = editor_client.post("/api/workspaces", json=workspace_create_data)
    assert create_response.status_code == 201
    workspace = create_response.json()["data"]
    workspace_id = workspace["workspace_id"]

    # Verify creation data
    assert workspace["workspace_name"] == workspace_create_data["workspace_name"]
    assert (
        workspace["workspace_description"]
        == workspace_create_data["workspace_description"]
    )
    assert workspace["workspace_utc_created"] is not None
    assert workspace["workspace_utc_modified"] is None

    # 2. Retrieve workspace
    get_response = editor_client.get(f"/api/workspaces/{workspace_id}")
    assert get_response.status_code == 200
    get_data = get_response.json()["data"]
    assert get_data["workspace_id"] == workspace_id

    # Store creation timestamp for later comparison
    creation_time = get_data["workspace_utc_created"]
    time.sleep(1)  # Ensure timestamps will differ

    # 3. Update workspace
    update_response = editor_client.patch(
        f"/api/workspaces/{workspace_id}", json=workspace_update_data
    )
    assert update_response.status_code == 200
    update_data = update_response.json()["data"]

    # 4. Verify update
    assert update_data["workspace_name"] == workspace_update_data["workspace_name"]
    assert (
        update_data["workspace_description"]
        == workspace_update_data["workspace_description"]
    )
    assert update_data["workspace_utc_created"] == creation_time
    assert update_data["workspace_utc_modified"] is not None

    # 5. Delete workspace
    delete_response = editor_client.delete(f"/api/workspaces/{workspace_id}")
    assert delete_response.status_code == 200

    # 6. Confirm deletion
    assert editor_client.get(f"/api/workspaces/{workspace_id}").status_code == 404
