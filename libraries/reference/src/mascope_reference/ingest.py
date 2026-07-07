"""Versioned ingestion of a source dump into the reference mirror.

Each ingest is one versioned load: it records a new ``reference_source`` row,
streams the adapter's records through :func:`normalize.finalize`, and bulk
inserts them as ``reference_compound`` rows pointing at that source row. The
new load becomes the active version of its source and any prior active load of
the same source is deactivated, so queries see exactly one version per source
while older loads stay on disk for reproducibility (``prune=True`` drops them).

Runs against a synchronous SQLAlchemy engine - it is driven by the CLI, off the
request path, and streams so a multi-gigabyte dump never lands in memory.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from sqlalchemy import delete, insert, update
from sqlalchemy.engine import Engine

from mascope_reference.adapters.base import Adapter
from mascope_reference.normalize import finalize
from mascope_reference.record import ReferenceRecord
from mascope_reference.schema import (
    COMPOUND_INSERT_COLUMNS,
    reference_compound,
    reference_source,
)


DEFAULT_BATCH_SIZE = 5000


@dataclass
class IngestResult:
    """Outcome of one ingest load."""

    source: str
    version: str
    reference_source_id: int
    ingested: int
    skipped: int


def _compound_row(source_id: int, record: ReferenceRecord) -> dict:
    """Build a ``reference_compound`` insert dict from a finalized record."""
    record_columns = set(COMPOUND_INSERT_COLUMNS) - {"reference_source_id"}
    data = record.model_dump(include=record_columns)
    data["reference_source_id"] = source_id
    return data


def _finalized_rows(
    adapter: Adapter, path: Path, source_id: int
) -> Iterator[tuple[dict | None, bool]]:
    """Yield (insert_dict, skipped) for each raw record from the adapter."""
    for raw in adapter.parse(path):
        record = finalize(raw)
        if record is None:
            # Formula had no parseable elements - no usable annotation key.
            yield None, True
        else:
            yield _compound_row(source_id, record), False


def ingest(
    engine: Engine,
    adapter: Adapter,
    path: Path,
    version: str,
    *,
    source_name: str | None = None,
    batch_size: int = DEFAULT_BATCH_SIZE,
    activate: bool = True,
    prune: bool = False,
    progress: Callable[[int], None] | None = None,
) -> IngestResult:
    """Ingest one source dump as a new versioned load.

    :param engine: Synchronous SQLAlchemy engine for the target database.
    :param adapter: Source adapter resolved from the registry.
    :param path: Path to the downloaded dump.
    :param version: Version tag for this load (release date/tag), for
        reproducibility and provenance.
    :param source_name: Provenance name for this load, overriding the adapter's.
        Lets several loads of a generic adapter (e.g. ``custom``) coexist as
        distinct sources instead of replacing one another. Defaults to
        ``adapter.name``.
    :param batch_size: Rows per bulk insert.
    :param activate: Mark this load active and deactivate prior loads of the
        same source. Set ``False`` to stage a load without exposing it.
    :param prune: After a successful activated load, delete prior (now
        inactive) loads of the same source and their compounds.
    :param progress: Optional callback invoked with the running inserted count
        after each batch.
    :return: An :class:`IngestResult` summarizing the load.
    :raises FileNotFoundError: If ``path`` does not exist.
    """
    if not path.exists():
        raise FileNotFoundError(f"Reference dump not found: {path}")

    name = source_name or adapter.name
    ingested = 0
    skipped = 0
    with engine.begin() as conn:
        if activate:
            # Only one active version per source at a time.
            conn.execute(
                update(reference_source)
                .where(reference_source.c.name == name)
                .where(reference_source.c.is_active.is_(True))
                .values(is_active=False)
            )

        source_id = conn.execute(
            insert(reference_source)
            .values(
                name=name,
                version=version,
                license=adapter.license,
                record_count=0,
                is_active=activate,
                ingested_at=datetime.now(timezone.utc),
            )
            .returning(reference_source.c.reference_source_id)
        ).scalar_one()

        batch: list[dict] = []
        for row, was_skipped in _finalized_rows(adapter, path, source_id):
            if was_skipped:
                skipped += 1
                continue
            batch.append(row)
            if len(batch) >= batch_size:
                conn.execute(insert(reference_compound), batch)
                ingested += len(batch)
                batch = []
                if progress is not None:
                    progress(ingested)
        if batch:
            conn.execute(insert(reference_compound), batch)
            ingested += len(batch)
            if progress is not None:
                progress(ingested)

        conn.execute(
            update(reference_source)
            .where(reference_source.c.reference_source_id == source_id)
            .values(record_count=ingested)
        )

        if prune and activate:
            _prune_inactive(conn, name, keep_source_id=source_id)

    return IngestResult(
        source=name,
        version=version,
        reference_source_id=source_id,
        ingested=ingested,
        skipped=skipped,
    )


def _prune_inactive(conn, source_name: str, keep_source_id: int) -> None:
    """Delete all but the given load for a source (compounds then source rows)."""
    stale = conn.execute(
        reference_source.select()
        .with_only_columns(reference_source.c.reference_source_id)
        .where(reference_source.c.name == source_name)
        .where(reference_source.c.reference_source_id != keep_source_id)
    ).scalars().all()
    if not stale:
        return
    conn.execute(
        delete(reference_compound).where(
            reference_compound.c.reference_source_id.in_(stale)
        )
    )
    conn.execute(
        delete(reference_source).where(
            reference_source.c.reference_source_id.in_(stale)
        )
    )
