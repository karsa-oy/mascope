from datetime import datetime, timezone

import pytest
import pytest_asyncio

from mascope_backend.db import (
    SampleBatch,
    TargetCollection,
    TargetCollectionInSampleBatch,
)
from mascope_backend.db.id import gen_id


"""
Tests: Workspace scoping of collection <-> batch associations.

The invariant: a workspace-scoped collection may only be associated with
batches of its own workspace; global collections (workspace_id=NULL) may span
workspaces. The invariant is enforced from both directions (collection
create/update and batch update), and changing a collection's batch
associations additionally requires editor access to the workspaces of the
batches being added or removed - preserved associations are exempt, so a
global collection with associations in other workspaces stays manageable.
"""


def _batch(dataset_id: str, name: str) -> SampleBatch:
    return SampleBatch(
        sample_batch_id=gen_id(),
        dataset_id=dataset_id,
        sample_batch_name=name,
        sample_batch_utc_created=datetime.now(timezone.utc),
    )


@pytest_asyncio.fixture
async def scratch_alpha_batch(async_session_factory, alpha_dataset):
    """Per-test batch in the Alpha dataset (safe to mutate)."""
    batch = _batch(alpha_dataset, "Scope Test Alpha Batch")
    async with async_session_factory() as session:
        session.add(batch)
        await session.commit()
    return batch.sample_batch_id


@pytest_asyncio.fixture
async def scratch_beta_batch(async_session_factory, beta_dataset):
    """Per-test batch in the Beta dataset (safe to mutate)."""
    batch = _batch(beta_dataset, "Scope Test Beta Batch")
    async with async_session_factory() as session:
        session.add(batch)
        await session.commit()
    return batch.sample_batch_id


@pytest_asyncio.fixture
async def alpha_collection(async_session_factory, ws_alpha):
    """Per-test TARGETS collection scoped to workspace Alpha."""
    tc_id = gen_id()
    async with async_session_factory() as session:
        session.add(
            TargetCollection(
                target_collection_id=tc_id,
                target_collection_name="Scope Test Alpha",
                target_collection_type="TARGETS",
                workspace_id=ws_alpha["workspace_id"],
            )
        )
        await session.commit()
    return tc_id


@pytest_asyncio.fixture
async def global_collection(async_session_factory):
    """Per-test global TARGETS collection."""
    tc_id = gen_id()
    async with async_session_factory() as session:
        session.add(
            TargetCollection(
                target_collection_id=tc_id,
                target_collection_name="Scope Test Global",
                target_collection_type="TARGETS",
                workspace_id=None,
            )
        )
        await session.commit()
    return tc_id


@pytest_asyncio.fixture
async def global_collection_with_beta_batch(async_session_factory, scratch_beta_batch):
    """Per-test global collection already associated with a Beta batch."""
    tc_id = gen_id()
    async with async_session_factory() as session:
        session.add(
            TargetCollection(
                target_collection_id=tc_id,
                target_collection_name="Scope Test Global+Beta",
                target_collection_type="TARGETS",
                workspace_id=None,
            )
        )
        session.add(
            TargetCollectionInSampleBatch(
                target_collection_id=tc_id,
                sample_batch_id=scratch_beta_batch,
            )
        )
        await session.commit()
    return tc_id


# ============= Collection side: scope validation =============


@pytest.mark.asyncio
async def test_create_with_out_of_scope_batch_conflict(
    owner_client, ws_alpha, scratch_beta_batch
):
    """A workspace-scoped collection cannot be created with batches from
    another workspace, even by a superuser."""
    resp = await owner_client.post(
        "/api/target/collections",
        json={
            "target_collection_name": "Cross-WS Create",
            "workspace_id": ws_alpha["workspace_id"],
            "sample_batch_ids": [scratch_beta_batch],
        },
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_create_with_in_scope_batch(owner_client, ws_alpha, scratch_alpha_batch):
    """A workspace-scoped collection can be created with its own workspace's
    batches."""
    resp = await owner_client.post(
        "/api/target/collections",
        json={
            "target_collection_name": "In-Scope Create",
            "workspace_id": ws_alpha["workspace_id"],
            "sample_batch_ids": [scratch_alpha_batch],
        },
    )
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_create_global_with_cross_workspace_batches(
    owner_client, scratch_alpha_batch, scratch_beta_batch
):
    """A global collection may be associated with batches in any workspace."""
    resp = await owner_client.post(
        "/api/target/collections",
        json={
            "target_collection_name": "Global Cross-WS Create",
            "workspace_id": None,
            "sample_batch_ids": [scratch_alpha_batch, scratch_beta_batch],
        },
    )
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_update_with_out_of_scope_batch_conflict(
    owner_client, alpha_collection, scratch_beta_batch
):
    """A workspace-scoped collection cannot be assigned batches from another
    workspace on update, even by a superuser."""
    resp = await owner_client.patch(
        f"/api/target/collections/{alpha_collection}",
        json={"sample_batch_ids": [scratch_beta_batch]},
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_update_with_in_scope_batch_as_editor(
    editor_client, alpha_collection, scratch_alpha_batch
):
    """A workspace editor can manage their collection's batches within the
    workspace (batches-only payload, as sent by the Manage batches dialog)."""
    resp = await editor_client.patch(
        f"/api/target/collections/{alpha_collection}",
        json={"sample_batch_ids": [scratch_alpha_batch]},
    )
    assert resp.status_code == 200


# ============= Collection side: batch-change ACL =============


@pytest.mark.asyncio
async def test_create_with_foreign_batch_forbidden(
    editor_client, ws_alpha, scratch_beta_batch
):
    """An alpha editor cannot create a collection referencing a beta batch
    (no membership in beta)."""
    resp = await editor_client.post(
        "/api/target/collections",
        json={
            "target_collection_name": "Foreign Batch Create",
            "workspace_id": ws_alpha["workspace_id"],
            "sample_batch_ids": [scratch_beta_batch],
        },
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_preserving_foreign_batches_allowed(
    admin_client,
    global_collection_with_beta_batch,
    scratch_alpha_batch,
    scratch_beta_batch,
):
    """A global admin without beta membership can change a global collection's
    alpha associations while preserving its beta associations."""
    resp = await admin_client.patch(
        f"/api/target/collections/{global_collection_with_beta_batch}",
        json={"sample_batch_ids": [scratch_beta_batch, scratch_alpha_batch]},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_update_removing_foreign_batch_forbidden(
    admin_client, global_collection_with_beta_batch
):
    """A global admin without beta membership cannot remove a global
    collection's beta associations."""
    resp = await admin_client.patch(
        f"/api/target/collections/{global_collection_with_beta_batch}",
        json={"sample_batch_ids": []},
    )
    assert resp.status_code == 403


# ============= Collection side: batches-only updates by editors =============


@pytest.mark.asyncio
async def test_batches_only_update_of_global_collection_as_editor(
    editor_client, global_collection, scratch_alpha_batch
):
    """A workspace editor can bulk-assign a global collection to their own
    workspace's batches via the collection-side Edit batches route."""
    resp = await editor_client.patch(
        f"/api/target/collections/{global_collection}",
        json={"sample_batch_ids": [scratch_alpha_batch]},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_batches_only_update_of_global_collection_foreign_batch_forbidden(
    editor_client, global_collection, scratch_beta_batch
):
    """An alpha editor cannot assign a global collection to beta batches."""
    resp = await editor_client.patch(
        f"/api/target/collections/{global_collection}",
        json={"sample_batch_ids": [scratch_beta_batch]},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_global_collection_field_update_still_requires_admin(
    editor_client, global_collection, scratch_alpha_batch
):
    """Mixing basic-field changes into the payload keeps the admin gate on
    global collections."""
    resp = await editor_client.patch(
        f"/api/target/collections/{global_collection}",
        json={
            "target_collection_name": "Renamed Global",
            "sample_batch_ids": [scratch_alpha_batch],
        },
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_batches_only_update_as_guest_forbidden(
    guest_client, global_collection, scratch_alpha_batch
):
    """A guest (read-only member) cannot change a global collection's batch
    associations in their workspace."""
    resp = await guest_client.patch(
        f"/api/target/collections/{global_collection}",
        json={"sample_batch_ids": [scratch_alpha_batch]},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_batches_only_update_as_outsider_forbidden(
    outsider_client, alpha_collection, scratch_alpha_batch
):
    """A non-member cannot change a workspace collection's associations at
    all (no read access to the collection)."""
    resp = await outsider_client.patch(
        f"/api/target/collections/{alpha_collection}",
        json={"sample_batch_ids": [scratch_alpha_batch]},
    )
    assert resp.status_code == 403


# ============= Batch side: scope validation =============


@pytest.mark.asyncio
async def test_batch_update_with_out_of_scope_collection_conflict(
    owner_client, scratch_alpha_batch, beta_target_collection
):
    """A batch cannot be assigned a collection scoped to another workspace."""
    resp = await owner_client.patch(
        f"/api/sample/batches/{scratch_alpha_batch}",
        json={"target_collection_ids": [beta_target_collection]},
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_batch_update_with_global_collection(
    editor_client, scratch_alpha_batch, global_collection
):
    """A workspace editor can assign a global collection to their batch
    without collection-mutation rights."""
    resp = await editor_client.patch(
        f"/api/sample/batches/{scratch_alpha_batch}",
        json={"target_collection_ids": [global_collection]},
    )
    assert resp.status_code == 200
