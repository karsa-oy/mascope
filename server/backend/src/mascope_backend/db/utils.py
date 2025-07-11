import os
from pathlib import Path

from mascope_backend.runtime import runtime


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
    if os.path.exists(runtime.config.database):
        files = os.listdir(runtime.config.database)
        databases = [
            f
            for f in files
            if f.startswith("mascope.v") and f.endswith(".db") and "_failed_" not in f
        ]
        versions = [int(f.split(".v")[1].split(".db")[0]) for f in databases]
        if versions:
            v = max(versions)
    return v


def get_current_db_path() -> Path:
    """
    Get the current database file path.

    :return: Path to the current database file
    :rtype: Path
    """
    return Path(runtime.config.database) / f"mascope.v{get_current_db_version()}.db"
