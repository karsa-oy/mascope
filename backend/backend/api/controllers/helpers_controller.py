from sqlalchemy import select
from backend.db import async_session
from backend.api_sio import sio
from ..models.models import (
    TargetCompoundInTargetCollection,
    TargetCollectionInSampleBatch,
)
from ..models.pydantic_models.match_pydantic_model import (
    ProgressProperties,
)


async def get_affected_batches_and_collections(target_compound_id: str):
    async with async_session() as session:
        # Get the target collections for this compound
        target_collections = await session.execute(
            select(TargetCompoundInTargetCollection.target_collection_id).where(
                TargetCompoundInTargetCollection.target_compound_id
                == target_compound_id
            )
        )
        target_collections_ids = {tc[0] for tc in target_collections}

        # Get all affected sample batches
        sample_batches = await session.execute(
            select(TargetCollectionInSampleBatch.sample_batch_id).where(
                TargetCollectionInSampleBatch.target_collection_id.in_(
                    target_collections_ids
                )
            )
        )
        sample_batches_ids = {sb[0] for sb in sample_batches}

        return sample_batches_ids, target_collections_ids


async def emit_progress_update(
    progress_properties: ProgressProperties, increment: float
):
    #  TODO: - optimize instrument/compute_sample_match notifications emits/listeners.
    if not progress_properties:
        return
    if progress_properties.progress_type in ["rematch_batches", "rematch_batch"]:
        item_weight = progress_properties.item_weight
        item_index = progress_properties.item_index
        batch_index = progress_properties.batch_index
        total_batches = progress_properties.total_batches
        workspace_id = progress_properties.workspace_id

        # Calculate the progress contribution of completed batches
        batch_progress = ((batch_index - 1) / total_batches) * 100

        # Calculate the progress within the current batch
        item_progress = ((item_index + increment) * item_weight) * 100

        # Calculate the proportional progress of the current batch in terms of the overall progress
        proportional_batch_progress = item_progress * (1 / total_batches)

        # Combine both progresses
        progress_percentage_all = batch_progress + proportional_batch_progress

        if progress_properties.progress_type == "rematch_batches":
            # emit event to the user who triggered rematch_batches operation
            await sio.emit(
                "rematch_batches_progress_percentage",
                {
                    "progress_percentage": progress_percentage_all,
                    "progress_percentage_batch": proportional_batch_progress
                    * total_batches,
                },
                room=progress_properties.sid,
                namespace="/",
            )
            # emit event to the client of current affected batch
            # TODO_notifications compute the real progress for the current batch, not progress_percentage_all
            await sio.emit(
                "rematch_batch_progress_percentage",
                {
                    "progress_percentage": progress_percentage_all,
                    "progress_percentage_batch": proportional_batch_progress
                    * total_batches,
                },
                room=progress_properties.sample_batch_id,
                namespace="/",
            )
        if progress_properties.progress_type == "rematch_batch":
            await sio.emit(
                "rematch_batch_progress_percentage",
                {
                    "progress_percentage": progress_percentage_all,
                    "progress_percentage_batch": proportional_batch_progress
                    * total_batches,
                },
                room=progress_properties.sample_batch_id,
                namespace="/",
            )

    elif progress_properties.progress_type == "match_item":
        sample_batch_id = progress_properties.sample_batch_id

        progress_percentage_item = increment * 100
        await sio.emit(
            "match_item_update_compute_progress",
            {
                "progress_percentage": progress_percentage_item,
            },
            room=sample_batch_id,
            namespace="/",
        )
    elif progress_properties.progress_type == "export_peaks":
        total_samples = progress_properties.total_samples
        item_index = progress_properties.item_index

        progress_percentage = ((item_index + increment) / total_samples) * 100

        await sio.emit(
            "batch_export_peak_data_progress",
            {
                "progress_percentage": progress_percentage,
                "progress_data_message": f"Processing sample {item_index + 1}/{total_samples}",
            },
            room=progress_properties.sid,
            namespace="/",
        )
