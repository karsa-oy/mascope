import pytest


"""
Tests: Workspace membership management.

Verifies the /api/workspaces/{workspace_id}/members endpoints enforce
correct role requirements and handle CRUD operations properly.
"""


def _members_url(workspace_id, user_id=None):
    base = f"/api/workspaces/{workspace_id}/members"
    if user_id is not None:
        return f"{base}/{user_id}"
    return base


# ============= Read (list members) =============


@pytest.mark.asyncio
async def test_list_members_as_guest(guest_client, ws_alpha):
    """Guest members can list workspace members."""
    resp = await guest_client.get(_members_url(ws_alpha["workspace_id"]))
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) >= 4  # guest, editor, admin, owner


@pytest.mark.asyncio
async def test_list_members_as_outsider(outsider_client, ws_alpha):
    """Non-members cannot list workspace members."""
    resp = await outsider_client.get(_members_url(ws_alpha["workspace_id"]))
    assert resp.status_code == 403


# ============= Add member =============


@pytest.mark.asyncio
async def test_add_member_as_admin(admin_client, outsider_user, ws_alpha):
    """Admin can add a new member to the workspace."""
    resp = await admin_client.post(
        _members_url(ws_alpha["workspace_id"]),
        json={"user_id": outsider_user.id, "workspace_role": "guest"},
    )
    assert resp.status_code == 201
    member_data = resp.json()["data"]
    assert member_data["user_id"] == outsider_user.id
    assert member_data["workspace_role"] == "guest"

    # Clean up: remove the member so other tests aren't affected
    await admin_client.delete(
        _members_url(ws_alpha["workspace_id"], outsider_user.id),
    )


@pytest.mark.asyncio
async def test_add_member_as_guest_forbidden(guest_client, outsider_user, ws_alpha):
    """Guest cannot add members."""
    resp = await guest_client.post(
        _members_url(ws_alpha["workspace_id"]),
        json={"user_id": outsider_user.id, "workspace_role": "guest"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_add_member_as_editor_forbidden(editor_client, outsider_user, ws_alpha):
    """Editor cannot add members."""
    resp = await editor_client.post(
        _members_url(ws_alpha["workspace_id"]),
        json={"user_id": outsider_user.id, "workspace_role": "guest"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_add_duplicate_member(admin_client, test_users, ws_alpha):
    """Adding an already-existing member returns a conflict error."""
    resp = await admin_client.post(
        _members_url(ws_alpha["workspace_id"]),
        json={"user_id": test_users["guest"].id, "workspace_role": "guest"},
    )
    assert resp.status_code == 409


# ============= Update member role =============


@pytest.mark.asyncio
async def test_update_member_role_as_admin(
    admin_client,
    outsider_user,
    ws_alpha,
):
    """Admin can change a member's role."""
    # First add the outsider as guest
    await admin_client.post(
        _members_url(ws_alpha["workspace_id"]),
        json={"user_id": outsider_user.id, "workspace_role": "guest"},
    )

    # Promote to editor
    resp = await admin_client.patch(
        _members_url(ws_alpha["workspace_id"], outsider_user.id),
        json={"workspace_role": "editor"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["workspace_role"] == "editor"

    # Clean up
    await admin_client.delete(
        _members_url(ws_alpha["workspace_id"], outsider_user.id),
    )


@pytest.mark.asyncio
async def test_update_member_role_as_guest_forbidden(
    guest_client, test_users, ws_alpha
):
    """Guest cannot change member roles."""
    resp = await guest_client.patch(
        _members_url(ws_alpha["workspace_id"], test_users["editor"].id),
        json={"workspace_role": "admin"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_member_role_as_editor_forbidden(
    editor_client, test_users, ws_alpha
):
    """Editor cannot change member roles."""
    resp = await editor_client.patch(
        _members_url(ws_alpha["workspace_id"], test_users["guest"].id),
        json={"workspace_role": "admin"},
    )
    assert resp.status_code == 403


# ============= Remove member =============


@pytest.mark.asyncio
async def test_remove_member_as_admin(admin_client, outsider_user, ws_alpha):
    """Admin can remove a member from the workspace."""
    # Add outsider first
    await admin_client.post(
        _members_url(ws_alpha["workspace_id"]),
        json={"user_id": outsider_user.id, "workspace_role": "guest"},
    )

    # Remove
    resp = await admin_client.delete(
        _members_url(ws_alpha["workspace_id"], outsider_user.id),
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["removed"] is True


@pytest.mark.asyncio
async def test_remove_last_owner_forbidden(owner_client, ws_alpha):
    """The last owner of a workspace cannot remove themselves (403)."""
    resp = await owner_client.delete(
        _members_url(ws_alpha["workspace_id"], ws_alpha["members"]["owner"].id),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_cannot_remove_owner(
    admin_client, owner_client, outsider_user, ws_alpha
):
    """Admin cannot remove an owner even when multiple owners exist (role ceiling)."""
    # Add outsider as a second owner
    await owner_client.post(
        _members_url(ws_alpha["workspace_id"]),
        json={"user_id": outsider_user.id, "workspace_role": "owner"},
    )

    # Admin tries to remove the second owner — should be blocked by role ceiling
    resp = await admin_client.delete(
        _members_url(ws_alpha["workspace_id"], outsider_user.id),
    )
    assert resp.status_code == 403

    # Clean up: owner removes the second owner
    await owner_client.delete(
        _members_url(ws_alpha["workspace_id"], outsider_user.id),
    )


@pytest.mark.asyncio
async def test_remove_member_as_guest_forbidden(guest_client, test_users, ws_alpha):
    """Guest cannot remove members."""
    resp = await guest_client.delete(
        _members_url(ws_alpha["workspace_id"], test_users["editor"].id),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_remove_member_as_editor_forbidden(editor_client, test_users, ws_alpha):
    """Editor cannot remove members."""
    resp = await editor_client.delete(
        _members_url(ws_alpha["workspace_id"], test_users["guest"].id),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_remove_nonexistent_member(admin_client, ws_alpha):
    """Removing a non-member returns 404."""
    resp = await admin_client.delete(
        _members_url(ws_alpha["workspace_id"], 999999),
    )
    assert resp.status_code == 404
