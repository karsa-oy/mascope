"""
Tests: file download access control via ``POST /api/file/download``.

Verifies that the download endpoint enforces workspace ACL through
``check_sample_file_access_bulk``, with an Acquisitions member bypass
consistent with the sample file read routes.

Fixtures used:
- ``sample_file`` — linked to ``alpha_item`` (ws_alpha, all users are members)
- ``beta_sample_file`` — linked to ``beta_item`` (ws_beta, only owner is member)
- ``orphan_sample_file`` — no sample item references
"""

import pytest


# ============= Accessible file =============


@pytest.mark.asyncio
async def test_download_accessible_file(guest_client, sample_file, alpha_item):
    """Member can download a file linked to a sample item in their workspace."""
    resp = await guest_client.post(
        "/api/file/download",
        json={"sample_file_ids": [sample_file]},
    )
    # 202 = accepted (background download started) — NOT 403
    assert resp.status_code == 202


# ============= Inaccessible file (other workspace) =============


@pytest.mark.asyncio
async def test_download_inaccessible_file(guest_client, beta_sample_file, beta_item):
    """Non-member of ws_beta cannot download beta's file."""
    resp = await guest_client.post(
        "/api/file/download",
        json={"sample_file_ids": [beta_sample_file]},
    )
    assert resp.status_code == 403


# ============= Orphan file (no sample items) =============


@pytest.mark.asyncio
async def test_download_orphan_file(guest_client, orphan_sample_file):
    """File with no sample items is inaccessible to non-Acquisitions members."""
    resp = await guest_client.post(
        "/api/file/download",
        json={"sample_file_ids": [orphan_sample_file]},
    )
    assert resp.status_code == 403


# ============= Mixed batch (one accessible, one not) =============


@pytest.mark.asyncio
async def test_download_mixed_files_forbidden(
    guest_client, sample_file, beta_sample_file, alpha_item, beta_item
):
    """If ANY file in the batch is inaccessible, the entire request is rejected."""
    resp = await guest_client.post(
        "/api/file/download",
        json={"sample_file_ids": [sample_file, beta_sample_file]},
    )
    assert resp.status_code == 403


# ============= Outsider =============


@pytest.mark.asyncio
async def test_download_as_outsider(outsider_client, sample_file, alpha_item):
    """Outsider (no workspace memberships) cannot download any file."""
    resp = await outsider_client.post(
        "/api/file/download",
        json={"sample_file_ids": [sample_file]},
    )
    assert resp.status_code == 403


# ============= Acquisitions member bypasses check =============


@pytest.mark.asyncio
async def test_download_as_acq_member(
    acq_guest_client, beta_sample_file, orphan_sample_file, beta_item
):
    """Acquisitions member can download any file, including orphaned ones."""
    resp = await acq_guest_client.post(
        "/api/file/download",
        json={"sample_file_ids": [beta_sample_file, orphan_sample_file]},
    )
    assert resp.status_code == 202


# ============= Superuser bypasses check =============


@pytest.mark.asyncio
async def test_download_as_superuser(owner_client, beta_sample_file, beta_item):
    """Superuser can download any file regardless of workspace membership."""
    resp = await owner_client.post(
        "/api/file/download",
        json={"sample_file_ids": [beta_sample_file]},
    )
    assert resp.status_code == 202
