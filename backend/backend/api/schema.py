import pandas as pd

from backend.db.conn import conn
from backend.server import sio



@sio.event(namespace='/')
async def schema_read(sid):
    with conn:
        schema = {}
        tables = pd.read_sql_query("""
            SELECT name FROM sqlite_master WHERE type='table'
            """,
            conn
            )['name'].tolist()
        for table_name in tables:
            table_info = conn.cursor().execute(
                "PRAGMA table_info('%s')" % table_name
                ).fetchall()
            columns = [{
                'field': col_name,
                'label': col_name.replace("_", " ").title(),
                'type': col_type
                } for _, col_name, col_type, _, _, _ in table_info
            ]
            schema.update({table_name: columns})
    return schema
