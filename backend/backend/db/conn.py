import duckdb
import os

from backend.db import get_current_db_version, db_dir

current_version = get_current_db_version()

con = duckdb.connect(
    database=os.path.join(
        db_dir, f'mascope.v{current_version}.duckdb'
    ),
    read_only=True
)


def init_cursor():
    return con.cursor()


# app
# workspace
# batch

def init_conn(batches):
    app_tables = [
        'workspace',
        'target_collection',
        'attribute_template',
        'config_mechanism'
    ]
    workspace_tables = [
        'batches'
    ]
    batch_tables = [
        'sample_item',
        'sample_file',
        'match_compound',
        'match_ion'
    ]
    target_tables = [
        'target_collection',
        'target_compound',
        'target_ion',
        'target_isotope'
    ]
    conn = duckdb.connect(':memory:')

