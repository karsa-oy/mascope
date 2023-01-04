import asyncio
import pandas as pd

from backend.api.calibration import mz_calibrate_sample as calibration_mz_calibrate_sample
from backend.api.match import item_compute as match_item_compute
from backend.api.sample import item_create as sample_item_create
from backend.db.conn import conn
from backend.server import sio


async def process_sample(sample_item):
    try:
        filename = sample_item['filename']
        [instrument] = pd.read_sql(f"""--sql
                SELECT instrument
                FROM sample_file
                WHERE filename = ?
                """,
                conn,
                params=[filename]
            )['instrument'].tolist()
        await calibration_mz_calibrate_sample(None, sample_item)
        await match_item_compute(sample_item['sample_item_id'])
    except:
        print("Failed to process sample %s" %sample_item['filename'])


async def scenthound_process_sample(sid, sample_item):
    process_task = sio.start_background_task(
        process_sample, sample_item
    )
    await asyncio.gather(process_task)

@sio.event(namespace='/')
async def scenthound_process_samples(sid, sample_items):
    # Create sample item records
    sample_item_df = sample_item_create(sample_items)
    sample_items = sample_item_df.to_dict('records')

    process_tasks = [
        sio.start_background_task(
            process_sample, sample_item
        )
        for sample_item in sample_items
    ]
    await asyncio.gather(*process_tasks)
    sample_batch_id = sample_item_df['sample_batch_id'].tolist()[0]
    await sio.emit(
        'sample_batch_reload',
        room=sample_batch_id,
        namespace='/'
        )