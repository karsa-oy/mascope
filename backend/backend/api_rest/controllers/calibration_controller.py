from backend.api.match import item_remove as match_item_remove
from backend.api.signal import signal_mz_calibration_update

from backend.api_rest.controllers.sample_files_controller import update_sample_file
from backend.api_rest.controllers.sample_files_controller import get_sample_files
from backend.api_rest.controllers.sample_items_controller import get_sample_items

import pandas as pd

from typing import List
from ..models.pydantic_models.sample_file_pydantic_model import (
    SampleFileUpdate,
)


async def calibration_mz_apply(fit: dict, sample_filenames: List[str]):
    # Read sample file records
    sample_files = []
    for filename in sample_filenames:
        sample_file = await get_sample_files(filename=filename)
        sample_files.extend(sample_file["data"])

    sample_file_df = pd.DataFrame(sample_files)

    sample_file_df = sample_file_df.assign(
        mz_calibration=sample_file_df[["mz_calibration"]].applymap(
            lambda x: x if x is not None else x
        ),
        range=sample_file_df[["range"]].applymap(lambda x: x),
    )

    # Update zarr files
    filenames = sample_file_df["filename"].tolist()
    new_mz = signal_mz_calibration_update(fit, filenames)
    new_range = [new_mz[0], new_mz[-1]]

    fit.update({"verified": True})
    for _, sample_file in sample_file_df.iterrows():
        # Update database record
        sample_file["mz_calibration"] = fit
        sample_file["range"] = new_range
        await update_sample_file(
            sample_file["sample_file_id"], SampleFileUpdate(**sample_file.to_dict())
        )
        # Read affected sample items
        sample_items = await get_sample_items(filename=sample_file["filename"])
        sample_item_ids = [item["sample_item_id"] for item in sample_items["data"]]

        for sample_item_id in sample_item_ids:
            # Delete outdated matches
            match_item_remove(sample_item_id)
    return sample_item_ids
