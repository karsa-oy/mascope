import pytest


"""
Tests: Workspace-level access control.

Verifies the /api/workspaces endpoints enforce correct Role requirements
and that workspace listing is scoped to user membership.
"""


def _url(workspace_id=None):
    base = "/api/workspaces"
    if workspace_id is not None:
        return f"{base}/{workspace_id}"
    return base


# ============= List workspaces (scoped to membership) =============


@pytest.mark.asyncio
async def test_list_workspaces_only_shows_memberships(
    guest_client,
    ws_alpha,
    ws_beta,
):
    """Users only see workspaces they are members of.

    - guest_client is a member of ws_alpha but NOT ws_beta
    - Both workspaces exist in the DB
    """
    resp = await guest_client.get(_url())
    assert resp.status_code == 200

    ws_ids = {w["workspace_id"] for w in resp.json()["data"]}
    assert ws_alpha["workspace_id"] in ws_ids
    assert ws_beta["workspace_id"] not in ws_ids


@pytest.mark.asyncio
async def test_list_workspaces_outsider_sees_none(outsider_client, ws_alpha, ws_beta):
    """Outsider user (no memberships at all) sees an empty list."""
    resp = await outsider_client.get(_url())
    assert resp.status_code == 200
    # Outsider is not a member of any workspace
    ws_ids = {w["workspace_id"] for w in resp.json()["data"]}
    assert ws_alpha["workspace_id"] not in ws_ids
    assert ws_beta["workspace_id"] not in ws_ids


# ============= Get single workspace =============


@pytest.mark.asyncio
async def test_get_workspace_as_guest(guest_client, ws_alpha):
    """Any workspace member (even guest) can read workspace details."""
    resp = await guest_client.get(_url(ws_alpha["workspace_id"]))
    assert resp.status_code == 200
    assert resp.json()["data"]["workspace_id"] == ws_alpha["workspace_id"]


@pytest.mark.asyncio
async def test_get_workspace_as_outsider(outsider_client, ws_alpha):
    """Non-members cannot read workspace details."""
    resp = await outsider_client.get(_url(ws_alpha["workspace_id"]))
    assert resp.status_code == 403


# ============= Create workspace =============


@pytest.mark.asyncio
async def test_create_workspace_adds_creator_as_owner(editor_client):
    """Creating a workspace auto-adds the creator as workspace owner."""
    resp = await editor_client.post(
        _url(),
        json={
            "workspace_name": "Creator Test Workspace",
            "workspace_description": "Testing auto-owner",
        },
    )
    assert resp.status_code == 200
    ws_data = resp.json()["data"]
    ws_id = ws_data["workspace_id"]

    # Verify the creator is now listed as a member with 'owner' role
    members_resp = await editor_client.get(f"/api/workspaces/{ws_id}/members")
    assert members_resp.status_code == 200
    members = members_resp.json()["data"]
    assert len(members) == 1
    assert members[0]["workspace_role"] == "owner"


@pytest.mark.asyncio
async def test_create_workspace_guest_forbidden(guest_client):
    """Guest global role cannot create workspaces (requires editor+)."""
    resp = await guest_client.post(
        _url(),
        json={"workspace_name": "Should Fail"},
    )
    assert resp.status_code == 403


# ============= Update workspace =============


@pytest.mark.asyncio
async def test_update_workspace_as_admin(admin_client, ws_alpha):
    """Admin can update workspace metadata."""
    resp = await admin_client.patch(
        _url(ws_alpha["workspace_id"]),
        json={"workspace_description": "Updated by admin"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["workspace_description"] == "Updated by admin"


@pytest.mark.asyncio
async def test_update_workspace_as_editor_forbidden(editor_client, ws_alpha):
    """Editor cannot update workspace (requires admin+)."""
    resp = await editor_client.patch(
        _url(ws_alpha["workspace_id"]),
        json={"workspace_description": "Should fail"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_workspace_as_guest_forbidden(guest_client, ws_alpha):
    """Guest cannot update workspace."""
    resp = await guest_client.patch(
        _url(ws_alpha["workspace_id"]),
        json={"workspace_description": "Should fail"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_workspace_as_outsider_forbidden(outsider_client, ws_alpha):
    """Outsider cannot update workspace."""
    resp = await outsider_client.patch(
        _url(ws_alpha["workspace_id"]),
        json={"workspace_description": "Should fail"},
    )
    assert resp.status_code == 403


# ============= Delete workspace =============


@pytest.mark.asyncio
async def test_delete_workspace_as_admin_forbidden(admin_client, ws_alpha):
    """Admin cannot delete workspace (requires owner)."""
    resp = await admin_client.delete(_url(ws_alpha["workspace_id"]))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_delete_workspace_as_editor_forbidden(editor_client, ws_alpha):
    """Editor cannot delete workspace."""
    resp = await editor_client.delete(_url(ws_alpha["workspace_id"]))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_delete_workspace_as_guest_forbidden(guest_client, ws_alpha):
    """Guest cannot delete workspace."""
    resp = await guest_client.delete(_url(ws_alpha["workspace_id"]))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_delete_workspace_as_outsider_forbidden(outsider_client, ws_alpha):
    """Outsider cannot delete workspace."""
    resp = await outsider_client.delete(_url(ws_alpha["workspace_id"]))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_delete_workspace_as_owner(owner_client):
    """Owner can delete a workspace.

    Uses a throwaway workspace to avoid destroying shared fixtures.
    """
    # Create a workspace first
    create_resp = await owner_client.post(
        _url(),
        json={"workspace_name": "Workspace To Delete"},
    )
    assert create_resp.status_code == 200
    ws_id = create_resp.json()["data"]["workspace_id"]

    # Owner deletes it
    del_resp = await owner_client.delete(_url(ws_id))
    assert del_resp.status_code == 200

    # Verify it's gone
    get_resp = await owner_client.get(_url(ws_id))
    assert get_resp.status_code == 404
