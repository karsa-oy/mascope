"""
Collection-level match records service for target collections with match data.
"""

from sqlalchemy import select, and_

from mascope_backend.db import async_session
from mascope_backend.db.models import (
    Sample,
    SampleBatch,
    TargetCollection,
    TargetCollectionInSampleBatch,
    MatchCollection,
)
from mascope_backend.api.lib.api_features import api_controller
from mascope_backend.api.controllers.samples.lib.samples_fetch import fetch_sample
from mascope_backend.api.controllers.sample.lib.sample_batches_fetch import (
    fetch_sample_batch,
)
from mascope_backend.api.models.target.collections.config import (
    target_collection_config,
)


@api_controller()
async def get_match_collection_records(
    sample_item_id: str | None = None,
    sample_batch_id: str | None = None,
    target_collection_id: str | None = None,
) -> dict:
    """
    Retrieves target collections with match collection data for sample or batch.

    Handles entity validation and orchestrates the data retrieval process.
    For sample-level queries, returns target collections with actual match data.
    For batch-level queries, returns target collections with placeholder match data.

    :param sample_item_id: Unique identifier of the sample item, defaults to None
    :type sample_item_id: str | None
    :param sample_batch_id: Unique identifier of the sample batch, defaults to None
    :type sample_batch_id: str | None
    :param target_collection_id: Optional filter by specific target collection, defaults to None
    :type target_collection_id: str | None
    :return: Dictionary containing status, message, results count, and match collection records data
    :rtype: dict
    """
    if sample_item_id:
        sample = await fetch_sample(sample_item_id)
        entity_name = sample.sample_item_name
        entity_type = "sample"

        data = await _get_sample_match_collection_records(sample, target_collection_id)
    else:
        sample_batch = await fetch_sample_batch(sample_batch_id)
        entity_name = sample_batch.sample_batch_name
        entity_type = "batch"

        data = await _get_batch_match_collection_records(
            sample_batch, target_collection_id
        )

    if not data:
        return {
            "status": "success",
            "message": f"No match collections found for {entity_type} '{entity_name}'",
            "results": 0,
            "data": [],
        }

    return {
        "status": "success",
        "message": f"Successfully retrieved match collection records for {entity_type} '{entity_name}'",
        "results": len(data),
        "data": data,
    }


async def _get_sample_match_collection_records(
    sample: Sample, target_collection_id: str | None = None
) -> list[dict]:
    """
    Retrieves target collections with match collection data for a sample.

    :param sample: Sample item SQLAlchemy object
    :type sample: Sample
    :param target_collection_id: Optional target collection filter
    :type target_collection_id: str | None
    :return: List of collection records with nested match data
    :rtype: list[dict]
    """
    async with async_session() as session:
        query = (
            select(
                TargetCollection,
                MatchCollection,
                TargetCollection.target_collection_type.in_(
                    target_collection_config.APP_ALARMING_COLLECTION_TYPES
                ).label("alarming"),
            )
            .select_from(TargetCollection)
            .join(
                TargetCollectionInSampleBatch,
                and_(
                    TargetCollectionInSampleBatch.sample_batch_id
                    == sample.sample_batch_id,
                    TargetCollectionInSampleBatch.target_collection_id
                    == TargetCollection.target_collection_id,
                ),
            )
            .outerjoin(
                MatchCollection,
                and_(
                    MatchCollection.target_collection_id
                    == TargetCollection.target_collection_id,
                    MatchCollection.sample_item_id == sample.sample_item_id,
                ),
            )
        )

        if target_collection_id:
            query = query.where(
                TargetCollection.target_collection_id == target_collection_id
            )

        result = await session.execute(query)
        rows = result.all()

        data = []
        for row in rows:
            collection_data = {
                "target_collection_id": row.TargetCollection.target_collection_id,
                "target_collection_name": row.TargetCollection.target_collection_name,
                "target_collection_description": row.TargetCollection.target_collection_description,
                "target_collection_type": row.TargetCollection.target_collection_type,
            }

            if row.MatchCollection:
                match_data = {
                    "match_collection_id": row.MatchCollection.match_collection_id,
                    "sample_item_id": row.MatchCollection.sample_item_id,
                    "match_score": row.MatchCollection.match_score,
                    "match_category": row.MatchCollection.match_category,
                    "sample_peak_intensity_sum": row.MatchCollection.sample_peak_intensity_sum,
                    "match_collection_utc_created": row.MatchCollection.match_collection_utc_created,
                    "match_collection_utc_modified": row.MatchCollection.match_collection_utc_modified,
                    "alarming": row.alarming,
                }
            else:
                match_data = {
                    "match_collection_id": None,
                    "sample_item_id": sample.sample_item_id,
                    "match_score": None,
                    "match_category": None,
                    "sample_peak_intensity_sum": None,
                    "match_collection_utc_created": None,
                    "match_collection_utc_modified": None,
                    "alarming": row.alarming,
                }

            collection_data["match"] = match_data
            data.append(collection_data)

        return data


async def _get_batch_match_collection_records(
    sample_batch: SampleBatch, target_collection_id: str | None = None
) -> list[dict]:
    """
    Retrieves target collections with placeholder match data for a batch.

    :param sample_batch: Sample batch SQLAlchemy object
    :type sample_batch: SampleBatch
    :param target_collection_id: Optional target collection filter
    :type target_collection_id: str | None
    :return: List of collection records with placeholder match data
    :rtype: list[dict]
    """
    async with async_session() as session:
        query = (
            select(
                TargetCollection,
                TargetCollection.target_collection_type.in_(
                    target_collection_config.APP_ALARMING_COLLECTION_TYPES
                ).label("alarming"),
            )
            .select_from(TargetCollection)
            .join(
                TargetCollectionInSampleBatch,
                and_(
                    TargetCollectionInSampleBatch.sample_batch_id
                    == sample_batch.sample_batch_id,
                    TargetCollectionInSampleBatch.target_collection_id
                    == TargetCollection.target_collection_id,
                ),
            )
        )

        if target_collection_id:
            query = query.where(
                TargetCollection.target_collection_id == target_collection_id
            )

        result = await session.execute(query)
        rows = result.all()

        data = []
        for row in rows:
            collection_data = {
                "target_collection_id": row.TargetCollection.target_collection_id,
                "target_collection_name": row.TargetCollection.target_collection_name,
                "target_collection_description": row.TargetCollection.target_collection_description,
                "target_collection_type": row.TargetCollection.target_collection_type,
            }

            collection_data["match"] = {
                "match_collection_id": None,
                "sample_item_id": None,
                "match_score": None,
                "match_category": None,
                "sample_peak_intensity_sum": None,
                "match_collection_utc_created": None,
                "match_collection_utc_modified": None,
                "alarming": None,
            }

            data.append(collection_data)

        return data
