import pytest


"""
Tests: Membership-scoped target association access.

Verifies that /api/target/associations routes enforce workspace membership
through the associated collection or batch ACL chain.
"""


# ============= target_collections_in_sample_batch =============


@pytest.mark.asyncio
async def test_get_collections_in_batch_as_member(
    guest_client, alpha_collection_in_batch
):
    """Workspace member can query collection-batch associations for their workspace."""
    tc_id, batch_id = alpha_collection_in_batch
    resp = await guest_client.get(
        "/api/target/associations/target_collections_in_sample_batch",
        params={"sample_batch_id": batch_id},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    tc_ids = [r["target_collection_id"] for r in data]
    assert tc_id in tc_ids


@pytest.mark.asyncio
async def test_get_collections_in_batch_as_outsider(
    outsider_client, alpha_collection_in_batch
):
    """Non-member cannot query collection-batch associations via batch filter."""
    _, batch_id = alpha_collection_in_batch
    resp = await outsider_client.get(
        "/api/target/associations/target_collections_in_sample_batch",
        params={"sample_batch_id": batch_id},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_get_collections_in_batch_by_collection_as_outsider(
    outsider_client, alpha_collection_in_batch
):
    """Non-member cannot query association via collection_id filter either."""
    tc_id, _ = alpha_collection_in_batch
    resp = await outsider_client.get(
        "/api/target/associations/target_collections_in_sample_batch",
        params={"target_collection_id": tc_id},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_get_collections_in_batch_without_filter_forbidden(guest_client):
    """Calling without sample_batch_id or target_collection_id is rejected."""
    resp = await guest_client.get(
        "/api/target/associations/target_collections_in_sample_batch",
    )
    assert resp.status_code == 403


# ============= target_compound_in_target_collections =============


@pytest.mark.asyncio
async def test_get_compounds_in_collection_as_member(
    guest_client, alpha_target_collection
):
    """Workspace member can query compound-collection associations."""
    resp = await guest_client.get(
        "/api/target/associations/target_compound_in_target_collections",
        params={"target_collection_id": alpha_target_collection},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_get_compounds_in_collection_as_outsider(
    outsider_client, alpha_target_collection
):
    """Non-member cannot query compound-collection associations for a workspace
    collection."""
    resp = await outsider_client.get(
        "/api/target/associations/target_compound_in_target_collections",
        params={"target_collection_id": alpha_target_collection},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_get_compounds_in_global_collection_as_outsider(
    outsider_client, global_target_collection
):
    """Any authenticated user can query compound associations for a global collection"""
    resp = await outsider_client.get(
        "/api/target/associations/target_compound_in_target_collections",
        params={"target_collection_id": global_target_collection},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_get_compounds_in_collection_without_collection_id_forbidden(
    guest_client,
):
    """Calling without target_collection_id is rejected."""
    resp = await guest_client.get(
        "/api/target/associations/target_compound_in_target_collections",
    )
    assert resp.status_code == 403
