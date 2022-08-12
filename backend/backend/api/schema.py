from backend.db import con
from backend.server import sio

cur = con.cursor()


@sio.event(namespace='/api')
async def schema_read(sid):
    def zip_cols(row):
        table = row['table_name']
        columns = [{
                'field': col_name,
                'label': col_name.replace("_", " ").title(),
                'type': col_type
            } for col_name, col_type
            in zip(row['column_names'], row['column_types'])
        ]
        return [table, columns]

    return {
        table: columns
        for table, columns
        in map(zip_cols, (
            cur.execute("""--sql
                describe;
            """)
            .fetchdf()
            .to_dict('records')
        ))
    }
