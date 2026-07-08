"""
Unit tests for the auto-processing peak-assignment hook.

``auto_assign_sample_peaks`` is what the sample auto-processing pipeline calls.
These verify the two properties that matter for the hot path: it runs the engine
Stage-A only (``run_untargeted=False``) and it never lets an assignment failure
escape into the processing lifecycle.
"""

from unittest.mock import AsyncMock, patch

import pytest


_SVC = "mascope_backend.api.new.peak_assignments.service"


@pytest.mark.asyncio
async def test_runs_stage_a_only():
    """The auto hook drives the engine database-first only, nested under parent."""
    from mascope_backend.api.new.peak_assignments.service import (
        auto_assign_sample_peaks,
    )

    with patch(f"{_SVC}.assign_sample_peaks", new_callable=AsyncMock) as assign:
        await auto_assign_sample_peaks(
            sample_item_id="si-1", user_id=42, parent_id="proc-1"
        )

    assign.assert_called_once()
    kwargs = assign.call_args.kwargs
    # Stage-A only: untargeted (Stage B) enumeration is off on the hot path
    assert kwargs["config"].run_untargeted is False
    # Runs nested so the parent orchestrator owns reloads / avoids toast spam
    assert kwargs["independent_transaction"] is False
    assert kwargs["parent_id"] == "proc-1"
    assert kwargs["user_id"] == 42


@pytest.mark.asyncio
async def test_swallows_engine_failure():
    """An assignment failure is logged and never propagated to auto-processing."""
    from mascope_backend.api.new.peak_assignments.service import (
        auto_assign_sample_peaks,
    )

    with patch(f"{_SVC}.assign_sample_peaks", new_callable=AsyncMock) as assign:
        assign.side_effect = RuntimeError("boom")
        # Must not raise
        await auto_assign_sample_peaks(sample_item_id="si-1", user_id=42)

    assign.assert_called_once()
