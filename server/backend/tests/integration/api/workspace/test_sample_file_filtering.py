"""
Tests: Sample file list filtering by workspace membership.

Verifies that GET /api/sample/files returns only files linked to sample items
in workspaces where the user is a member.  The controller's ``user_id`` EXISTS
subquery is the mechanism under test.

Acquisitions workspace members bypass the filter and see all files, including
orphaned files with no sample items.

Fixtures used:
- ``sample_file`` — linked to ``alpha_item`` (ws_alpha, all users are members)
- ``beta_sample_file`` — linked to ``beta_item`` (ws_beta, only owner is member)
- ``orphan_sample_file`` — no sample item references at all
"""

import pytest


# ============= Filtered list (non-Acquisitions member) =============


@pytest.mark.asyncio
async def test_list_files_member_sees_own_workspace_files(
    guest_client, sample_file, alpha_item
):
    """Guest (member of ws_alpha) sees the file linked to alpha_item."""
    resp = await guest_client.get("/api/sample/files")
    assert resp.status_code == 200
    file_ids = [f["sample_file_id"] for f in resp.json()["data"]]
    assert sample_file in file_ids


@pytest.mark.asyncio
async def test_list_files_member_does_not_see_other_workspace_files(
    guest_client, beta_sample_file, beta_item
):
    """Guest (not a member of ws_beta) does NOT see beta's file."""
    resp = await guest_client.get("/api/sample/files")
    assert resp.status_code == 200
    file_ids = [f["sample_file_id"] for f in resp.json()["data"]]
    assert beta_sample_file not in file_ids


@pytest.mark.asyncio
async def test_list_files_outsider_sees_nothing(outsider_client):
    """Outsider (no workspace memberships) gets an empty list."""
    resp = await outsider_client.get("/api/sample/files")
    assert resp.status_code == 200
    assert resp.json()["data"] == []


@pytest.mark.asyncio
async def test_list_files_orphan_file_hidden_for_non_acq_member(
    guest_client, orphan_sample_file
):
    """A file with no sample items is invisible to non-Acquisitions members."""
    resp = await guest_client.get("/api/sample/files")
    assert resp.status_code == 200
    file_ids = [f["sample_file_id"] for f in resp.json()["data"]]
    assert orphan_sample_file not in file_ids


# ============= Acquisitions members see all files =============


@pytest.mark.asyncio
async def test_list_files_acq_member_sees_all(
    acq_guest_client, sample_file, beta_sample_file, orphan_sample_file
):
    """Acquisitions guest sees all files including orphaned ones."""
    resp = await acq_guest_client.get("/api/sample/files")
    assert resp.status_code == 200
    file_ids = [f["sample_file_id"] for f in resp.json()["data"]]
    assert sample_file in file_ids
    assert beta_sample_file in file_ids
    assert orphan_sample_file in file_ids


@pytest.mark.asyncio
async def test_list_files_superuser_sees_all(
    owner_client, sample_file, beta_sample_file, orphan_sample_file
):
    """Superuser (owner) bypasses filtering and sees every file."""
    resp = await owner_client.get("/api/sample/files")
    assert resp.status_code == 200
    file_ids = [f["sample_file_id"] for f in resp.json()["data"]]
    assert sample_file in file_ids
    assert beta_sample_file in file_ids
    assert orphan_sample_file in file_ids


# ============= Single file access =============


@pytest.mark.asyncio
async def test_get_file_as_member(guest_client, sample_file, alpha_item):
    """Member can read a file linked to a sample item in their workspace."""
    resp = await guest_client.get(f"/api/sample/files/{sample_file}")
    assert resp.status_code == 200
    assert resp.json()["data"]["sample_file_id"] == sample_file


@pytest.mark.asyncio
async def test_get_file_as_outsider(outsider_client, sample_file, alpha_item):
    """Non-member cannot read a file even if they know the ID."""
    resp = await outsider_client.get(f"/api/sample/files/{sample_file}")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_get_beta_file_as_nonmember(guest_client, beta_sample_file, beta_item):
    """Guest (not a member of ws_beta) cannot read beta's file."""
    resp = await guest_client.get(f"/api/sample/files/{beta_sample_file}")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_get_orphan_file_as_acq_member(acq_guest_client, orphan_sample_file):
    """Acquisitions member can read an orphaned file with no sample items."""
    resp = await acq_guest_client.get(f"/api/sample/files/{orphan_sample_file}")
    assert resp.status_code == 200
    assert resp.json()["data"]["sample_file_id"] == orphan_sample_file


@pytest.mark.asyncio
async def test_get_beta_file_as_acq_member(acq_guest_client, beta_sample_file):
    """Acquisitions member can read any file regardless of workspace ownership."""
    resp = await acq_guest_client.get(f"/api/sample/files/{beta_sample_file}")
    assert resp.status_code == 200
    assert resp.json()["data"]["sample_file_id"] == beta_sample_file
