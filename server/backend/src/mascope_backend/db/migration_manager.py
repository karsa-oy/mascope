"""
Migration manager module that handles database migrations.

This module centralizes all database migration logic, including version checking,
migration execution, and corruption detection.
"""

import os
import inspect
from datetime import datetime
from importlib import import_module

from mascope_backend.runtime import runtime

db_dir = runtime.config.database


class DatabaseFailedError(RuntimeError):
    """Exception raised when database corruption is detected."""

    def __init__(self, message: str, previous_version: int | None = None):
        self.previous_version = previous_version
        super().__init__(message)


def get_available_db_version() -> int:
    """
    Determine the latest available migration script version.

    Steps:
    1. Find all files in migration directory that match pattern "v*.py"
    2. Extract version numbers from filenames
    3. Return the highest version number found

    :return: The highest version number found in migration scripts
    :rtype: int
    """
    migrations_dir = os.path.join(os.path.dirname(__file__), "migration")
    files = os.listdir(migrations_dir)
    migrations = [f for f in files if f.endswith(".py") and f.startswith("v")]
    versions = [int(f.replace("v", "").replace(".py", "")) for f in migrations]
    return max(versions) if versions else 0


def get_current_db_version() -> int:
    """
    Determine the current database version from existing files.

    :return: The highest version number found in database files
    :rtype: int
    """
    v = 0
    if os.path.exists(db_dir):
        files = os.listdir(db_dir)
        databases = [
            f
            for f in files
            if f.startswith("mascope.v") and f.endswith(".db") and "_failed_" not in f
        ]
        versions = [int(f.split(".v")[1].split(".db")[0]) for f in databases]
        if versions:
            v = max(versions)
    return v


async def migrate(current_version: int, target_version: int) -> int:
    """
    Migrate the database from current_version to target_version.

    Steps:
    1. Create database directory if needed
    2. Clean up any existing failure markers for versions to be migrated
    3. For each version between current and target:
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
            runtime.logger.error(f"Failed to import migration module: {error}")
            raise RuntimeError(
                f"Could not import migration script for v{next_version}"
            ) from error

        # Run the migration
        try:
            await run_migration_script(migration_module)
            runtime.logger.info(f"Migration {migration_label} succeeded!")
            current_version = get_current_db_version()
        except Exception as error:
            runtime.logger.error(f"Migration {migration_label} failed: {error}")

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
