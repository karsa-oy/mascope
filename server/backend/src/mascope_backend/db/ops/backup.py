import os
import asyncio
import sqlite3
from datetime import datetime
from mascope_backend.db import get_current_db_version
from mascope_backend.runtime import runtime


async def create_db_backup():
    """
    Asynchronously create a timestamped backup of the SQLite database using SQLite's backup API.
    """
    # Get the current database version and path
    database_dir = runtime.config.database
    current_version = get_current_db_version()
    db_path = os.path.join(database_dir, f"mascope.v{current_version}.db")
    backup_dir = os.path.join(database_dir, "backup")

    # Create the backup directory if it doesn't exist
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)

    # Create a timestamped backup file name
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_db_path = os.path.join(
        backup_dir, f"{timestamp}_backup_mascope.v{current_version}.db"
    )

    # Use SQLite's backup API to ensure a consistent backup
    try:
        # Run the blocking database backup in a separate thread using asyncio's run_in_executor
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, backup_db, db_path, backup_db_path)
        runtime.logger.info(f"Database backup created at {backup_db_path}")
    except Exception as e:
        runtime.logger.error(f"Failed to create database backup: {e}")


def backup_db(db_path, backup_db_path):
    """
    Helper function to perform the actual database backup.
    """
    with sqlite3.connect(db_path) as conn:
        with sqlite3.connect(backup_db_path) as backup_conn:
            conn.backup(backup_conn)


def run_db_backup():
    """
    Entry point for running the backup command synchronously.
    """
    asyncio.run(create_db_backup())
