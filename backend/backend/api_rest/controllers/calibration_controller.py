import pandas as pd
from typing import List

from backend.db_api_rest import async_session
from backend.lib.signal import signal_mz_calibration_update
from backend.socket_events import sio

from sqlalchemy import func, and_
from sqlalchemy.future import select

from .match_controller import match_item_remove
from .sample_files_controller import (
    update_sample_file,
    get_sample_files,
)
from .sample_items_controller import get_sample_items


from ..models.pydantic_models.sample_file_pydantic_model import (
    SampleFileUpdate,
)
from ..models.models import Sample


async def calibration_mz_apply(fit: dict, sample_filenames: List[str]):
    # Read sample file records
    sample_files = []
    for filename in sample_filenames:
        sample_file = await get_sample_files(filename=filename)
        sample_files.extend(sample_file["data"])

    sample_file_df = pd.DataFrame(sample_files)

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
            # FAQ_match removes mathces in all samples assosiated with filename
            # Delete outdated matches
            await match_item_remove(sample_item_id)

            await sio.emit(
                "calibration_mz_applied",
                sample_item_id,
                room=sample_item_id,
                namespace="/",
            )

    return sample_item_ids


async def get_mz_calibration(
    instrument: str = None,
    sample_item_id: str = None,
):
    async with async_session() as session:
        stmt = select(Sample.mz_calibration)
        if instrument:
            stmt = select(Sample.mz_calibration).where(
                and_(
                    Sample.instrument == instrument,
                    Sample.mz_calibration.isnot(None),
                    Sample.datetime_utc
                    == select(func.max(Sample.datetime_utc))
                    .where(
                        and_(
                            Sample.instrument == instrument,
                            Sample.mz_calibration.isnot(None),
                        )
                    )
                    .scalar_subquery(),
                )
            )
        elif sample_item_id:
            stmt = stmt.filter(Sample.sample_item_id == sample_item_id)

        result = await session.execute(stmt)
        mz_calibration = result.scalars().first()

        return mz_calibration
