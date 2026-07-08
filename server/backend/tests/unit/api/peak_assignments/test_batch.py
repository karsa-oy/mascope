"""
Unit tests for the batch-level peak assignment orchestrator.

Verify that ``assign_sample_batch_peaks`` sequences every sample in a batch,
isolates per-sample failures (one bad sample never aborts the rest), and
aggregates a batch status. All external dependencies are mocked - no DB, file
I/O, or Socket.IO required (mirrors test_auto_process.py).
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# Module path prefixes for patching
_MOD = "mascope_backend.api.new.peak_assignments.batch"
_NOTIF = "mascope_backend.socket.notifications"
_UTILS = "mascope_backend.api.lib.utils"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_sample(sample_item_id, name=None):
    s = MagicMock()
    s.sample_item_id = sample_item_id
    s.sample_item_name = name or sample_item_id
    return s


def _make_batch(name="Test Batch"):
    b = MagicMock()
    b.sample_batch_name = name
    return b


def _session_returning(samples):
    """Build an async_session() context manager whose query yields ``samples``."""
    scalars = MagicMock()
    scalars.all.return_value = samples
    exec_result = MagicMock()
    exec_result.scalars.return_value = scalars

    session = AsyncMock()
    session.execute = AsyncMock(return_value=exec_result)

    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx


def _base_patches(samples, batch=None):
    """Patches common to every test."""
    return {
        "fetch_batch": patch(f"{_MOD}.fetch_sample_batch", new_callable=AsyncMock),
        "assign": patch(f"{_MOD}.assign_sample_peaks", new_callable=AsyncMock),
        "async_session": patch(f"{_MOD}.async_session"),
        "progress": patch(
            f"{_MOD}.send_progress_user_notification", new_callable=AsyncMock
        ),
        "handle_notifications": patch(
            f"{_NOTIF}.handle_notifications", new_callable=AsyncMock
        ),
        "handle_reloads": patch(f"{_UTILS}.handle_reloads", new_callable=AsyncMock),
    }


def _start(patches, samples, batch=None):
    mocks = {k: p.start() for k, p in patches.items()}
    mocks["fetch_batch"].return_value = batch or _make_batch()
    mocks["async_session"].return_value = _session_returning(samples)
    return mocks


@pytest.fixture(autouse=True)
def _stop_all_patches():
    yield
    patch.stopall()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_assigns_every_sample_in_batch():
    """One assignment run is launched per sample; status is success."""
    from mascope_backend.api.new.peak_assignments.batch import (
        assign_sample_batch_peaks,
    )

    samples = [_make_sample(f"si-{i}") for i in range(3)]
    patches = _base_patches(samples)
    mocks = _start(patches, samples)
    mocks["assign"].return_value = {"status": "success"}

    result = await assign_sample_batch_peaks(
        sample_batch_id="batch-1",
        independent_transaction=True,
        user_id=42,
        process_id="proc-1",
    )

    assert mocks["assign"].call_count == 3
    assert result["status"] == "success"
    assert result["data"]["assigned_samples_count"] == 3
    assert result["data"]["failed_samples_count"] == 0
    assert result["_notification_data"]["sample_batch_id"] == "batch-1"


@pytest.mark.asyncio
async def test_isolates_per_sample_failure():
    """A single failing sample does not abort assignment for the rest."""
    from mascope_backend.api.new.peak_assignments.batch import (
        assign_sample_batch_peaks,
    )

    samples = [_make_sample(f"si-{i}") for i in range(3)]
    patches = _base_patches(samples)
    mocks = _start(patches, samples)
    mocks["assign"].side_effect = [
        RuntimeError("corrupt file"),
        {"status": "success"},
        {"status": "success"},
    ]

    result = await assign_sample_batch_peaks(
        sample_batch_id="batch-1",
        independent_transaction=True,
        user_id=42,
        process_id="proc-1",
    )

    # All three samples were attempted despite the first raising
    assert mocks["assign"].call_count == 3
    assert result["status"] == "partial"
    assert result["data"]["assigned_samples_count"] == 2
    assert result["data"]["failed_samples_count"] == 1


@pytest.mark.asyncio
async def test_blank_samples_are_skipped():
    """Samples the engine skips (blank/no peaks) count as skipped, not assigned."""
    from mascope_backend.api.new.peak_assignments.batch import (
        assign_sample_batch_peaks,
    )

    samples = [_make_sample(f"si-{i}") for i in range(2)]
    patches = _base_patches(samples)
    mocks = _start(patches, samples)
    mocks["assign"].return_value = {"status": "skipped"}

    result = await assign_sample_batch_peaks(
        sample_batch_id="batch-1",
        independent_transaction=True,
        user_id=42,
        process_id="proc-1",
    )

    assert result["status"] == "skipped"
    assert result["data"]["skipped_samples_count"] == 2
    assert result["data"]["assigned_samples_count"] == 0


@pytest.mark.asyncio
async def test_empty_batch_skips_without_assigning():
    """A batch with no samples is skipped and never calls the engine."""
    from mascope_backend.api.new.peak_assignments.batch import (
        assign_sample_batch_peaks,
    )

    patches = _base_patches([])
    mocks = _start(patches, [])

    result = await assign_sample_batch_peaks(
        sample_batch_id="batch-1",
        independent_transaction=True,
        user_id=42,
        process_id="proc-1",
    )

    mocks["assign"].assert_not_called()
    assert result["status"] == "skipped"
    assert result["data"]["total_samples_count"] == 0
