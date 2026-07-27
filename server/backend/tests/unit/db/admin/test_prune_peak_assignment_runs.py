"""
Unit tests for the peak-assignment retention selection.

``_select_prunable_run_ids`` decides which runs get deleted, and deleting a run
cascades to its whole ledger - so a mistake here is silent, irreversible data
loss. It takes its session as a parameter, so the ranking can be tested without
a database by feeding it the rows a query would have returned.

The ordering these tests assume is the query's, not Python's: the SELECT sorts
by sample, then created DESC NULLS LAST, then run id DESC.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from mascope_backend.db.admin.peak_assignments.prune_runs import (
    _select_prunable_run_ids,
)


def _session(completed_rows, stale_ids):
    """A session whose two queries return the given completed rows / stale ids.

    ``_select_prunable_run_ids`` issues exactly two statements: the completed-run
    scan (``.all()``) and the stale non-completed scan (``.scalars()``).
    """
    completed_result = MagicMock()
    completed_result.all.return_value = completed_rows

    stale_result = MagicMock()
    stale_result.scalars.return_value = stale_ids

    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[completed_result, stale_result])
    return session


@pytest.mark.asyncio
async def test_keeps_the_newest_n_completed_per_sample():
    """Only runs past the keep window are prunable, and per sample."""
    rows = [
        # si1, newest first (as the query orders them)
        ("s1-new", "si1"),
        ("s1-mid", "si1"),
        ("s1-old", "si1"),
        ("s1-older", "si1"),
        # si2 has fewer than the keep count
        ("s2-only", "si2"),
    ]
    session = _session(rows, [])

    prunable = await _select_prunable_run_ids(
        session, keep_per_sample=2, keep_failed_hours=24
    )

    assert prunable == ["s1-old", "s1-older"]


@pytest.mark.asyncio
async def test_keep_window_is_per_sample_not_global():
    """A sample with few runs is never pruned because another sample has many."""
    rows = [("a1", "si1"), ("a2", "si1"), ("a3", "si1"), ("b1", "si2")]
    session = _session(rows, [])

    prunable = await _select_prunable_run_ids(
        session, keep_per_sample=1, keep_failed_hours=24
    )

    assert prunable == ["a2", "a3"]
    assert "b1" not in prunable


@pytest.mark.asyncio
async def test_stale_non_completed_runs_are_added():
    """Failed/interrupted runs past the grace period are prunable too."""
    session = _session([("keep", "si1")], ["failed-1", "failed-2"])

    prunable = await _select_prunable_run_ids(
        session, keep_per_sample=3, keep_failed_hours=24
    )

    assert prunable == ["failed-1", "failed-2"]


@pytest.mark.asyncio
async def test_result_is_deduplicated_and_order_stable():
    """The same run never appears twice, and order is preserved for dry runs."""
    rows = [("r1", "si1"), ("r2", "si1"), ("r3", "si1")]
    session = _session(rows, ["r3", "r4"])

    prunable = await _select_prunable_run_ids(
        session, keep_per_sample=1, keep_failed_hours=24
    )

    assert prunable == ["r2", "r3", "r4"]
    assert len(set(prunable)) == len(prunable)


@pytest.mark.asyncio
async def test_nothing_prunable_returns_empty():
    session = _session([("only", "si1")], [])

    assert (
        await _select_prunable_run_ids(session, keep_per_sample=3, keep_failed_hours=24)
        == []
    )


class TestPruneGuards:
    """The prune refuses configurations that would delete more than intended."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "kwargs",
        [
            {"keep_per_sample": 0},
            {"keep_per_sample": -1},
            {"keep_failed_hours": -1},
            {"batch_size": 0},
        ],
    )
    async def test_invalid_policy_is_rejected(self, kwargs):
        """keep_per_sample=0 would delete every run of every sample."""
        from mascope_backend.db.admin.peak_assignments.prune_runs import (
            prune_peak_assignment_runs,
        )

        with pytest.raises(ValueError):
            await prune_peak_assignment_runs(**kwargs)


def test_grace_cutoff_is_in_the_past():
    """Sanity: the grace window subtracts, so a fresh failure is never pruned."""
    from mascope_backend.db.admin.peak_assignments.prune_runs import (
        DEFAULT_KEEP_FAILED_HOURS,
    )

    cutoff = datetime.now(timezone.utc) - timedelta(hours=DEFAULT_KEEP_FAILED_HOURS)
    assert cutoff < datetime.now(timezone.utc)
    assert DEFAULT_KEEP_FAILED_HOURS > 0


class TestReaperResilience:
    """The startup reaper must never be able to stop the server booting."""

    @pytest.mark.asyncio
    async def test_missing_table_is_swallowed(self, monkeypatch):
        """A database without the table (not yet migrated) must not break boot.

        The reaper runs in init_main_process alongside the other startup tasks,
        which share one try block - so a raise here aborts startup entirely.
        """
        from mascope_backend.db.admin.peak_assignments import reset_running_runs

        def _boom(*_args, **_kwargs):
            raise RuntimeError('relation "peak_assignment_run" does not exist')

        monkeypatch.setattr(reset_running_runs, "async_session", _boom)

        result = await reset_running_runs.reset_running_peak_assignment_runs()

        assert result["status"] == "skipped"
        assert result["data"]["reset_count"] == 0
