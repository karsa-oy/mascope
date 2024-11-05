import importlib
import os
import re
from mascope_server.db import get_current_db_version
from mascope_server.runtime import runtime


def get_table_configs() -> dict:
    """
    Retrieves the table configurations for the current version of the database schema.

    :return: Dictionary with table configurations (columns, fks, SQL).
    """
    current_version = get_current_db_version()

    try:
        # Dynamically import the appropriate version module
        version_module = importlib.import_module(
            f"mascope_server.db.tables_config.versions.v{current_version}"
        )
        runtime.logger.info(
            f"Using schema configuration for version {current_version}."
        )
        return version_module.table_configs
    except ModuleNotFoundError:
        runtime.logger.warning(
            f"No schema configuration for version {current_version}. Using latest configuration."
        )
        return get_latest_table_configs()


def get_latest_table_configs() -> dict:
    """
    Retrieves the latest available table configurations based on the available version files.

    :return: Dictionary containing the latest table configuration.
    """
    # Find the latest version by looking at the available version files
    versions_dir = os.path.join(os.path.dirname(__file__), "versions")
    files = os.listdir(versions_dir)
    print(files)
    version_files = [f for f in files if re.search(r"v[0-9]+\.py", f)]
    print(version_files)
    versions = [int(re.search(r"[0-9]+", f).group()) for f in version_files]
    print(versions)

    # Get the highest version number
    latest_version = max(versions)

    # Dynamically import the latest version module
    version_module = importlib.import_module(
        f"mascope_server.db.tables_config.versions.v{latest_version}"
    )
    runtime.logger.info(
        f"Using latest schema configuration for version {latest_version}."
    )
    return version_module.table_configs
