import asyncio
import os
import shutil
import time
from dataclasses import dataclass
from typing import Iterable, Sequence
from concurrent.futures import ThreadPoolExecutor
import sqlite3

from mascope_backend.runtime import runtime
from mascope_backend.db import configure_database_engine
from mascope_backend.db.ops.backup import create_db_backup
import mascope_file.io as m_io

# Determine concurrency level based on CPU cores
# Reserve 2 cores for system responsiveness
# Concurrency is used for I/O-bound peak ID lookups
cpu_cores = os.cpu_count()
CONCURRENCY = max(1, cpu_cores - 2)

# Thresholds and batch sizes
ISOTOPE_BUFFER_TARGET = 2_000_000  # rows before flush to temp SQL table
SQLITE_BATCH_INSERT_SIZE = 100_000
MAX_PENDING_FILES = 512  # cap memory usage
LOAD_TIMEOUT = 30.0


# NOTE when __slots__ is defined, Python allocates a fixed set of attributes,
# preventing the creation of __dict__ and saving memory,
# especially important when creating millions of small objects.
@dataclass(slots=True)
class IsotopeRow:
    target_isotope_id: str
    sample_item_id: str
    sample_peak_index: int


@dataclass(slots=True)
class PeakLookupTask:
    sample_item_id: str
    filename: str
    needed_indices: list[int]


async def run() -> None:
    # Backup and prepare database
    await create_db_backup()
    old_version = 38
    new_version = 39
    src = os.path.join(runtime.config.database, f"mascope.v{old_version}.db")
    dst = os.path.join(runtime.config.database, f"mascope.v{new_version}.db")
    shutil.copyfile(src, dst)
    await configure_database_engine(new_version)

    conn = get_sqlite_connection(dst)
    try:
        migrate_sample_peak_id_to_varchar(conn)
        create_temp_tables(conn)
        sample_id_to_filename_map = load_sample_mapping(conn)
        executor = ThreadPoolExecutor(max_workers=CONCURRENCY)
        updates = []
        deletes = []
        current_file_batch = {}
        start = time.time()

        runtime.logger.info(
            "Starting migration v39: updating match_isotope.sample_peak_id in progress..."
        )

        async def process_file_batch() -> None:
            """Process the current batch of files for peak ID lookups and prepare updates/deletes."""
            if not current_file_batch:
                return
            peak_lookup_tasks = []
            for sample_item_id, rows in current_file_batch.items():
                filename = sample_id_to_filename_map.get(sample_item_id)
                if not filename:
                    # No sample file -> delete all related isotopes
                    deletes.extend(r.target_isotope_id for r in rows)
                    continue
                required_peak_indices = [
                    r.sample_peak_index for r in rows if r.sample_peak_index >= 0
                ]
                if not required_peak_indices:
                    # No matched peaks
                    updates.extend((r.target_isotope_id, "") for r in rows)
                    continue
                peak_lookup_tasks.append(
                    PeakLookupTask(sample_item_id, filename, required_peak_indices)
                )

            peak_mapping = await gather_peak_lookups(executor, peak_lookup_tasks)
            for sample_item_id, rows in current_file_batch.items():
                peak_map = peak_mapping.get(sample_item_id, {})
                if not peak_map and any(r.sample_peak_index >= 0 for r in rows):
                    # Failed to load peaks -> delete all related isotopes
                    deletes.extend(r.target_isotope_id for r in rows)
                    continue
                for r in rows:
                    if r.sample_peak_index < 0:
                        # -1 indicates no matched peak
                        updates.append((r.target_isotope_id, ""))
                    else:
                        new_id = peak_map.get(r.sample_peak_index)
                        (
                            updates.append((r.target_isotope_id, new_id))
                            if new_id is not None
                            else deletes.append(r.target_isotope_id)
                        )
            if len(updates) + len(deletes) >= ISOTOPE_BUFFER_TARGET:
                # Flush to temp SQL tables
                flush_updates(conn, updates, deletes)
                updates.clear()
                deletes.clear()
            current_file_batch.clear()

        # Stream and process isotope rows
        total_rows = conn.execute("SELECT COUNT(*) FROM match_isotope;").fetchone()[0]
        last_percent = -1
        for row in stream_isotopes(conn):
            bucket = current_file_batch.setdefault(row.sample_item_id, [])
            bucket.append(row)
            if len(current_file_batch) >= MAX_PENDING_FILES:
                await process_file_batch()
                percent_ready = int((len(updates) + len(deletes)) / total_rows * 100)
                if percent_ready // 5 > last_percent // 5:
                    runtime.logger.info(f"Processed {percent_ready}% isotope rows...")
                    last_percent = percent_ready
        await process_file_batch()
        flush_updates(conn, updates, deletes)

        runtime.logger.info("Applying final updates to match_isotope table...")

        apply_final_update(conn)

        executor.shutdown(wait=True)
        restore_normal_pragmas(conn)
        conn.commit()
        conn.execute("VACUUM;")
        runtime.logger.info(f"Migration v39 complete in {time.time() - start:.2f}s")
    finally:
        # Ensure lock release even on exception
        try:
            conn.close()
        except Exception as e:
            runtime.logger.exception(
                f"Exception occurred while closing the database connection during migration v39 cleanup: {e}."
            )


def apply_sqlite_pragmas(conn: sqlite3.Connection) -> None:
    """Apply SQLite pragmas optimized for bulk migration performance."""
    pragmas = [
        ("journal_mode", "MEMORY"),  # temp change, will restore to WAL later
        ("synchronous", "OFF"),
        ("temp_store", "MEMORY"),
        ("locking_mode", "EXCLUSIVE"),  # must be reverted or connection closed
        ("cache_size", "-200000"),
        ("mmap_size", "1099511627776"),
    ]
    cur = conn.cursor()
    for key, value in pragmas:
        cur.execute(f"PRAGMA {key}={value};")
    cur.close()


def restore_normal_pragmas(conn: sqlite3.Connection) -> None:
    """
    Restore settings for normal application operation after bulk migration.
    Only journal_mode persists across connections; others are connection-scoped.
    """
    cur = conn.cursor()
    # WAL for concurrency; NORMAL sync for durability/perf balance.
    cur.execute("PRAGMA journal_mode=WAL;")
    cur.execute("PRAGMA synchronous=NORMAL;")
    cur.execute("PRAGMA locking_mode=NORMAL;")
    cur.execute("PRAGMA temp_store=DEFAULT;")
    cur.execute("PRAGMA foreign_keys=ON;")
    cur.close()


def get_sqlite_connection(db_path: str) -> sqlite3.Connection:
    """Get a SQLite connection with pragmas applied for migration."""
    conn = sqlite3.connect(db_path)
    apply_sqlite_pragmas(conn)
    conn.execute("PRAGMA foreign_keys=OFF;")
    return conn


def load_sample_mapping(conn: sqlite3.Connection) -> dict[str, str]:
    """Load mapping of sample_item_id to filename from sample_item table."""
    cur = conn.cursor()
    cur.execute("SELECT sample_item_id, filename FROM sample_item;")
    mapping = {row[0]: row[1] for row in cur.fetchall()}
    cur.close()
    return mapping


def stream_isotopes(conn: sqlite3.Connection) -> Iterable[IsotopeRow]:
    """Stream isotope rows from match_isotope table in batches."""
    cur = conn.cursor()
    cur.execute(
        "SELECT target_isotope_id, sample_item_id, sample_peak_id "
        "FROM match_isotope ORDER BY sample_item_id;"
    )
    fetch = cur.fetchmany
    while True:
        rows = fetch(100_000)
        if not rows:
            break
        for target_id, sample_item_id, peak_index in rows:
            yield IsotopeRow(target_id, sample_item_id, int(peak_index))
    cur.close()


def load_peak_ids_slice(filename: str, indices: Sequence[int]) -> dict[int, str]:
    """Load peak IDs for given indices from the sample file.

    :param filename: Sample file name to load peak IDs from
    :type filename: str
    :param indices: List of peak ids from the match_isotope.sample_peak_id column
    :type indices: Sequence[int]
    :return: Mapping of original index to peak ID string
    :rtype: dict[int, str]
    """
    if not indices:
        return {}
    # Deduplicate & keep only non-negative
    unique = sorted({i for i in indices if i >= 0})
    if not unique:
        return {}

    try:
        peak_id_coordinates = m_io.load_coord(
            filename, var="peak_timeseries", coord_name="id"
        )
        num_peak_ids = peak_id_coordinates.shape[0]
        in_bounds_indices = [i for i in unique if i < num_peak_ids]
        if not in_bounds_indices:
            return {}
        peak_id_slice = peak_id_coordinates[in_bounds_indices]

        return {
            idx: str(peak_id_slice[pos]) for pos, idx in enumerate(in_bounds_indices)
        }
    except Exception:
        # Any failure -> delete related isotopes
        return {}


async def gather_peak_lookups(
    executor: ThreadPoolExecutor, tasks: list[PeakLookupTask]
) -> dict[str, dict[int, str]]:
    """Gather peak ID lookups using thread pool executor.

    :param executor: ThreadPoolExecutor for concurrent file I/O
    :type executor: ThreadPoolExecutor
    :param tasks: List of PeakLookupTask to process
    :type tasks: list[PeakLookupTask]
    :return: Mapping of sample_item_id to peak ID mappings
    :rtype: dict[str, dict[int, str]]
    """
    loop = asyncio.get_running_loop()
    futures = [
        loop.run_in_executor(
            executor, load_peak_ids_slice, t.filename, t.needed_indices
        )
        for t in tasks
    ]
    results = await asyncio.wait_for(asyncio.gather(*futures), timeout=LOAD_TIMEOUT)
    peak_lookup_mapping = {}
    for task, mapping in zip(tasks, results):
        peak_lookup_mapping[task.sample_item_id] = mapping
    return peak_lookup_mapping


def create_temp_tables(conn: sqlite3.Connection) -> None:
    """Create temporary tables for batching updates and deletes."""
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TEMP TABLE temp_updates (
            target_isotope_id TEXT PRIMARY KEY,
            new_sample_peak_id TEXT
        );
    """
    )
    cur.execute(
        """
        CREATE TEMP TABLE temp_deletes (
            target_isotope_id TEXT PRIMARY KEY
        );
    """
    )
    cur.close()


def flush_updates(
    conn: sqlite3.Connection, updates: list[tuple[str, str]], deletes: list[str]
) -> None:
    """Flush accumulated updates and deletes to temporary tables."""
    cur = conn.cursor()
    # Batched inserts
    for i in range(0, len(updates), SQLITE_BATCH_INSERT_SIZE):
        chunk = updates[i : i + SQLITE_BATCH_INSERT_SIZE]
        cur.executemany(
            "INSERT OR REPLACE INTO temp_updates (target_isotope_id, new_sample_peak_id) VALUES (?, ?);",
            chunk,
        )
    for i in range(0, len(deletes), SQLITE_BATCH_INSERT_SIZE):
        chunk = [(d,) for d in deletes[i : i + SQLITE_BATCH_INSERT_SIZE]]
        cur.executemany(
            "INSERT OR REPLACE INTO temp_deletes (target_isotope_id) VALUES (?);", chunk
        )
    conn.commit()
    cur.close()


def migrate_sample_peak_id_to_varchar(conn: sqlite3.Connection) -> None:
    """
    Migrate match_isotope.sample_peak_id from INTEGER to VARCHAR(20) NOT NULL,
    updating the table to match the v39 schema.
    """
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS match_isotope_new (
            match_isotope_id VARCHAR(32) NOT NULL PRIMARY KEY,
            target_isotope_id VARCHAR(16) NOT NULL
                REFERENCES target_isotope(target_isotope_id) ON DELETE CASCADE,
            sample_item_id VARCHAR(16) NOT NULL
                REFERENCES sample_item(sample_item_id) ON DELETE CASCADE,
            sample_peak_id VARCHAR(20) NOT NULL,
            sample_peak_mz FLOAT NOT NULL,
            sample_peak_intensity FLOAT NOT NULL,
            sample_peak_intensity_relative FLOAT NOT NULL,
            sample_peak_tof FLOAT NOT NULL,
            match_abundance_error FLOAT NOT NULL,
            match_mz_error FLOAT NOT NULL,
            match_isotope_similarity FLOAT NOT NULL,
            match_score FLOAT NOT NULL CHECK (match_score BETWEEN 0 AND 1),
            match_isotope_utc_created TIMESTAMP,
            match_isotope_utc_modified TIMESTAMP
        );
        """
    )
    cur.execute(
        """
        INSERT INTO match_isotope_new (
            match_isotope_id,
            target_isotope_id,
            sample_item_id,
            sample_peak_id,
            sample_peak_mz,
            sample_peak_intensity,
            sample_peak_intensity_relative,
            sample_peak_tof,
            match_abundance_error,
            match_mz_error,
            match_isotope_similarity,
            match_score,
            match_isotope_utc_created,
            match_isotope_utc_modified
        )
        SELECT
            match_isotope_id,
            target_isotope_id,
            sample_item_id,
            CAST(sample_peak_id AS VARCHAR(20)),
            sample_peak_mz,
            sample_peak_intensity,
            sample_peak_intensity_relative,
            sample_peak_tof,
            match_abundance_error,
            match_mz_error,
            match_isotope_similarity,
            match_score,
            match_isotope_utc_created,
            match_isotope_utc_modified
        FROM match_isotope;
        """
    )
    cur.execute("DROP TABLE match_isotope;")
    cur.execute("ALTER TABLE match_isotope_new RENAME TO match_isotope;")
    # Recreate indexes for optimal query performance
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_match_isotope_sample_item ON match_isotope (sample_item_id);"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_match_isotope_sample_peak_id ON match_isotope (sample_peak_id);"
    )
    conn.commit()
    cur.close()


def apply_final_update(conn: sqlite3.Connection) -> None:
    """Apply final updates and deletes from temporary tables to match_isotope."""
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE match_isotope
        SET sample_peak_id = (
            SELECT new_sample_peak_id
            FROM temp_updates u
            WHERE u.target_isotope_id = match_isotope.target_isotope_id
        )
        WHERE target_isotope_id IN (SELECT target_isotope_id FROM temp_updates);
    """
    )
    cur.execute(
        """
        DELETE FROM match_isotope
        WHERE target_isotope_id IN (SELECT target_isotope_id FROM temp_deletes);
    """
    )
    conn.commit()
    cur.close()


if __name__ == "__main__":
    asyncio.run(run())
