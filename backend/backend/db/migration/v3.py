import asyncio
import datetime
import json
import nest_asyncio
import os
import pandas as pd
import sqlite3
import shutil

from backend.db import gen_id

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
            instrument_function_id VARCHAR(32) PRIMARY KEY
            ,instrument VARCHAR(64)
            ,datetime_utc TIMESTAMP
            ,peakshape JSON
            ,resolution_function JSON
        );
    """)

    # Populate
    from backend.lib.signal.peak import load_peakshape_mat
    instrument_function_data = []
    
    # KLTOF2
    instrument = "KLTOF2"
    peakshape_file = os.path.join(data_path, 'database', '20221129T135120.mat')
    peakshape = load_peakshape_mat(peakshape_file)
    R_p1 = 0.0001097
    R_p2 = 0.002287
    timestamp = datetime.datetime(2021, 8, 31)
    instrument_function_data.append((
        gen_id(length=32),
        instrument,
        timestamp.isoformat(),
        json.dumps({'x': list(peakshape['x']), 'y': list(peakshape['y'])}),
        json.dumps([R_p1, R_p2])
    ))
    # 
    instrument = "KLTOF2"
    peakshape_file = os.path.join(data_path, 'database', '20221202T102104.mat')
    peakshape = load_peakshape_mat(peakshape_file)
    R_p1 = 0.0001258
    R_p2 = 0.001769
    timestamp = datetime.datetime(2022, 1, 27)
    instrument_function_data.append((
        gen_id(length=32),
        instrument,
        timestamp.isoformat(),
        json.dumps({'x': list(peakshape['x']), 'y': list(peakshape['y'])}),
        json.dumps([R_p1, R_p2])
    ))
    # 
    # KLTOF1
    instrument = "KLTOF1"
    peakshape_file = os.path.join(data_path, 'database', '20221202T101822.mat')
    peakshape = load_peakshape_mat(peakshape_file)
    R_p1 = 9.01e-05
    R_p2 = 0.0006993
    timestamp = datetime.datetime(2022, 11, 10)
    instrument_function_data.append((
        gen_id(length=32),
        instrument,
        timestamp.isoformat(),
        json.dumps({'x': list(peakshape['x']), 'y': list(peakshape['y'])}),
        json.dumps([R_p1, R_p2])
    ))
    # 

    instrument_function_df = pd.DataFrame.from_records(
        instrument_function_data,
        columns=(
            'instrument_function_id',
            'instrument',
            'datetime_utc',
            'peakshape',
            'resolution_function'
            )
    )
    instrument_function_df.to_sql(
        'instrument_function',
        new_conn,
        if_exists='append',
        index=False
    )