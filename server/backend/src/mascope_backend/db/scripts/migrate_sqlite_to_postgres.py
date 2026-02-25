"""
SQLite -> PostgreSQL data migration.

Prerequisites:
- PostgreSQL container running
- Initial Alembic migration applied (schema exists)
- SQLite database at current latest version

Process:
- Configure SQLite engine (for restore/maintenance only)
- Run SQLite restore/maintenance (clean data)
- Create explicit engines for both databases
- Read from SQLite, write to PostgreSQL
- Validate row counts
"""

import asyncio
from datetime import datetime as dt, timezone as tz

from sqlalchemy import event, func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from mascope_backend.db import configure_database_engine
from mascope_backend.db.models import (
    Base,
    SampleBatch,
    SampleItem,
    update_workspace_on_sample_batch_change,
    update_sample_batch_on_sample_item_change,
    update_modified_timestamp,
)
from mascope_backend.db.ops.backup import create_db_backup
from mascope_backend.db.ops.maintenance import db_maintenance
from mascope_backend.db.ops.restore import db_restore
from mascope_backend.db.secrets import postgres_password
from mascope_backend.db.utils import get_current_db_version
from mascope_backend.runtime import runtime

BATCH_INSERT_SIZE = 1000

db_cfg = runtime.config.database

# FK dependency order - CRITICAL for referential integrity
TABLE_ORDER = [
    # Independent tables (no FKs)
    "attribute_template",
    "instrument_function",
    "ionization_mechanism",
    "role",
    "target_collection",
    "target_compound",
    "workspace",
    # Level 1 (depend on independent tables)
    "ionization_mode",  # -> target_collection
    "sample_batch",  # -> workspace
    "sample_file",  # -> instrument_function
    "target_compound_in_target_collection",  # junction
    "target_ion",  # -> target_compound, ionization_mechanism
    "user",  # -> role
    # Level 2
    "access_token",  # -> user
    "sample_item",  # -> sample_batch, sample_file, ionization_mode
    "target_collection_in_sample_batch",  # junction
    "target_isotope",  # -> target_ion
    # Level 3 (match tables - deepest children)
    "match_collection",  # -> sample_item, target_collection
    "match_compound",  # -> sample_item, target_compound
    "match_ion",  # -> sample_item, target_ion
    "match_isotope",  # -> sample_item, target_isotope
    "match_rating",  # -> sample_item, target_ion
    "match_sample",  # -> sample_item
]


def get_model_class(table_name: str):
    """Map table name to SQLAlchemy model."""
    for mapper in Base.registry.mappers:
        if mapper.class_.__tablename__ == table_name:
            return mapper.class_
    raise ValueError(f"No model found for table: {table_name}")


def add_timezone_to_datetime(column_name: str, value: dt, table_name: str) -> dt:
    """
    Restore timezone info to naive datetimes read from SQLite.

    SQLite stores all datetimes as naive strings regardless of tzinfo -
    timezone is silently stripped on write and not restored on read.

    Rules:
    - Already tz-aware: return as-is (shouldn't happen in practice)
    - sample_file.datetime: keep naive - instrument local time, timezone unknown
    - All others: tag as UTC - all system timestamps (created_at, registered_at,
      datetime_utc, etc.) are generated with dt.now(timezone.utc) in the application
      layer.

    :param column_name: Name of the datetime column
    :param value: Naive datetime read from SQLite
    :param table_name: Name of the table
    :return: Timezone-aware datetime (or naive for instrument local time)
    """
    if value.tzinfo is not None:
        return value  # Already has timezone

    # sample_file.datetime: local instrument time - keep naive
    # PostgreSQL stores this as TIMESTAMP WITHOUT TIME ZONE intentionally
    if table_name == "sample_file" and column_name == "datetime":
        return value

    # All system timestamps are UTC by convention (generated with dt.now(timezone.utc))
    # _utc suffix columns are explicit, others (created_at, registered_at, etc.) are implicit UTC
    return value.replace(tzinfo=tz.utc)


async def migrate_table(
    table_name: str,
    sqlite_session: AsyncSession,
    postgres_session: AsyncSession,
) -> int:
    """
    Migrate single table from SQLite -> PostgreSQL using SQLAlchemy ORM.

    :param table_name: table name to migrate
    :type table_name: str
    :param sqlite_session: SQLite database session
    :type sqlite_session: AsyncSession
    :param postgres_session: PostgreSQL database session
    :type postgres_session: AsyncSession
    :return: Number of rows migrated.
    :rtype: int
    """
    Model = get_model_class(table_name)

    # Read all rows from SQLite
    total_count = await sqlite_session.scalar(select(func.count()).select_from(Model))

    if total_count == 0:
        runtime.logger.info(f"  {table_name}: empty, skipping")
        return 0

    runtime.logger.info(f"  {table_name}: {total_count} rows")

    # Stream rows instead of loading all into memory
    result = await sqlite_session.stream(
        select(Model).execution_options(yield_per=BATCH_INSERT_SIZE)
    )

    total = 0
    batch = []

    async for (row,) in result:
        data = row.to_dict()

        for key, value in data.items():
            if isinstance(value, dt):
                data[key] = add_timezone_to_datetime(key, value, table_name)

        batch.append(data)

        if len(batch) >= BATCH_INSERT_SIZE:
            await _insert_batch(postgres_session, Model, batch)
            total += len(batch)
            batch = []
            pct = total / total_count * 100
            runtime.logger.info(f"    {total}/{total_count} ({pct:.1f}%)")

    # Remaining rows
    if batch:
        await _insert_batch(postgres_session, Model, batch)
        total += len(batch)

    runtime.logger.info(f"    ✅ {total}/{total_count} (100%)")
    return total


async def _insert_batch(
    session: AsyncSession,
    Model,
    batch: list[dict],
) -> None:
    """Core insert using insert, bypassing ORM overhead."""
    await session.execute(pg_insert(Model.__table__).values(batch))
    await session.flush()


async def reset_sequences(postgres_session: AsyncSession) -> None:
    """
    Reset PostgreSQL sequences for autoincrement columns.

    Only role_id and user.id use autoincrement in the schema.
    All other PKs are string-based (no sequences).
    """
    runtime.logger.info("\nResetting sequences")

    # role.role_id
    await postgres_session.execute(
        text(
            """
        SELECT setval(
            pg_get_serial_sequence('role', 'role_id'),
            COALESCE((SELECT MAX(role_id) FROM role), 1),
            true
        )
    """
        )
    )

    # user.id
    await postgres_session.execute(
        text(
            """
        SELECT setval(
            pg_get_serial_sequence('"user"', 'id'),
            COALESCE((SELECT MAX(id) FROM "user"), 1),
            true
        )
    """
        )
    )

    await postgres_session.commit()
    runtime.logger.info("Sequences reset successfully")


async def validate_migration(
    sqlite_session: AsyncSession,
    postgres_session: AsyncSession,
) -> list[tuple[str, int, int]]:
    """Compare row counts SQLite vs PostgreSQL."""
    mismatches = []

    runtime.logger.info("Validation:")

    for table_name in TABLE_ORDER:
        Model = get_model_class(table_name)

        sqlite_count = await sqlite_session.scalar(
            select(func.count()).select_from(Model)
        )
        postgres_count = await postgres_session.scalar(
            select(func.count()).select_from(Model)
        )

        match = sqlite_count == postgres_count
        status = "✅" if match else "❌"

        runtime.logger.info(
            f"{status} {table_name:40} SQLite: {sqlite_count:6} -> PostgreSQL: {postgres_count:6}"
        )

        if not match:
            mismatches.append((table_name, sqlite_count, postgres_count))

    return mismatches


async def run():
    """Execute migration."""
    runtime.logger.info("Starting SQLite -> PostgreSQL data migration")
    runtime.logger.info("Runtime configuration:")
    runtime.logger.info(f"Mode: {runtime.mode}")  # dev or prod
    runtime.logger.info(f"Env: {runtime.env.name}")  # test-env-1, default, etc
    runtime.logger.info(
        f"Target Postgres DB: {runtime.config.database.get_postgres_database_name(runtime.env.name)}"
    )

    # --- Setup SQLite engine ---
    current_db_version = get_current_db_version()

    # early check of correect paths resolutions
    if not current_db_version:
        runtime.logger.error("Error resolving paths to the current SQLite DB.")
        return

    await create_db_backup()

    await configure_database_engine(version=current_db_version, db_type="sqlite")
    runtime.logger.info(f"Connected to SQLite v{current_db_version}")

    # --- Validate SQLite is clean (uses global session internally) ---
    runtime.logger.info("Validating SQLite database")
    await db_restore()
    await db_maintenance()

    # --- Disable event listeners during migration ---
    runtime.logger.info("Disabling event listeners for migration")

    event.remove(SampleBatch, "after_insert", update_workspace_on_sample_batch_change)
    event.remove(SampleBatch, "after_update", update_workspace_on_sample_batch_change)
    event.remove(SampleBatch, "after_delete", update_workspace_on_sample_batch_change)
    event.remove(SampleItem, "after_update", update_sample_batch_on_sample_item_change)
    event.remove(SampleBatch, "before_update", update_modified_timestamp)

    # --- Create explicit engines for migration (separate from global) ---
    runtime.logger.info("Setting up migration connections")

    sqlite_url = db_cfg.get_sqlite_url(version=current_db_version)
    postgres_url = db_cfg.get_postgres_url(
        password=postgres_password, env_name=runtime.env.name
    )

    sqlite_engine = create_async_engine(sqlite_url, echo=False)
    postgres_engine = create_async_engine(postgres_url, echo=False)

    SQLiteSession = async_sessionmaker(sqlite_engine, expire_on_commit=False)
    PostgresSession = async_sessionmaker(postgres_engine, expire_on_commit=False)

    # --- Migrate data (SQLite uses global async_session(), PostgreSQL uses local) --
    runtime.logger.info("Starting migration")

    async with SQLiteSession() as sqlite_session, PostgresSession() as postgres_session:
        total_migrated = 0

        for table_name in TABLE_ORDER:
            count = await migrate_table(table_name, sqlite_session, postgres_session)
            await postgres_session.commit()
            total_migrated += count

    runtime.logger.info(f"Total migrated: {total_migrated} rows")

    # Reset sequences AFTER all data inserted
    async with PostgresSession() as postgres_session:
        await reset_sequences(postgres_session)

    # --- Re-enable event listeners ---
    runtime.logger.info("Re-enabling event listeners")
    event.listen(SampleBatch, "after_insert", update_workspace_on_sample_batch_change)
    event.listen(SampleBatch, "after_update", update_workspace_on_sample_batch_change)
    event.listen(SampleBatch, "after_delete", update_workspace_on_sample_batch_change)
    event.listen(SampleItem, "after_update", update_sample_batch_on_sample_item_change)
    event.listen(SampleBatch, "before_update", update_modified_timestamp)

    # --- Validate ---
    runtime.logger.info("Validating migration")
    async with SQLiteSession() as sqlite_session, PostgresSession() as postgres_session:
        mismatches = await validate_migration(sqlite_session, postgres_session)

    if mismatches:
        runtime.logger.error(f"❌ {len(mismatches)} tables have count mismatches!")
        for table, sqlite_count, postgres_count in mismatches:
            runtime.logger.error(f"  {table}: {sqlite_count} -> {postgres_count}")
        raise RuntimeError("❌ Migration validation failed")

    runtime.logger.info("✅ Migration completed successfully!")

    await postgres_engine.dispose()


if __name__ == "__main__":
    asyncio.run(run())
