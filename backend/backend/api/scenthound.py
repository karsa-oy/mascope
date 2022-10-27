import asyncio

from backend.api.calibration import mz_calibrate_sample as calibration_mz_calibrate_sample
from backend.api.match import item_compute as match_item_compute
from backend.api.sample import item_create as sample_item_create
from backend.server import sio


@sio.event(namespace='/')
async def scenthound_process_samples(sid, sample_items):
    # Create sample item records
    sample_item_df = sample_item_create(sample_items)
    sample_items = sample_item_df.to_dict('records')
    # m/z calibrate
    [
        calibration_mz_calibrate_sample(sample_item)
        for sample_item in sample_items
    ]
    # match
    [
        match_item_compute(sample_item['sample_item_id'])
        for sample_item in sample_items
    ]
    sample_batch_id = sample_item_df['sample_batch_id'].tolist()[0]
    await sio.emit(
        'sample_batch_reload',
        room=sample_batch_id,
        namespace='/'
        )