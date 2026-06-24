import pytest


"""
Tests: Membership-scoped sample item access.

Verifies that /api/sample/items routes enforce workspace membership
via the item → batch → dataset → workspace ACL resolution chain.
"""

# ============= Get single item =============


@pytest.mark.asyncio
async def test_get_item_as_member(guest_client, alpha_item):
    """Workspace member (guest) can read an item via require_sample_role("guest")."""
    resp = await guest_client.get(f"/api/sample/items/{alpha_item}")
    assert resp.status_code == 200
    assert resp.json()["data"]["sample_item_id"] == alpha_item


@pytest.mark.asyncio
async def test_get_item_as_outsider(outsider_client, alpha_item):
    """Non-member cannot read a sample item."""
    resp = await outsider_client.get(f"/api/sample/items/{alpha_item}")
    assert resp.status_code == 403


# ============= Create item =============


@pytest.mark.asyncio
async def test_create_item_as_editor(editor_client, alpha_batch, sample_file):
    """Workspace editor can create an item
    check_batch_access on body.sample_batch_id)."""
    resp = await editor_client.post(
        "/api/sample/items",
        json={
            "sample_batch_id": alpha_batch,
            "sample_file_id": sample_file,
            "sample_item_name": "ACL Test Item",
            "sample_item_type": "SAMPLE",
            "sample_item_attributes": {},
            "polarity": "+",
            "tic": 500.0,
            "t0": 0.0,
            "t1": 30.0,
        },
    )
    # 201 = success; 400 = sample_view not in test DB (controller-internal, not ACL)
    assert resp.status_code in (201, 400)
    assert resp.status_code != 403


@pytest.mark.asyncio
async def test_create_item_as_guest_forbidden(guest_client, alpha_batch, sample_file):
    """Workspace guest cannot create items
    requires editor global + workspace editor)."""
    resp = await guest_client.post(
        "/api/sample/items",
        json={
            "sample_batch_id": alpha_batch,
            "sample_file_id": sample_file,
            "sample_item_name": "Should Fail",
            "sample_item_type": "SAMPLE",
            "sample_item_attributes": {},
            "polarity": "+",
            "tic": 500.0,
            "t0": 0.0,
            "t1": 30.0,
        },
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_item_outsider_forbidden(
    outsider_client, alpha_batch, sample_file
):
    """Non-member cannot create items in a workspace they don't belong to."""
    resp = await outsider_client.post(
        "/api/sample/items",
        json={
            "sample_batch_id": alpha_batch,
            "sample_file_id": sample_file,
            "sample_item_name": "Should Fail",
            "sample_item_type": "SAMPLE",
            "sample_item_attributes": {},
            "polarity": "+",
            "tic": 500.0,
            "t0": 0.0,
            "t1": 30.0,
        },
    )
    assert resp.status_code == 403


# ============= List items with batch filter =============


@pytest.mark.asyncio
async def test_list_items_with_batch_filter_as_member(
    guest_client, alpha_batch, alpha_item
):
    """Member can list items when filtering by sample_batch_id (check_batch_access)."""
    resp = await guest_client.get(
        "/api/sample/items",
        params={"sample_batch_id": alpha_batch},
    )
    assert resp.status_code == 200
    item_ids = [i["sample_item_id"] for i in resp.json()["data"]]
    assert alpha_item in item_ids


@pytest.mark.asyncio
async def test_list_items_with_batch_filter_as_outsider(outsider_client, alpha_batch):
    """Non-member cannot list items filtered by a batch in a workspace they don't belong
    to."""
    resp = await outsider_client.get(
        "/api/sample/items",
        params={"sample_batch_id": alpha_batch},
    )
    assert resp.status_code == 403


# ============= GAP: List items without filter =============


@pytest.mark.asyncio
async def test_list_items_without_filter_rejected(outsider_client):
    """Listing items without sample_batch_id returns 422 (required param)."""
    resp = await outsider_client.get("/api/sample/items")
    assert resp.status_code == 422


# ============= Cross-workspace isolation =============


@pytest.mark.asyncio
async def test_item_cross_workspace_isolation(guest_client, editor_client, beta_item):
    """Members of ws_alpha cannot access items in ws_beta.

    beta_item is in beta_batch → beta_dataset → ws_beta.
    guest/editor/admin are NOT members of ws_beta.
    """
    # Guest cannot read
    assert (await guest_client.get(f"/api/sample/items/{beta_item}")).status_code == 403

    # Editor cannot read
    assert (
        await editor_client.get(f"/api/sample/items/{beta_item}")
    ).status_code == 403
