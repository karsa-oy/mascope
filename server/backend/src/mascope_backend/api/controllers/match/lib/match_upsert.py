"""
Bulk natural-key upserts for the match aggregate tables.

The create funnels (ions / compounds / collections / samples) all follow the
same shape: write the aggregation's rows for a level, creating missing rows,
updating rows whose values changed and leaving identical rows untouched.
Historically this was a read-then-diff loop over ORM objects - one SELECT per
sample plus one flushed UPDATE/INSERT per row - which dominated aggregation
wall time on large batches. With the natural-key unique constraints in place
(migration a1c9f4e7d2b8) each level is now a batched
``INSERT ... ON CONFLICT DO UPDATE ... WHERE row IS DISTINCT FROM excluded``:

- missing rows are inserted,
- conflicting rows are updated only when a value differs (the WHERE guard
  keeps unchanged rows lock- and WAL-free, preserving their utc_modified),
- RETURNING with ``xmax = 0`` distinguishes inserts from updates, so the
  funnels keep their created/updated/unchanged reporting.

One Postgres nuance versus the old Python ``!=`` diff: Postgres treats two
NaN floats as not distinct, so a NaN value no longer re-updates its row on
every pass (the old comparison churned forever - an improvement, not a
regression).

Callers hold the per-batch advisory write lock (acquire_match_write_locks)
for the whole transaction, so concurrent writers serialize before any row
lock is taken.
"""

from collections.abc import Sequence
from datetime import datetime, timezone

from pydantic import BaseModel
from sqlalchemy import literal_column
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from mascope_backend.db.id import gen_id


async def bulk_upsert_match_level(
    session: AsyncSession,
    model: type,
    id_column: str,
    natural_key: Sequence[str],
    value_columns: Sequence[str],
    utc_created_column: str,
    utc_modified_column: str,
    rows: Sequence[BaseModel],
) -> tuple[int, int, list[dict]]:
    """
    Upserts one match level's rows on its natural key.

    Deduplicates the input on the natural key keeping the last occurrence
    (duplicate keys in one INSERT would error; last-wins matches the old
    sequential behavior) and processes in sorted natural-key order so
    concurrent writers touch rows in the same sequence.

    :param session: Session holding the per-batch advisory write lock.
    :type session: AsyncSession
    :param model: The match table's ORM model.
    :type model: type
    :param id_column: Name of the primary key column (filled with gen_id(32)).
    :type id_column: str
    :param natural_key: Column names of the level's natural key.
    :type natural_key: Sequence[str]
    :param value_columns: Value columns compared and updated on conflict.
    :type value_columns: Sequence[str]
    :param utc_created_column: Timestamp column set on insert.
    :type utc_created_column: str
    :param utc_modified_column: Timestamp column set on value-changing update.
    :type utc_modified_column: str
    :param rows: The level's pydantic rows to write.
    :type rows: Sequence[BaseModel]
    :return: (created_count, updated_count, changed_rows) where changed_rows
        are dicts of the written key + value columns (unchanged rows are not
        included - they were not written).
    :rtype: tuple[int, int, list[dict]]
    """
    utc_now = datetime.now(timezone.utc)

    deduped = {
        tuple(getattr(row, column) for column in natural_key): row for row in rows
    }
    ordered_rows = [deduped[key] for key in sorted(deduped)]

    # One statement compiled once; executemany parameters ride SQLAlchemy's
    # insertmanyvalues, which pages the VALUES lists efficiently (building a
    # multi-row .values() expression instead would re-compile a huge tree per
    # page - measurably slower at this scale).
    insert_stmt = pg_insert(model)
    excluded = insert_stmt.excluded
    differs = None
    for column in value_columns:
        condition = getattr(model, column).is_distinct_from(excluded[column])
        differs = condition if differs is None else differs | condition
    upsert_stmt = insert_stmt.on_conflict_do_update(
        index_elements=list(natural_key),
        set_={
            **{column: excluded[column] for column in value_columns},
            utc_modified_column: utc_now,
        },
        where=differs,
    ).returning(
        getattr(model, id_column),
        *(getattr(model, column) for column in (*natural_key, *value_columns)),
        # xmax = 0 marks a freshly inserted row; nonzero marks an update
        literal_column("(xmax = 0)").label("_inserted"),
    )

    params = [
        {
            id_column: gen_id(32),
            **row.model_dump(),
            utc_created_column: utc_now,
        }
        for row in ordered_rows
    ]
    result = await session.execute(upsert_stmt, params)

    created_count = 0
    updated_count = 0
    changed_rows: list[dict] = []
    for returned in result.mappings():
        if returned["_inserted"]:
            created_count += 1
        else:
            updated_count += 1
        changed_rows.append(
            {key: value for key, value in returned.items() if key != "_inserted"}
        )

    return created_count, updated_count, changed_rows
