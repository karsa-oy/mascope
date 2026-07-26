"""Tests: Socket.IO room-subscription authorization (``user_can_subscribe_to_room``).

Record-sync events broadcast full record data to rooms named after the focused
entity (sample batch, sample item, dataset, target collection, instrument) or a
private ``user-<id>`` channel. Subscription must be gated by the same workspace
read ACL as REST - regression cover for the pre-hardening state where any
authenticated user could join any room by id and receive another tenant's data.

Fixtures: ``test_users`` (all members of ws_alpha; owner is a superuser),
``outsider_user`` (member of nothing), Beta entities (only owner is a member).
"""

import pytest

from mascope_backend.api.new.workspaces.dependencies import (
    user_can_subscribe_to_room,
)


# ============= Member may join their own workspace's rooms =============


@pytest.mark.asyncio
async def test_member_can_join_own_workspace_rooms(
    test_users, alpha_batch, alpha_dataset, alpha_item
):
    guest = test_users["guest"]
    for room in (alpha_batch, alpha_dataset, alpha_item):
        assert await user_can_subscribe_to_room(room, guest) is True


@pytest.mark.asyncio
async def test_member_can_join_workspace_collection_room(
    test_users, alpha_target_collection
):
    assert (
        await user_can_subscribe_to_room(alpha_target_collection, test_users["guest"])
        is True
    )


# ============= Non-member is refused another workspace's rooms =============


@pytest.mark.asyncio
async def test_non_member_cannot_join_other_workspace_rooms(
    test_users, beta_batch, beta_dataset, beta_item
):
    # guest is a member of Alpha but NOT Beta.
    guest = test_users["guest"]
    for room in (beta_batch, beta_dataset, beta_item):
        assert await user_can_subscribe_to_room(room, guest) is False


@pytest.mark.asyncio
async def test_non_member_cannot_join_other_workspace_collection(
    test_users, beta_target_collection
):
    assert (
        await user_can_subscribe_to_room(beta_target_collection, test_users["guest"])
        is False
    )


@pytest.mark.asyncio
async def test_outsider_cannot_join_any_room(outsider_user, alpha_batch):
    assert await user_can_subscribe_to_room(alpha_batch, outsider_user) is False


# ============= Private per-user channels =============


@pytest.mark.asyncio
async def test_user_can_join_own_user_channel(test_users):
    guest = test_users["guest"]
    assert await user_can_subscribe_to_room(f"user-{guest.id}", guest) is True


@pytest.mark.asyncio
async def test_user_cannot_join_another_users_channel(test_users):
    guest = test_users["guest"]
    owner = test_users["owner"]
    # Even a superuser (owner) may not join another user's private channel.
    assert await user_can_subscribe_to_room(f"user-{owner.id}", guest) is False
    assert await user_can_subscribe_to_room(f"user-{guest.id}", owner) is False


# ============= Superuser bypass for resource rooms =============


@pytest.mark.asyncio
async def test_superuser_can_join_any_resource_room(test_users, beta_batch):
    # owner is a superuser and not a Beta member, but still may join.
    assert await user_can_subscribe_to_room(beta_batch, test_users["owner"]) is True


# ============= Global collection readable by any authenticated user =============


@pytest.mark.asyncio
async def test_any_user_can_join_global_collection_room(
    outsider_user, global_target_collection
):
    assert (
        await user_can_subscribe_to_room(global_target_collection, outsider_user)
        is True
    )


# ============= Instrument workspace rooms =============


@pytest.mark.asyncio
async def test_instrument_member_can_join_instrument_room(
    acq_guest_user, acquisitions_workspace
):
    # Instrument rooms are the instrument name; acq_guest_user is a member.
    assert await user_can_subscribe_to_room("test-orbion", acq_guest_user) is True


@pytest.mark.asyncio
async def test_non_instrument_member_cannot_join_instrument_room(
    test_users, acquisitions_workspace
):
    # guest is not a member of the Acquisitions workspace.
    assert await user_can_subscribe_to_room("test-orbion", test_users["guest"]) is False


# ============= Unknown room denied (fail closed) =============


@pytest.mark.asyncio
async def test_unknown_room_denied(test_users):
    assert (
        await user_can_subscribe_to_room("does-not-exist-xyz", test_users["guest"])
        is False
    )
