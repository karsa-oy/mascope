import pytest


"""
Tests: Membership-scoped dataset access.

Verifies that /api/workspaces/{workspace_id}/datasets routes enforce
workspace membership and correct role levels.
"""


def _url(workspace_id, dataset_id=None):
    base = f"/api/workspaces/{workspace_id}/datasets"
    if dataset_id is not None:
        return f"{base}/{dataset_id}"
    return base


_DATASET_DATA = {
    "dataset_name": "ACL Test Dataset",
    "dataset_description": "Created during ACL tests",
    "dataset_type": "ANALYSIS",
}


# ============= List datasets =============


@pytest.mark.asyncio
async def test_list_datasets_as_member(guest_client, ws_alpha, alpha_dataset):
    """Workspace guest can list datasets."""
    resp = await guest_client.get(_url(ws_alpha["workspace_id"]))
    assert resp.status_code == 200
    ids = [d["dataset_id"] for d in resp.json()["data"]]
    assert alpha_dataset in ids


@pytest.mark.asyncio
async def test_list_datasets_as_outsider(outsider_client, ws_alpha):
    """Non-member cannot list datasets in a workspace."""
    resp = await outsider_client.get(_url(ws_alpha["workspace_id"]))
    assert resp.status_code == 403


# ============= Get single dataset =============


@pytest.mark.asyncio
async def test_get_dataset_as_member(guest_client, ws_alpha, alpha_dataset):
    """Workspace guest can read a specific dataset."""
    resp = await guest_client.get(_url(ws_alpha["workspace_id"], alpha_dataset))
    assert resp.status_code == 200
    assert resp.json()["data"]["dataset_id"] == alpha_dataset


@pytest.mark.asyncio
async def test_get_dataset_as_outsider(outsider_client, ws_alpha, alpha_dataset):
    """Non-member cannot read a dataset."""
    resp = await outsider_client.get(_url(ws_alpha["workspace_id"], alpha_dataset))
    assert resp.status_code == 403


# ============= Create dataset =============


@pytest.mark.asyncio
async def test_create_dataset_as_editor(editor_client, ws_alpha):
    """Workspace editor can create a dataset."""
    resp = await editor_client.post(
        _url(ws_alpha["workspace_id"]),
        json=_DATASET_DATA,
    )
    assert resp.status_code == 201
    assert resp.json()["data"]["dataset_name"] == _DATASET_DATA["dataset_name"]


@pytest.mark.asyncio
async def test_create_dataset_as_guest_forbidden(guest_client, ws_alpha):
    """Workspace guest cannot create datasets (requires editor+)."""
    resp = await guest_client.post(
        _url(ws_alpha["workspace_id"]),
        json=_DATASET_DATA,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_dataset_outsider_forbidden(outsider_client, ws_alpha):
    """Non-member cannot create datasets in a workspace."""
    resp = await outsider_client.post(
        _url(ws_alpha["workspace_id"]),
        json=_DATASET_DATA,
    )
    assert resp.status_code == 403


# ============= Update dataset =============


@pytest.mark.asyncio
async def test_update_dataset_as_editor(editor_client, ws_alpha, alpha_dataset):
    """Workspace editor can update a dataset."""
    resp = await editor_client.patch(
        _url(ws_alpha["workspace_id"], alpha_dataset),
        json={"dataset_description": "Updated by editor"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_update_dataset_as_guest_forbidden(guest_client, ws_alpha, alpha_dataset):
    """Workspace guest cannot update datasets."""
    resp = await guest_client.patch(
        _url(ws_alpha["workspace_id"], alpha_dataset),
        json={"dataset_description": "Should fail"},
    )
    assert resp.status_code == 403


# ============= Delete dataset =============


@pytest.mark.asyncio
async def test_delete_dataset_as_guest_forbidden(guest_client, ws_alpha, alpha_dataset):
    """Workspace guest cannot delete datasets."""
    resp = await guest_client.delete(_url(ws_alpha["workspace_id"], alpha_dataset))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_delete_dataset_as_editor(editor_client, ws_alpha):
    """Workspace editor can delete a dataset.

    Creates a throwaway dataset to avoid destroying shared fixtures.
    """
    # Create
    create_resp = await editor_client.post(
        _url(ws_alpha["workspace_id"]),
        json={
            "dataset_name": "Dataset To Delete",
            "dataset_type": "ANALYSIS",
        },
    )
    assert create_resp.status_code == 201
    ds_id = create_resp.json()["data"]["dataset_id"]

    # Delete
    del_resp = await editor_client.delete(_url(ws_alpha["workspace_id"], ds_id))
    assert del_resp.status_code == 200


# ============= Cross-workspace isolation =============


@pytest.mark.asyncio
async def test_dataset_cross_workspace_isolation(
    guest_client,
    editor_client,
    ws_beta,
    beta_dataset,
):
    """Members of workspace Alpha cannot access datasets in workspace Beta.

    guest/editor/admin are members of ws_alpha but NOT ws_beta.
    """
    ws_id = ws_beta["workspace_id"]

    # Guest cannot list
    assert (await guest_client.get(_url(ws_id))).status_code == 403

    # Editor cannot list
    assert (await editor_client.get(_url(ws_id))).status_code == 403

    # Editor cannot read specific dataset
    assert (await editor_client.get(_url(ws_id, beta_dataset))).status_code == 403

    # Editor cannot create
    assert (
        await editor_client.post(_url(ws_id), json=_DATASET_DATA)
    ).status_code == 403
