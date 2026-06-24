"""
Tests: Acquisitions workspace role — per-instrument access control.

Verifies that ``check_instrument_workspace_access(instrument, user, "editor")``
blocks users who are not editors (or above) of the specific instrument's system
workspace from creating sample files for that instrument.

The test suite uses the ``POST /api/sample/files`` (create) endpoint as a
representative mutation route.

Fixtures used:
- ``acquisitions_workspace`` — system workspace "Acquisitions test-orbion"
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
    per-instrument check lets the request through for an editor of the
    instrument's workspace.
    """
    resp = await acq_editor_client.post(
        "/api/sample/files",
        json={
            "filename": "test-orbion_editor.raw",
            "instrument": "test-orbion",
            "datetime": "2026-01-01T00:00:00",
            "datetime_utc": "2026-01-01T00:00:00Z",
            "length": 60.0,
            "range": [0, 500],
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
            "filename": "test-orbion_guest.raw",
            "instrument": "test-orbion",
            "datetime": "2026-01-01T00:00:00",
            "datetime_utc": "2026-01-01T00:00:00Z",
            "length": 60.0,
            "range": [0, 500],
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
            "filename": "test-orbion_outsider.raw",
            "instrument": "test-orbion",
            "datetime": "2026-01-01T00:00:00",
            "datetime_utc": "2026-01-01T00:00:00Z",
            "length": 60.0,
            "range": [0, 500],
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
            "filename": "test-orbion_alpha_editor.raw",
            "instrument": "test-orbion",
            "datetime": "2026-01-01T00:00:00",
            "datetime_utc": "2026-01-01T00:00:00Z",
            "length": 60.0,
            "range": [0, 500],
            "polarity": "+",
        },
    )
    assert resp.status_code == 403
