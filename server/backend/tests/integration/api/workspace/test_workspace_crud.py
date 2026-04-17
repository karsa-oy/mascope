"""
Integration tests for the Workspace API endpoints.
Tests CRUD operations through the API to verify that endpoints work correctly.
"""

import asyncio

import pytest
from fastapi import status


# ============= Role-Based Access Control Tests =============


@pytest.mark.asyncio
async def test_rbac_guest_permissions(
    guest_client, editor_client, workspace_create_data
):
    """Test RBAC for guest users.

    Verifies guests can view workspaces but cannot create, update, or delete.
    """
    create_response = await editor_client.post(
        "/api/workspaces", json=workspace_create_data
    )
    assert create_response.status_code == 201
    workspace_id = create_response.json()["data"]["workspace_id"]

    assert (await guest_client.get("/api/workspaces")).status_code == 200
    assert (
        await guest_client.get(f"/api/workspaces/{workspace_id}")
    ).status_code == 200

    assert (
        await guest_client.post("/api/workspaces", json=workspace_create_data)
    ).status_code == status.HTTP_403_FORBIDDEN

    assert (
        await guest_client.patch(
            f"/api/workspaces/{workspace_id}",
            json={"workspace_name": "Guest Update Attempt"},
        )
    ).status_code == status.HTTP_403_FORBIDDEN

    assert (
        await guest_client.delete(f"/api/workspaces/{workspace_id}")
    ).status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_rbac_editor_permissions(
    editor_client, workspace_create_data, workspace_update_data
):
    """Test RBAC for editor users.

    Verifies editors can perform all CRUD operations on workspaces.
    """
    create_response = await editor_client.post(
        "/api/workspaces", json=workspace_create_data
    )
    assert create_response.status_code == 201
    workspace_id = create_response.json()["data"]["workspace_id"]

    assert (await editor_client.get("/api/workspaces")).status_code == 200
    assert (
        await editor_client.get(f"/api/workspaces/{workspace_id}")
    ).status_code == 200

    assert (
        await editor_client.patch(
            f"/api/workspaces/{workspace_id}", json=workspace_update_data
        )
    ).status_code == 200

    assert (
        await editor_client.delete(f"/api/workspaces/{workspace_id}")
    ).status_code == 200


# ============= Create Operations =============


@pytest.mark.asyncio
async def test_create_workspace(editor_client, workspace_create_data):
    """Test creating a workspace with valid data."""
    response = await editor_client.post("/api/workspaces", json=workspace_create_data)

    assert response.status_code == 201
    data = response.json()
    assert all(k in data for k in ["data", "message"])
    assert "workspace_id" in data["data"]

    workspace = data["data"]
    assert workspace["workspace_name"] == workspace_create_data["workspace_name"]
    assert (
        workspace["workspace_description"]
        == workspace_create_data["workspace_description"]
    )
    assert workspace["workspace_utc_created"] is not None
    assert workspace["workspace_utc_modified"] is None


@pytest.mark.asyncio
async def test_create_workspace_validation(editor_client):
    """Test validation during workspace creation."""
    assert (await editor_client.post("/api/workspaces", json={})).status_code == 422
    assert (
        await editor_client.post("/api/workspaces", json={"workspace_name": 123})
    ).status_code == 422
    assert (
        await editor_client.post("/api/workspaces", json={"workspace_name": ""})
    ).status_code == 422


# ============= Read Operations =============


@pytest.mark.asyncio
async def test_get_workspaces(guest_client, editor_client, workspace_create_data):
    """Test retrieving workspace list."""
    create_response = await editor_client.post(
        "/api/workspaces", json=workspace_create_data
    )
    workspace_id = create_response.json()["data"]["workspace_id"]

    response = await guest_client.get("/api/workspaces")
    assert response.status_code == 200

    data = response.json()
    assert all(k in data for k in ["data", "results", "message"])

    workspace_found = any(
        w["workspace_id"] == workspace_id
        and w["workspace_name"] == workspace_create_data["workspace_name"]
        and w["workspace_description"] == workspace_create_data["workspace_description"]
        for w in data["data"]
    )
    assert workspace_found, f"Workspace with ID {workspace_id} not found in results"


@pytest.mark.asyncio
async def test_get_single_workspace(editor_client, workspace_create_data):
    """Test retrieving a single workspace by ID."""
    create_response = await editor_client.post(
        "/api/workspaces", json=workspace_create_data
    )
    workspace_id = create_response.json()["data"]["workspace_id"]

    response = await editor_client.get(f"/api/workspaces/{workspace_id}")
    assert response.status_code == 200

    data = response.json()["data"]
    assert data["workspace_id"] == workspace_id
    assert data["workspace_name"] == workspace_create_data["workspace_name"]
    assert (
        data["workspace_description"] == workspace_create_data["workspace_description"]
    )
    assert data["workspace_utc_created"] is not None
    assert data["workspace_utc_modified"] is None


@pytest.mark.asyncio
async def test_get_workspaces_pagination(editor_client, workspace_create_data):
    """Test pagination for workspace list endpoint."""
    for i in range(5):
        payload = {**workspace_create_data, "workspace_name": f"Workspace {i + 1}"}
        await editor_client.post("/api/workspaces", json=payload)

    first_page = (await editor_client.get("/api/workspaces?page=0&limit=2")).json()
    assert len(first_page["data"]) == 2

    second_page = (await editor_client.get("/api/workspaces?page=1&limit=2")).json()
    assert len(second_page["data"]) <= 2

    if second_page["data"]:
        first_ids = {w["workspace_id"] for w in first_page["data"]}
        second_ids = {w["workspace_id"] for w in second_page["data"]}
        assert not (first_ids & second_ids), "Pages should not overlap"


@pytest.mark.asyncio
async def test_get_workspaces_sorting(editor_client, workspace_create_data):
    """Test sorting for workspace list endpoint."""
    names = ["C Workspace", "A Workspace", "B Workspace"]
    for name in names:
        payload = {**workspace_create_data, "workspace_name": name}
        await editor_client.post("/api/workspaces", json=payload)

    asc_response = (
        await editor_client.get("/api/workspaces?sort=workspace_name&order=asc")
    ).json()
    asc_names = [
        w["workspace_name"]
        for w in asc_response["data"]
        if w["workspace_name"] in names
    ]
    for i in range(len(asc_names) - 1):
        assert asc_names[i] <= asc_names[i + 1]

    desc_response = (
        await editor_client.get("/api/workspaces?sort=workspace_name&order=desc")
    ).json()
    desc_names = [
        w["workspace_name"]
        for w in desc_response["data"]
        if w["workspace_name"] in names
    ]
    for i in range(len(desc_names) - 1):
        assert desc_names[i] >= desc_names[i + 1]


# ============= Update Operations =============


@pytest.mark.asyncio
async def test_update_workspace(
    editor_client, workspace_create_data, workspace_update_data
):
    """Test updating a workspace."""
    create_response = await editor_client.post(
        "/api/workspaces", json=workspace_create_data
    )
    workspace = create_response.json()["data"]
    workspace_id = workspace["workspace_id"]
    creation_time = workspace["workspace_utc_created"]

    await asyncio.sleep(1)

    update_response = await editor_client.patch(
        f"/api/workspaces/{workspace_id}", json=workspace_update_data
    )
    assert update_response.status_code == 200

    updated = update_response.json()["data"]
    assert updated["workspace_id"] == workspace_id
    assert updated["workspace_name"] == workspace_update_data["workspace_name"]
    assert (
        updated["workspace_description"]
        == workspace_update_data["workspace_description"]
    )
    assert updated["workspace_utc_created"] == creation_time
    assert updated["workspace_utc_modified"] is not None

    get_response = await editor_client.get(f"/api/workspaces/{workspace_id}")
    get_data = get_response.json()["data"]
    assert get_data["workspace_name"] == workspace_update_data["workspace_name"]
    assert (
        get_data["workspace_description"]
        == workspace_update_data["workspace_description"]
    )


@pytest.mark.asyncio
async def test_update_workspace_partial(editor_client, workspace_create_data):
    """Test partial updates to a workspace."""
    create_response = await editor_client.post(
        "/api/workspaces", json=workspace_create_data
    )
    workspace_id = create_response.json()["data"]["workspace_id"]

    name_response = await editor_client.patch(
        f"/api/workspaces/{workspace_id}", json={"workspace_name": "Updated Name Only"}
    )
    assert name_response.status_code == 200
    name_data = name_response.json()["data"]
    assert name_data["workspace_name"] == "Updated Name Only"
    assert (
        name_data["workspace_description"]
        == workspace_create_data["workspace_description"]
    )

    desc_response = await editor_client.patch(
        f"/api/workspaces/{workspace_id}",
        json={"workspace_description": "Updated description only"},
    )
    assert desc_response.status_code == 200
    desc_data = desc_response.json()["data"]
    assert desc_data["workspace_name"] == "Updated Name Only"
    assert desc_data["workspace_description"] == "Updated description only"


# ============= Delete Operations =============


@pytest.mark.asyncio
async def test_delete_workspace(editor_client, workspace_create_data):
    """Test deleting a workspace."""
    create_response = await editor_client.post(
        "/api/workspaces", json=workspace_create_data
    )
    workspace_id = create_response.json()["data"]["workspace_id"]

    delete_response = await editor_client.delete(f"/api/workspaces/{workspace_id}")
    assert delete_response.status_code == 200
    assert "message" in delete_response.json()

    get_response = await editor_client.get(f"/api/workspaces/{workspace_id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_workspace_delete_cascades_to_sample_batches(
    editor_client, workspace_create_data, sample_batch_create_data
):
    """Test that deleting a workspace cascades to delete associated sample batches."""
    create_workspace_response = await editor_client.post(
        "/api/workspaces", json=workspace_create_data
    )
    assert create_workspace_response.status_code == 201
    workspace_id = create_workspace_response.json()["data"]["workspace_id"]

    sample_batch_data = {**sample_batch_create_data, "workspace_id": workspace_id}
    print(f"⚠️⚠️⚠️⚠️⚠️⚠️ Creating sample batch with data: {sample_batch_data}")
    create_batch_response = await editor_client.post(
        "/api/sample/batches", json=sample_batch_data
    )
    print(
        f"⚠️⚠️⚠️⚠️⚠️⚠️ Create batch response: {create_batch_response.status_code} - {create_batch_response.text}"
    )
    assert create_batch_response.status_code == 201
    sample_batch_id = create_batch_response.json()["data"]["sample_batch_id"]

    get_batch_response = await editor_client.get(
        f"/api/sample/batches/{sample_batch_id}"
    )
    assert get_batch_response.status_code == 200
    assert get_batch_response.json()["data"]["workspace_id"] == workspace_id

    delete_workspace_response = await editor_client.delete(
        f"/api/workspaces/{workspace_id}"
    )
    assert delete_workspace_response.status_code == 200

    assert (
        await editor_client.get(f"/api/sample/batches/{sample_batch_id}")
    ).status_code == 404
    assert (
        await editor_client.get(f"/api/workspaces/{workspace_id}")
    ).status_code == 404


# ============= Error Handling Tests =============


@pytest.mark.asyncio
async def test_nonexistent_workspace_operations(editor_client, workspace_update_data):
    """Test operations on non-existent workspaces."""
    nonexistent_id = "nonexistent123"

    assert (
        await editor_client.get(f"/api/workspaces/{nonexistent_id}")
    ).status_code == 404
    assert (
        await editor_client.patch(
            f"/api/workspaces/{nonexistent_id}", json=workspace_update_data
        )
    ).status_code == 404
    assert (
        await editor_client.delete(f"/api/workspaces/{nonexistent_id}")
    ).status_code == 404


# ============= End-to-End Workflow Tests =============


@pytest.mark.asyncio
async def test_workspace_lifecycle(
    editor_client, workspace_create_data, workspace_update_data
):
    """Test complete workspace lifecycle from creation to deletion."""
    create_response = await editor_client.post(
        "/api/workspaces", json=workspace_create_data
    )
    assert create_response.status_code == 201
    workspace = create_response.json()["data"]
    workspace_id = workspace["workspace_id"]

    assert workspace["workspace_name"] == workspace_create_data["workspace_name"]
    assert (
        workspace["workspace_description"]
        == workspace_create_data["workspace_description"]
    )
    assert workspace["workspace_utc_created"] is not None
    assert workspace["workspace_utc_modified"] is None

    get_response = await editor_client.get(f"/api/workspaces/{workspace_id}")
    assert get_response.status_code == 200
    creation_time = get_response.json()["data"]["workspace_utc_created"]

    await asyncio.sleep(1)

    update_response = await editor_client.patch(
        f"/api/workspaces/{workspace_id}", json=workspace_update_data
    )
    assert update_response.status_code == 200
    update_data = update_response.json()["data"]
    assert update_data["workspace_name"] == workspace_update_data["workspace_name"]
    assert (
        update_data["workspace_description"]
        == workspace_update_data["workspace_description"]
    )
    assert update_data["workspace_utc_created"] == creation_time
    assert update_data["workspace_utc_modified"] is not None

    assert (
        await editor_client.delete(f"/api/workspaces/{workspace_id}")
    ).status_code == 200
    assert (
        await editor_client.get(f"/api/workspaces/{workspace_id}")
    ).status_code == 404
