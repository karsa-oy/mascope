import pytest
import pytest_asyncio

from mascope_backend.db import TargetCollection, TargetCollectionInSampleBatch
from mascope_backend.db.id import gen_id


"""
Tests: Membership-scoped target collection access.

Verifies that /api/target/collections routes enforce workspace membership
via the collection → workspace ACL resolution chain.

Three collection types tested:
- alpha_target_collection: scoped to ws_alpha (all test users are members)
- beta_target_collection: scoped to ws_beta (only owner is a member)
- global_target_collection: no workspace (readable by all, mutations require admin+
  global role)
"""


# ============= GET single collection =============


@pytest.mark.asyncio
async def test_get_collection_as_member(guest_client, alpha_target_collection):
    """Workspace member (guest) can read a collection in their workspace."""
    resp = await guest_client.get(f"/api/target/collections/{alpha_target_collection}")
    assert resp.status_code == 200
    assert resp.json()["data"]["target_collection_id"] == alpha_target_collection


@pytest.mark.asyncio
async def test_get_collection_as_outsider(outsider_client, alpha_target_collection):
    """Non-member cannot read a workspace-scoped collection."""
    resp = await outsider_client.get(
        f"/api/target/collections/{alpha_target_collection}"
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_get_global_collection_as_outsider(
    outsider_client, global_target_collection
):
    """Any authenticated user can read a global collection (workspace_id=NULL)."""
    resp = await outsider_client.get(
        f"/api/target/collections/{global_target_collection}"
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["target_collection_id"] == global_target_collection


@pytest.mark.asyncio
async def test_get_beta_collection_as_guest(guest_client, beta_target_collection):
    """Guest user (alpha member only) cannot read a beta-scoped collection."""
    resp = await guest_client.get(f"/api/target/collections/{beta_target_collection}")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_get_beta_collection_as_owner(owner_client, beta_target_collection):
    """Owner (member of both alpha and beta) can read a beta-scoped collection."""
    resp = await owner_client.get(f"/api/target/collections/{beta_target_collection}")
    assert resp.status_code == 200


# ============= GET list (workspace-filtered) =============


@pytest.mark.asyncio
async def test_list_collections_member_sees_own_workspace(
    guest_client, ws_alpha, alpha_target_collection, global_target_collection
):
    """Member sees collections from their workspaces plus global collections."""
    resp = await guest_client.get("/api/target/collections")
    assert resp.status_code == 200
    ids = [c["target_collection_id"] for c in resp.json()["data"]]
    assert alpha_target_collection in ids
    assert global_target_collection in ids


@pytest.mark.asyncio
async def test_list_collections_outsider_sees_only_global(
    outsider_client, alpha_target_collection, global_target_collection
):
    """Non-member sees only global collections (workspace_id=NULL)."""
    resp = await outsider_client.get("/api/target/collections")
    assert resp.status_code == 200
    ids = [c["target_collection_id"] for c in resp.json()["data"]]
    assert alpha_target_collection not in ids
    assert global_target_collection in ids


@pytest.mark.asyncio
async def test_list_collections_cross_workspace_isolation(
    guest_client, beta_target_collection
):
    """Guest (alpha member only) does not see beta-scoped collections."""
    resp = await guest_client.get("/api/target/collections")
    assert resp.status_code == 200
    ids = [c["target_collection_id"] for c in resp.json()["data"]]
    assert beta_target_collection not in ids


@pytest.mark.asyncio
async def test_list_collections_superuser_sees_all(
    owner_client,
    alpha_target_collection,
    beta_target_collection,
    global_target_collection,
):
    """Superuser (owner) sees all collections across all workspaces."""
    resp = await owner_client.get("/api/target/collections")
    assert resp.status_code == 200
    ids = [c["target_collection_id"] for c in resp.json()["data"]]
    assert alpha_target_collection in ids
    assert beta_target_collection in ids
    assert global_target_collection in ids


# ============= POST create =============


@pytest.mark.asyncio
async def test_create_collection_as_editor(editor_client, ws_alpha):
    """Editor in workspace can create a collection scoped to that workspace."""
    resp = await editor_client.post(
        "/api/target/collections",
        json={
            "target_collection_name": "ACL Test Create",
            "workspace_id": ws_alpha["workspace_id"],
        },
    )
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_create_collection_as_guest_forbidden(guest_client, ws_alpha):
    """Guest cannot create a collection (requires editor workspace role)."""
    resp = await guest_client.post(
        "/api/target/collections",
        json={
            "target_collection_name": "Should Fail",
            "workspace_id": ws_alpha["workspace_id"],
        },
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_collection_outsider_forbidden(outsider_client, ws_alpha):
    """Non-member cannot create a collection in a workspace they don't belong to."""
    resp = await outsider_client.post(
        "/api/target/collections",
        json={
            "target_collection_name": "Should Fail",
            "workspace_id": ws_alpha["workspace_id"],
        },
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_global_collection_as_editor_forbidden(editor_client):
    """Editor (global role < admin) cannot create a global collection."""
    resp = await editor_client.post(
        "/api/target/collections",
        json={
            "target_collection_name": "Should Fail",
            "workspace_id": None,
        },
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_global_collection_as_admin(admin_client):
    """Admin (global role >= admin) can create a global collection."""
    resp = await admin_client.post(
        "/api/target/collections",
        json={
            "target_collection_name": "Admin Global Collection",
            "workspace_id": None,
        },
    )
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_create_global_collection_as_superuser(owner_client):
    """Superuser (owner) can create a global collection."""
    resp = await owner_client.post(
        "/api/target/collections",
        json={
            "target_collection_name": "Superuser Global Collection",
            "workspace_id": None,
        },
    )
    assert resp.status_code == 201


# ============= PATCH update =============


@pytest.mark.asyncio
async def test_update_collection_as_editor(editor_client, alpha_target_collection):
    """Editor in workspace can update a collection in their workspace."""
    resp = await editor_client.patch(
        f"/api/target/collections/{alpha_target_collection}",
        json={
            "target_collection_name": "Updated Alpha Collection",
        },
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_update_collection_as_guest_forbidden(
    guest_client, alpha_target_collection
):
    """Guest cannot update a collection (requires editor workspace role)."""
    resp = await guest_client.patch(
        f"/api/target/collections/{alpha_target_collection}",
        json={
            "target_collection_name": "Should Fail",
        },
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_collection_outsider_forbidden(
    outsider_client, alpha_target_collection
):
    """Non-member cannot update a workspace-scoped collection."""
    resp = await outsider_client.patch(
        f"/api/target/collections/{alpha_target_collection}",
        json={
            "target_collection_name": "Should Fail",
        },
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_global_collection_as_editor_forbidden(
    editor_client, global_target_collection
):
    """Editor (global role < admin) cannot update a global collection."""
    resp = await editor_client.patch(
        f"/api/target/collections/{global_target_collection}",
        json={
            "target_collection_name": "Should Fail",
        },
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_global_collection_as_admin(
    admin_client, global_target_collection
):
    """Admin (global role >= admin) can update a global collection."""
    resp = await admin_client.patch(
        f"/api/target/collections/{global_target_collection}",
        json={
            "target_collection_name": "Admin Updated Global",
        },
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_update_global_collection_as_superuser(
    owner_client, global_target_collection
):
    """Superuser (owner) can update a global collection."""
    resp = await owner_client.patch(
        f"/api/target/collections/{global_target_collection}",
        json={
            "target_collection_name": "Updated Global Collection",
        },
    )
    assert resp.status_code == 200


# ============= DELETE =============


@pytest.mark.asyncio
async def test_delete_collection_outsider_forbidden(
    outsider_client, alpha_target_collection
):
    """Non-member cannot delete a workspace-scoped collection."""
    resp = await outsider_client.delete(
        f"/api/target/collections/{alpha_target_collection}"
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_delete_collection_as_guest_forbidden(
    guest_client, alpha_target_collection
):
    """Guest cannot delete a collection (requires editor workspace role)."""
    resp = await guest_client.delete(
        f"/api/target/collections/{alpha_target_collection}"
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_delete_global_collection_as_editor_forbidden(
    editor_client, global_target_collection
):
    """Editor (global role < admin) cannot delete a global collection."""
    resp = await editor_client.delete(
        f"/api/target/collections/{global_target_collection}"
    )
    assert resp.status_code == 403


# ============= DELETE (positive) =============


@pytest.mark.asyncio
async def test_delete_collection_as_editor(
    editor_client, async_session_factory, ws_alpha
):
    """Editor in workspace can delete a collection scoped to that workspace."""
    tc_id = gen_id()
    async with async_session_factory() as session:
        session.add(
            TargetCollection(
                target_collection_id=tc_id,
                target_collection_name="Deletable Alpha",
                workspace_id=ws_alpha["workspace_id"],
            )
        )
        await session.commit()

    resp = await editor_client.delete(f"/api/target/collections/{tc_id}")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_delete_global_collection_as_admin(admin_client, async_session_factory):
    """Admin (global role >= admin) can delete a global collection."""
    tc_id = gen_id()
    async with async_session_factory() as session:
        session.add(
            TargetCollection(
                target_collection_id=tc_id,
                target_collection_name="Deletable Global",
                workspace_id=None,
            )
        )
        await session.commit()

    resp = await admin_client.delete(f"/api/target/collections/{tc_id}")
    assert resp.status_code == 200


# ============= PATCH scope change — auth =============


@pytest_asyncio.fixture
async def _alpha_collection(async_session_factory, ws_alpha):
    """Per-test alpha-scoped collection for scope-change mutations."""
    tc_id = gen_id()
    async with async_session_factory() as session:
        session.add(
            TargetCollection(
                target_collection_id=tc_id,
                target_collection_name="Scope Change Alpha",
                workspace_id=ws_alpha["workspace_id"],
            )
        )
        await session.commit()
    return tc_id


@pytest_asyncio.fixture
async def _global_collection(async_session_factory):
    """Per-test global collection for scope-change mutations."""
    tc_id = gen_id()
    async with async_session_factory() as session:
        session.add(
            TargetCollection(
                target_collection_id=tc_id,
                target_collection_name="Scope Change Global",
                workspace_id=None,
            )
        )
        await session.commit()
    return tc_id


@pytest.mark.asyncio
async def test_scope_change_workspace_to_global_as_editor_forbidden(
    editor_client, _alpha_collection
):
    """Editor cannot move a workspace collection to global (requires admin+)."""
    resp = await editor_client.patch(
        f"/api/target/collections/{_alpha_collection}",
        json={"target_collection_name": "Scope Change Alpha", "workspace_id": None},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_scope_change_workspace_to_global_as_admin(
    admin_client, _alpha_collection
):
    """Admin can move a workspace collection to global scope."""
    resp = await admin_client.patch(
        f"/api/target/collections/{_alpha_collection}",
        json={"target_collection_name": "Scope Change Alpha", "workspace_id": None},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["workspace_id"] is None


@pytest.mark.asyncio
async def test_scope_change_global_to_workspace_as_editor(
    editor_client, _global_collection, ws_alpha
):
    """Editor cannot mutate a global collection (requires admin+ for current scope)."""
    resp = await editor_client.patch(
        f"/api/target/collections/{_global_collection}",
        json={
            "target_collection_name": "Scope Change Global",
            "workspace_id": ws_alpha["workspace_id"],
        },
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_scope_change_global_to_workspace_as_admin(
    admin_client, _global_collection, ws_alpha
):
    """Admin can move a global collection into a workspace they belong to."""
    resp = await admin_client.patch(
        f"/api/target/collections/{_global_collection}",
        json={
            "target_collection_name": "Scope Change Global",
            "workspace_id": ws_alpha["workspace_id"],
        },
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["workspace_id"] == ws_alpha["workspace_id"]


@pytest.mark.asyncio
async def test_scope_change_to_non_member_workspace_forbidden(
    editor_client, _alpha_collection, ws_beta
):
    """Editor cannot move collection to a workspace they are not a member of."""
    resp = await editor_client.patch(
        f"/api/target/collections/{_alpha_collection}",
        json={
            "target_collection_name": "Scope Change Alpha",
            "workspace_id": ws_beta["workspace_id"],
        },
    )
    assert resp.status_code == 403


# ============= PATCH scope change — validate_scope_change =============


@pytest.mark.asyncio
async def test_scope_change_blocked_by_out_of_scope_batches(
    admin_client, async_session_factory, ws_alpha, ws_beta, beta_batch
):
    """Moving a collection to alpha is blocked when it has batches in beta."""
    tc_id = gen_id()
    async with async_session_factory() as session:
        session.add(
            TargetCollection(
                target_collection_id=tc_id,
                target_collection_name="Cross-WS Batches",
                workspace_id=None,
            )
        )
        session.add(
            TargetCollectionInSampleBatch(
                target_collection_id=tc_id,
                sample_batch_id=beta_batch,
            )
        )
        await session.commit()

    resp = await admin_client.patch(
        f"/api/target/collections/{tc_id}",
        json={
            "target_collection_name": "Cross-WS Batches",
            "workspace_id": ws_alpha["workspace_id"],
        },
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_scope_change_to_global_always_allowed(
    admin_client, async_session_factory, ws_alpha, alpha_batch
):
    """Moving a workspace collection to global is always allowed,
    even when it has batch associations."""
    tc_id = gen_id()
    async with async_session_factory() as session:
        session.add(
            TargetCollection(
                target_collection_id=tc_id,
                target_collection_name="Expand to Global",
                workspace_id=ws_alpha["workspace_id"],
            )
        )
        session.add(
            TargetCollectionInSampleBatch(
                target_collection_id=tc_id,
                sample_batch_id=alpha_batch,
            )
        )
        await session.commit()

    resp = await admin_client.patch(
        f"/api/target/collections/{tc_id}",
        json={"target_collection_name": "Expand to Global", "workspace_id": None},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["workspace_id"] is None


@pytest.mark.asyncio
async def test_scope_change_allowed_when_batches_in_target_workspace(
    admin_client, async_session_factory, ws_alpha, alpha_batch
):
    """Moving a global collection to alpha is allowed when all its
    batches already belong to alpha."""
    tc_id = gen_id()
    async with async_session_factory() as session:
        session.add(
            TargetCollection(
                target_collection_id=tc_id,
                target_collection_name="Narrow to Alpha",
                workspace_id=None,
            )
        )
        session.add(
            TargetCollectionInSampleBatch(
                target_collection_id=tc_id,
                sample_batch_id=alpha_batch,
            )
        )
        await session.commit()

    resp = await admin_client.patch(
        f"/api/target/collections/{tc_id}",
        json={
            "target_collection_name": "Narrow to Alpha",
            "workspace_id": ws_alpha["workspace_id"],
        },
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["workspace_id"] == ws_alpha["workspace_id"]
