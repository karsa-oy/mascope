import os
import sqlite3
from .. import get_current_db_version, create_db_backup


def run():
    """
    Executes maintenance operations on the database. This includes backing up the database,
    vacuuming to defragment, analyzing to optimize query plans, and checking database integrity.
    """
    data_path = os.environ.get("MASCOPE_PRIVATE_DATABASE_DIR")

    # Determine the current version and paths
    current_version = get_current_db_version()
    db_path = os.path.join(data_path, f"mascope.v{current_version}.db")
    create_db_backup(db_path, "maintenance")

    # Connect to the original database
    conn = sqlite3.connect(db_path)
    with conn:
        # Perform a VACUUM operation to rebuild the database and optimize disk space
        print("Performing VACUUM...")
        conn.execute("VACUUM")

        # Perform an ANALYZE operation to optimize the database's internal statistics for better query planning
        print("Performing ANALYZE...")
        conn.execute("ANALYZE")

        # Log indexes after ANALYZE
        print("Indexes after maintenance:")
        log_indexes(conn)

        # Other maintenance operations could be added here
        print("Checking database integrity...")
        result = conn.execute("PRAGMA integrity_check")
        integrity_result = result.fetchone()
        print(f"Integrity check result: {integrity_result}")

    print("Database maintenance operations completed successfully.")


def log_indexes(conn):
    """Logs the indexes of all tables in the database and counts manual and auto-created indexes."""
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()

    manual_index_count = 0
    auto_index_count = 0

    for table in tables:
        # TODO_debug_mode
        # print(f"Indexes for table {table[0]}:")
        cursor.execute(f"PRAGMA index_list({table[0]})")
        indexes = cursor.fetchall()
        for index in indexes:
            print(index)
            if "idx_" in index[1]:
                manual_index_count += 1
            elif "sqlite_autoindex_" in index[1]:
                auto_index_count += 1

    print("\nSummary of Index Usage:")
    print(f"Manual indexes count: {manual_index_count}")
    print(f"Auto-created indexes count: {auto_index_count}")

    if manual_index_count == 0 and auto_index_count == 0:
        print("Warning: No indexes found, please verify if this is expected.")


if __name__ == "__main__":
    run()
