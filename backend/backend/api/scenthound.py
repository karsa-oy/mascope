import asyncio


from backend.api.calibration import (
    mz_calibrate_sample as calibration_mz_calibrate_sample,
)
from backend.api.match import item_compute as match_item_compute

from backend.api_rest.controllers.sample_items_controller import create_sample_item
from backend.api_rest.models.pydantic_models.sample_item_pydantic_model import (
    SampleItemCreate,
)

from backend.server import sio


async def process_batch(sample_items):
    for sample_item in sample_items:
        await process_sample(sample_item)
    return


async def process_sample(sample_item):
    try:
        await calibration_mz_calibrate_sample(None, sample_item, {})
        await match_item_compute(sample_item)
    except Exception as e:
        print("Failed to process sample %s" % sample_item["filename"])
        print(e)


async def scenthound_process_sample(sid, sample_item):
    process_task = sio.start_background_task(process_sample, sample_item)
    await asyncio.gather(process_task)


@sio.event(namespace="/")
async def scenthound_process_samples(sid, sample_items):
    created_sample_items = []

    for sample_item in sample_items:
        sample_item_model = SampleItemCreate(**sample_item)
        created_item = await create_sample_item(sample_item_model, skipReload=True)
        created_sample_items.append(created_item.to_dict())

    process_task = sio.start_background_task(process_batch, created_sample_items)
    await asyncio.gather(process_task)

    sample_batch_id = created_sample_items[0]["sample_batch_id"]
    await sio.emit("sample_batch_reload", room=sample_batch_id, namespace="/")
