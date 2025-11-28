"""
Migration manager module that handles database migrations.

This module centralizes all database migration logic, including version checking,
migration execution, and corruption detection.
"""

import os
import inspect
import traceback
from datetime import datetime
from importlib import import_module

from mascope_backend.db.utils import get_current_db_version, get_available_db_version
from mascope_backend.db.wal.direct import get_journal_mode, direct_wal_checkpoint
from mascope_backend.runtime import runtime

db_dir = runtime.config.database


class DatabaseFailedError(RuntimeError):
    """Exception raised when database corruption is detected."""

    def __init__(self, message: str, previous_version: int | None = None):
        self.previous_version = previous_version
        super().__init__(message)


async def check_db_migration():
    """
    Check database version and perform migrations if needed.

    This function is called once in the main process before workers spawn.
    It handles:
    - Version detection
    - Corruption checking
    - Schema migrations

    Does NOT configure the database engine - that's done per-worker.

    :raises RuntimeError: If corrupted database detected with no recovery option
    :raises Exception: If migration fails
    """
    current_version = get_current_db_version()
    target_version = get_available_db_version()

    # Check for corruption markers if there is an existing database
    if current_version > 0:
        try:
            # This will either return the same version or raise a DatabaseFailedError
            detect_failed_database(current_version)
        except DatabaseFailedError as e:
            if e.previous_version is not None:
                runtime.logger.warning(
                    f"Using previous stable version v{e.previous_version} as starting point"
                )
                current_version = e.previous_version
            else:
                # No previous version available - re-raise the error
                raise

    # Perform migration if needed
    if current_version == target_version:
        runtime.logger.info("No database migration needed")
    else:
        runtime.logger.info(
            f"Detected mascope database version: v{current_version}. "
            f"Required mascope database version: v{target_version}."
        )
        await migrate(current_version, target_version)


async def migrate(current_version: int, target_version: int) -> int:
    """
    Migrate the database from current_version to target_version.

    Steps:
    1. Create database directory if needed
    2. Checkpoint WAL databases before migration to ensure data consistency
    3. Clean up any existing failure markers for versions to be migrated
    4. For each version between current and target:
       a. Import the migration script
       b. Run the migration script
       c. If it fails, mark the failure and raise an error

    :param current_version: The current database version
    :type current_version: int
    :param target_version: The target databasAttempting to migratee version to migrate to
    :type target_version: int
    :raises RuntimeError: If any migration step fails
    :return: The version after migration (should be target_version if successful)
    :rtype: int
    """
    runtime.logger.info(
        f"Executing migration pathway from v{current_version} to v{target_version}"
    )

    # Create database directory if it doesn't exist
    if current_version == 0 and not os.path.exists(db_dir):
        os.mkdir(db_dir)

    # If database exists and is in WAL mode, checkpoint before migration
    if current_version > 0:
        try:
            journal_mode = get_journal_mode()
            if journal_mode == "wal":
                runtime.logger.info(
                    "Database in WAL mode, performing TRUNCATE checkpoint before migration"
                )
                success = direct_wal_checkpoint("TRUNCATE")
                if success:
                    runtime.logger.debug("WAL checkpoint completed successfully")
                else:
                    runtime.logger.warning(
                        "WAL checkpoint may not have completed fully"
                    )
        except Exception as e:
            runtime.logger.warning(f"Error during pre-migration WAL checkpoint: {e}")
            # Continue with migration - this is not a fatal error, backup will still be created

    # Clean up any existing failure markers for versions to be migrated
    for version in range(current_version + 1, target_version + 1):
        cleanup_failure_markers(version)

    # Migrate one version at a time
    while current_version < target_version:
        next_version = current_version + 1
        migration_label = f"from v{current_version} to v{next_version}"

        # Import the migration module
        try:
            migration_module = import_module(
                f"mascope_backend.db.migration.v{next_version}"
            )
        except Exception as error:
            runtime.logger.error(
                f"Failed to import migration module for v{next_version}: {type(error).__name__}: {error}\n{traceback.format_exc()}"
            )
            raise RuntimeError(
                f"Could not import migration script for v{next_version}"
            ) from error

        # Run the migration
        try:
            await run_migration_script(migration_module)
            runtime.logger.info(f"Migration {migration_label} succeeded!")
            current_version = get_current_db_version()
        except Exception as error:
            runtime.logger.error(
                f"Migration {migration_label} failed: {type(error).__name__}: {error}\n{traceback.format_exc()}"
            )

            # Mark the migration as failed
            mark_migration_failed(next_version, str(error))
            raise RuntimeError(
                f"Database migration {migration_label} failed"
            ) from error

    runtime.logger.info("Migration pathway successful: database is now up-to-date.")
    return current_version


def detect_failed_database(version: int) -> int:
    """
    Check if the given database version has failed markers.

    Steps:
    1. Check for failure markers for the current version
    2. If found - look for a previous stable version
    3. Raise a DatabaseFailedError with information about the previous version

    :param version: The database version to check
    :type version: int
    :return: The version to use (either the same or an earlier valid version)
    :rtype: int
    :raises DatabaseFailedError: If corruption is detected, with information about previous version
    """
    # Check for failed flags for the current version
    failed_flags = [
        f for f in os.listdir(db_dir) if f.startswith(f"mascope.v{version}.failed_")
    ]

    if not failed_flags:
        # No corruption detected, return the current version
        return version

    runtime.logger.warning(
        f"Found markers indicating database v{version} may be corrupted"
    )

    # Try to find a previous non-corrupted version
    prev_version = version - 1
    while prev_version > 0:
        prev_db_path = os.path.join(db_dir, f"mascope.v{prev_version}.db")
        prev_failed_flags = [
            f
            for f in os.listdir(db_dir)
            if f.startswith(f"mascope.v{prev_version}.failed_")
        ]

        if os.path.exists(prev_db_path) and not prev_failed_flags:
            runtime.logger.info(f"Found earlier non-corrupted version v{prev_version}")

            # Raise an exception with information about the previous version
            raise DatabaseFailedError(
                f"Database v{version} is corrupted. Previous stable version is v{prev_version}.",
                previous_version=prev_version,
            )

        prev_version -= 1

    # No valid version found - raise an error without a previous version
    raise DatabaseFailedError(
        "No valid database version found. Manual intervention required."
    )


async def run_migration_script(migration):
    """
    Executes a migration script, handling both synchronous and asynchronous run functions.

    Steps:
    1. Check if the migration's 'run' function is a coroutine
    2. If it is, await its execution
    3. Otherwise, run it synchronously

    :param migration: The imported migration module
    :type migration: module
    """
    if inspect.iscoroutinefunction(migration.run):
        runtime.logger.info("Running asynchronous migration script.")
        await migration.run()
    else:
        runtime.logger.info("Running synchronous migration script.")
        migration.run()


def cleanup_failure_markers(version: int) -> None:
    """
    Clean up failed migration flags for a specific version.

    Steps:
    1. Find all failure marker files for the specified version
    2. Remove them all to maintain a clean state

    :param version: The version to clean up flags for
    :type version: int
    """
    failed_flags = [
        f for f in os.listdir(db_dir) if f.startswith(f"mascope.v{version}.failed_")
    ]

    if not failed_flags:
        return

    # Remove all flags
    for flag in failed_flags:
        try:
            os.remove(os.path.join(db_dir, flag))
            runtime.logger.debug(f"Cleaned up failure flag: {flag}")
        except Exception as e:
            runtime.logger.warning(f"Failed to remove flag file {flag}: {e}")


def mark_migration_failed(version: int, error_message: str) -> None:
    """
    Mark a migration as failed by creating a timestamped failure marker.

    Steps:
    1. Clean up any existing failure markers for this version
    2. Create a new failure marker with the current timestamp
    3. Write error details to the marker file

    :param version: The database version that failed migration
    :type version: int
    :param error_message: The error message to record
    :type error_message: str
    """
    # Clean up any existing failed flags first
    cleanup_failure_markers(version)

    # Create a new failure flag with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    failed_flag = os.path.join(db_dir, f"mascope.v{version}.failed_{timestamp}")

    with open(failed_flag, "w") as f:
        f.write(f"Migration failed at {timestamp}. Error: {error_message}")

    runtime.logger.info(f"Created failure marker at {failed_flag}")
