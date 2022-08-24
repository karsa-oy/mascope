import sqlite3
import os

from backend.db import get_current_db_version, db_dir

current_version = get_current_db_version()

conn = sqlite3.connect(
    database=os.path.join(
        db_dir, f'mascope.v{current_version}.db'
    )
)

