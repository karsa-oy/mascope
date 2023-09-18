import asyncio

from backend.api.calibration import (
    mz_calibrate_sample as calibration_mz_calibrate_sample,
)

from backend.api_rest.controllers.match_controller import (
    match_batches_compute,
)
from backend.api_rest.controllers.sample_items_controller import create_sample_item
from backend.api_rest.models.pydantic_models.sample_item_pydantic_model import (
    SampleItemCreate,
)
from backend.api_rest.models.pydantic_models.match_pydantic_model import (
    MatchComputeBatch,
)

from backend.server import sio


@sio.event(namespace="/")
async def scenthound_process_samples(sid, sample_items):
    created_sample_items = []

    for sample_item in sample_items:
        sample_item_model = SampleItemCreate(**sample_item)
        created_item = await create_sample_item(sample_item_model, skipReload=True)
        created_sample_items.append(created_item.to_dict())

    process_task = sio.start_background_task(process_batch, created_sample_items)
    await asyncio.gather(process_task)


async def process_batch(sample_items):
    # Step 1. Calibrate each sample
    for sample_item in sample_items:
        await calibrate_sample(sample_item)

    # Step 2. Compute matches for the batch
    sample_batch_id = sample_items[0]["sample_batch_id"]

    await match_batches_compute([MatchComputeBatch(sample_batch_id=sample_batch_id)])
    return


# TODO_calibration change to calibrate_batch
async def calibrate_sample(sample_item):
    try:
        await calibration_mz_calibrate_sample(None, sample_item, {})
    except Exception as e:
        print("Failed to calibrate sample %s" % sample_item["filename"])
        print(e)
