import pytest


"""
Tests: Membership-scoped sample batch access.

Verifies that /api/sample/batches routes enforce workspace membership
via the batch → dataset → workspace ACL resolution chain.
"""

# ============= Get single batch =============


@pytest.mark.asyncio
async def test_get_batch_as_member(guest_client, alpha_batch):
    """Workspace member (guest) can read a batch via require_batch_role("guest")."""
    resp = await guest_client.get(f"/api/sample/batches/{alpha_batch}")
    assert resp.status_code == 200
    assert resp.json()["data"]["sample_batch_id"] == alpha_batch


@pytest.mark.asyncio
async def test_get_batch_as_outsider(outsider_client, alpha_batch):
    """Non-member cannot read a batch."""
    resp = await outsider_client.get(f"/api/sample/batches/{alpha_batch}")
    assert resp.status_code == 403


# ============= Create batch =============


@pytest.mark.asyncio
async def test_create_batch_as_editor(editor_client, alpha_dataset):
    """Workspace editor can create a batch (check_dataset_access on body.dataset_id)."""
    resp = await editor_client.post(
        "/api/sample/batches",
        json={
            "dataset_id": alpha_dataset,
            "sample_batch_name": "ACL Test Batch",
            "target_collection_ids": [],
        },
    )
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_create_batch_as_guest_forbidden(guest_client, alpha_dataset):
    """Workspace guest cannot create batches (requires editor global role + editor
    workspace role)."""
    resp = await guest_client.post(
        "/api/sample/batches",
        json={
            "dataset_id": alpha_dataset,
            "sample_batch_name": "Should Fail",
            "target_collection_ids": [],
        },
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_batch_outsider_forbidden(outsider_client, alpha_dataset):
    """Non-member cannot create batches in a workspace they don't belong to."""
    resp = await outsider_client.post(
        "/api/sample/batches",
        json={
            "dataset_id": alpha_dataset,
            "sample_batch_name": "Should Fail",
            "target_collection_ids": [],
        },
    )
    assert resp.status_code == 403


# ============= List batches with dataset_id filter =============


@pytest.mark.asyncio
async def test_list_batches_with_dataset_filter_as_member(
    guest_client, alpha_dataset, alpha_batch
):
    """Member can list batches when filtering by dataset_id (check_dataset_access)."""
    resp = await guest_client.get(
        "/api/sample/batches",
        params={"dataset_id": alpha_dataset},
    )
    assert resp.status_code == 200
    batch_ids = [b["sample_batch_id"] for b in resp.json()["data"]]
    assert alpha_batch in batch_ids


@pytest.mark.asyncio
async def test_list_batches_with_dataset_filter_as_outsider(
    outsider_client, alpha_dataset
):
    """Non-member cannot list batches filtered by a dataset in a workspace they don't
    belong to."""
    resp = await outsider_client.get(
        "/api/sample/batches",
        params={"dataset_id": alpha_dataset},
    )
    assert resp.status_code == 403


# ============= List batches without dataset_id =============


@pytest.mark.asyncio
async def test_list_batches_without_dataset_id_rejected(outsider_client):
    """Listing batches without dataset_id is rejected (422).

    dataset_id is a required query parameter so that workspace ACL
    is always enforced via the dataset → workspace resolution chain.
    """
    resp = await outsider_client.get("/api/sample/batches")
    assert resp.status_code == 422


# ============= Cross-workspace isolation =============


@pytest.mark.asyncio
async def test_batch_cross_workspace_isolation(guest_client, editor_client, beta_batch):
    """Members of ws_alpha cannot access batches in ws_beta.

    beta_batch is in beta_dataset which is in ws_beta.
    guest/editor/admin are NOT members of ws_beta.
    """
    # Guest cannot read
    assert (
        await guest_client.get(f"/api/sample/batches/{beta_batch}")
    ).status_code == 403

    # Editor cannot read
    assert (
        await editor_client.get(f"/api/sample/batches/{beta_batch}")
    ).status_code == 403
