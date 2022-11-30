import asyncio
import datetime
import json
import nest_asyncio
import os
import pandas as pd
import sqlite3
import shutil


# patch asyncio to supported run_until_complete
# when an event loop is already running
nest_asyncio.apply()


def run():
    data_path = os.environ.get('MASCOPE_PRIVATE_DATADIR')

    # STEP 1 - setup new database
    old_db_path = os.path.join(data_path, 'database', 'mascope.v2.db')
    new_db_path = os.path.join(data_path, 'database', 'mascope.v3.db')
    shutil.copyfile(old_db_path, new_db_path)
    new_conn = sqlite3.connect(database=new_db_path)

    # Create instrument function table
    new_conn.execute("""--sql
        CREATE TABLE instrument_function (
            instrument VARCHAR(64) PRIMARY KEY
            ,datetime_utc TIMESTAMP
            ,peakshape JSON
            ,resolution_function JSON
        );
    """)

    # Populate
    from backend.lib.signal.peak import load_peakshape_mat
    instrument_function_data = []
    for i in range(1):
        instrument = "KLTOF2"
        peakshape_file = r'C:\Users\Oskari Kausiala\Documents\Repositories\labbis\parameters\peakShapes\peakshape.mat'    
        peakshape = load_peakshape_mat(peakshape_file)
        R_p1 = 0.000125
        R_p2 = 0.002545
        timestamp = datetime.datetime(1970, 1, 1)
        instrument_function_data.append((
            instrument,
            timestamp.isoformat(),
            json.dumps({'x': list(peakshape['x']), 'y': list(peakshape['y'])}),
            json.dumps([R_p1, R_p2])
        ))
    
    instrument_function_df = pd.DataFrame.from_records(
        instrument_function_data,
        columns=('instrument', 'datetime_utc', 'peakshape', 'resolution_function')
    )
    instrument_function_df.to_sql(
        'instrument_function',
        new_conn,
        if_exists='append',
        index=False
    )