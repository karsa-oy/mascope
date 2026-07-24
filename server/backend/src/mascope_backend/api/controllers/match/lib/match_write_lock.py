"""
Per-batch advisory locking for match-table writers.

Every writer of the match tables (the create/delete funnels in the ions /
compounds / collections / samples / isotopes controllers) serializes on a
transaction-scoped Postgres advisory lock keyed by the sample batch before
touching any rows. Without this, two concurrent flows - e.g. a double-fired
batch refresh, or a batch aggregation overlapping the upload pipeline's
per-sample aggregation - walk overlapping row sets in data-dependent orders
inside long transactions, which produced AB/BA deadlocks on match_ion in
production, and their read-then-write upserts could insert duplicate logical
rows (now also rejected by the natural-key unique constraints).

The locks are transaction-scoped (pg_advisory_xact_lock): they release
automatically on commit or rollback, so no explicit unlock or connection
management is needed. Multiple batches are locked in sorted order to keep the
acquisition order deterministic across concurrent writers.
"""

from collections.abc import Iterable

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from mascope_backend.db import SampleItem


# Namespace discriminator so these locks cannot collide with other advisory
# lock users; hashed into the first int of the two-int lock key space.
_MATCH_WRITE_LOCK_NAMESPACE = "mascope_match_write"


async def acquire_match_write_locks(
    session: AsyncSession,
    sample_item_ids: Iterable[str],
) -> None:
    """
    Acquires the per-batch match-write advisory locks for the given samples.

    Must be called inside the same session/transaction that performs the match
    writes, before any match rows are read or written; blocks until every
    concurrent writer of the same batches has committed.

    :param session: The session whose transaction takes and holds the locks.
    :type session: AsyncSession
    :param sample_item_ids: Samples whose parent batches are to be locked.
    :type sample_item_ids: Iterable[str]
    """
    sample_item_ids = set(sample_item_ids)
    if not sample_item_ids:
        return

    batch_ids = (
        (
            await session.execute(
                select(SampleItem.sample_batch_id)
                .where(SampleItem.sample_item_id.in_(sample_item_ids))
                .distinct()
            )
        )
        .scalars()
        .all()
    )
    # Sorted acquisition keeps concurrent multi-batch writers deadlock-free
    for batch_id in sorted(batch_ids):
        await session.execute(
            select(
                func.pg_advisory_xact_lock(
                    func.hashtext(_MATCH_WRITE_LOCK_NAMESPACE),
                    func.hashtext(batch_id),
                )
            )
        )
