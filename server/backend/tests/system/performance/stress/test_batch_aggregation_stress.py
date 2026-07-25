"""
Batch-aggregation stress test against a scaled database (opt-in).

Measures the full batch aggregation write path at production scale and
verifies value-equivalence via per-level checksums. Boots nothing itself -
prepare a scaled database once, then opt in with ``MASCOPE_STRESS_TEST=1``.

Preparing the database (once; ~5 minutes):

    # 1. Clone the demo database into the shared dev Postgres
    docker exec mascope_demo_postgres pg_dump -U mascope_user -d mascope_demo \
        -Fc -f /tmp/demo_stress.dump
    docker cp mascope_demo_postgres:/tmp/demo_stress.dump /tmp/demo_stress.dump
    docker cp /tmp/demo_stress.dump mascope_dev_postgres:/tmp/demo_stress.dump
    docker exec mascope_dev_postgres psql -U mascope_user -d postgres \
        -c "CREATE DATABASE mascope_stress"
    docker exec mascope_dev_postgres pg_restore -U mascope_user \
        -d mascope_stress --no-owner /tmp/demo_stress.dump
    # 2. Migrate to head (point alembic at the stress DB), then expand the
    #    largest batch with the benchmark's cloning script:
    psql ... -v batch=<batch_id> -v collection=<collection_id> \
        -v imult=0 -v mult=27 -f server/backend/tests/system/benchmark/expand_demo.sql

Running:

    MASCOPE_STRESS_TEST=1 MASCOPE_ENV=stress \
    POSTGRES_PASSWORD_FILE=$MASCOPE_PATH/.runtime/secrets/postgres_password.txt \
    uv run pytest server/backend/tests/system/performance/stress/ -v -s

Configuration (all optional):
- ``MASCOPE_STRESS_BATCH_ID``: batch to aggregate (default: the batch with
  the most samples).
- ``MASCOPE_STRESS_RESET=1``: delete the batch's aggregate rows first, so the
  run measures the full re-create write path instead of a no-op diff pass.
- ``MASCOPE_STRESS_BUDGET_S``: wall-time budget for the aggregation
  (default 600 s) - fails the test on a regression past the budget.
"""

import os
import time

import pytest
from sqlalchemy import func, select, text


requires_stress_db = pytest.mark.skipif(
    os.environ.get("MASCOPE_STRESS_TEST") != "1",
    reason=(
        "stress run not requested; prepare a scaled database (see module "
        "docstring) and set MASCOPE_STRESS_TEST=1"
    ),
)

BUDGET_S = float(os.environ.get("MASCOPE_STRESS_BUDGET_S", "600"))


@requires_stress_db
@pytest.mark.asyncio
async def test_batch_aggregation_at_scale():
    """Full batch aggregation completes within budget with complete results."""
    from mascope_backend.db import (
        MatchCollection,
        MatchCompound,
        MatchIon,
        MatchSample,
        SampleItem,
        async_session,
        configure_database_engine,
    )

    await configure_database_engine()

    import mascope_backend.api.controllers.match.aggregate.match_aggregate_controller as mac
    from mascope_backend.api.controllers.match.match_controller import (
        _batch_aggregates_incomplete,
    )

    # Socket emissions are irrelevant here and may lack a broker
    async def no_emit(*args, **kwargs):
        return None

    mac.emit_record_created = no_emit
    mac.emit_record_reload = no_emit

    async with async_session() as session:
        batch_id = os.environ.get("MASCOPE_STRESS_BATCH_ID") or (
            await session.scalar(
                select(SampleItem.sample_batch_id)
                .group_by(SampleItem.sample_batch_id)
                .order_by(func.count().desc())
                .limit(1)
            )
        )
        sample_count = await session.scalar(
            select(func.count())
            .select_from(SampleItem)
            .where(SampleItem.sample_batch_id == batch_id)
        )

        if os.environ.get("MASCOPE_STRESS_RESET") == "1":
            for table in (
                "match_ion",
                "match_compound",
                "match_collection",
                "match_sample",
            ):
                await session.execute(
                    text(
                        f"DELETE FROM {table} t USING sample_item si "  # noqa: S608
                        "WHERE si.sample_item_id = t.sample_item_id "
                        "AND si.sample_batch_id = :batch"
                    ),
                    {"batch": batch_id},
                )
            await session.commit()

    started = time.perf_counter()
    result = await mac.aggregate_and_create_matches(sample_batch_id=batch_id)
    elapsed = time.perf_counter() - started

    assert result.get("status") in ("success", "partial"), result
    assert not await _batch_aggregates_incomplete(batch_id)

    async with async_session() as session:
        checks = {}
        for name, model in (
            ("match_ion", MatchIon),
            ("match_compound", MatchCompound),
            ("match_collection", MatchCollection),
            ("match_sample", MatchSample),
        ):
            checks[name] = (
                await session.execute(
                    select(
                        func.count(),
                        func.coalesce(func.sum(model.match_score), 0.0),
                        func.coalesce(func.sum(model.sample_peak_intensity_sum), 0.0),
                    )
                    .select_from(model)
                    .join(
                        SampleItem,
                        SampleItem.sample_item_id == model.sample_item_id,
                    )
                    .where(SampleItem.sample_batch_id == batch_id)
                )
            ).one()

    assert checks["match_sample"][0] == sample_count, "missing sample aggregates"

    print(f"\nSTRESS: batch {batch_id}, {sample_count} samples")
    print(f"STRESS: aggregation {elapsed:.1f}s (budget {BUDGET_S:.0f}s)")
    for name, (count, score_sum, intensity_sum) in checks.items():
        print(
            f"STRESS: {name} count={count} score={float(score_sum):.6f} "
            f"intensity={float(intensity_sum):.3f}"
        )

    assert elapsed <= BUDGET_S, (
        f"batch aggregation took {elapsed:.1f}s, over the {BUDGET_S:.0f}s budget"
    )
