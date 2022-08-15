import duckdb
import os

from backend.db import get_current_db_version, db_dir

current_version = get_current_db_version()

con = duckdb.connect(
    database=os.path.join(
        db_dir, f'mascope.v{current_version}.duckdb'
    )
)


def init_cursor():
    return con.cursor()
