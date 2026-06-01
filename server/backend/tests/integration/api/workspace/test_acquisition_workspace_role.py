"""
Tests: Acquisitions workspace role dependency.

Verifies that ``require_acquisition_workspace_role("editor")`` blocks users who
are not editors (or above) of the system "Acquisitions" workspace from mutating
sample files.

The test suite uses the ``POST /api/sample/files`` (create) endpoint as a
representative mutation route.  The dependency is identical on all mutation
routes so testing one is sufficient.

Fixtures used:
- ``acquisitions_workspace`` — system workspace with ``is_system=True``
- ``acq_editor_client`` — user who IS an editor of the Acquisitions workspace
- ``acq_guest_client`` — user who IS a guest of the Acquisitions workspace
- ``outsider_client`` — user with no workspace memberships
"""

import pytest


# ============= Mutation allowed for Acquisitions editor =============


@pytest.mark.asyncio
async def test_create_file_as_acquisitions_editor(acq_editor_client):
    """Acquisitions editor can hit the create endpoint (ACL passes).

    We expect 409 (duplicate) or 201 — NOT 403.  The point is that the
    ``require_acquisition_workspace_role("editor")`` dependency lets the
    request through.
    """
    resp = await acq_editor_client.post(
        "/api/sample/files",
        json={
            "filename": "acq_test_editor.h5",
            "instrument": "test-instrument",
            "datetime": "2026-01-01T00:00:00",
            "datetime_utc": "2026-01-01T00:00:00Z",
            "length": 60.0,
            "range": {"min": 0, "max": 500},
            "polarity": "+",
        },
    )
    # 201 = created; 409 = duplicate filename; 500 = background processing issue
    # The key assertion: NOT 403
    assert resp.status_code != 403


# ============= Mutation blocked for Acquisitions guest =============


@pytest.mark.asyncio
async def test_create_file_as_acquisitions_guest_forbidden(acq_guest_client):
    """Acquisitions guest cannot create files (requires editor)."""
    resp = await acq_guest_client.post(
        "/api/sample/files",
        json={
            "filename": "acq_test_guest.h5",
            "instrument": "test-instrument",
            "datetime": "2026-01-01T00:00:00",
            "datetime_utc": "2026-01-01T00:00:00Z",
            "length": 60.0,
            "range": {"min": 0, "max": 500},
            "polarity": "+",
        },
    )
    assert resp.status_code == 403


# ============= Mutation blocked for outsider =============


@pytest.mark.asyncio
async def test_create_file_as_outsider_forbidden(outsider_client):
    """User with no workspace memberships cannot create files."""
    resp = await outsider_client.post(
        "/api/sample/files",
        json={
            "filename": "acq_test_outsider.h5",
            "instrument": "test-instrument",
            "datetime": "2026-01-01T00:00:00",
            "datetime_utc": "2026-01-01T00:00:00Z",
            "length": 60.0,
            "range": {"min": 0, "max": 500},
            "polarity": "+",
        },
    )
    assert resp.status_code == 403


# ============= Mutation blocked for non-acquisitions workspace member =============


@pytest.mark.asyncio
async def test_create_file_as_alpha_editor_forbidden(editor_client):
    """Editor of ws_alpha (but NOT Acquisitions workspace) cannot create files."""
    resp = await editor_client.post(
        "/api/sample/files",
        json={
            "filename": "acq_test_alpha_editor.h5",
            "instrument": "test-instrument",
            "datetime": "2026-01-01T00:00:00",
            "datetime_utc": "2026-01-01T00:00:00Z",
            "length": 60.0,
            "range": {"min": 0, "max": 500},
            "polarity": "+",
        },
    )
    assert resp.status_code == 403
