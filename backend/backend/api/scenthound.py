import asyncio

from backend.api.calibration import calibration_mz_calibrate_sample
from backend.api.match import match_item_compute
from backend.api.sample import sample_item_create
from backend.server import sio


@sio.event(namespace='/')
async def scenthound_process_samples(sid, sample_items):
    # Create sample item records
    sample_items = await sample_item_create(sid, sample_items)
    # m/z calibrate
    calibration_tasks = [
        asyncio.create_task(
            calibration_mz_calibrate_sample(sid, sample_item)
        )
        for sample_item in sample_items
    ]
    await asyncio.gather(*calibration_tasks)
    # match
    match_item_tasks = [
        asyncio.create_task(
            match_item_compute(sid, sample_item['sample_item_id'])
        )
        for sample_item in sample_items
    ]
    await asyncio.gather(*match_item_tasks)