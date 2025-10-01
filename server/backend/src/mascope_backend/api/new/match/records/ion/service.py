"""
Ion-level match records service for target ions with match data.
"""

from sqlalchemy import select, and_

from mascope_backend.db import async_session
from mascope_backend.db.models import (
    Sample,
    SampleBatch,
    TargetCollection,
    TargetCollectionInSampleBatch,
    TargetCompoundInTargetCollection,
    TargetCompound,
    TargetIon,
    IonizationMechanism,
    MatchIon,
)
from mascope_backend.api.lib.api_features import api_controller
from mascope_backend.api.controllers.samples.lib.samples_fetch import fetch_sample
from mascope_backend.api.controllers.sample.lib.sample_batches_fetch import (
    fetch_sample_batch,
)
from mascope_backend.api.new.ionization.modes.util import (
    fetch_batch_ionization_mechanism_ids,
    fetch_sample_ionization_mechanism_ids,
)
from mascope_backend.api.models.target.collections.config import (
    target_collection_config,
)


@api_controller()
async def get_match_ion_records(
    sample_item_id: str | None = None,
    sample_batch_id: str | None = None,
    target_collection_id: str | None = None,
) -> dict:
    """
    Retrieves target ions with match ion data for sample or batch.

    Handles entity validation and orchestrates the data retrieval process.
    For sample-level queries, returns target ions with actual match data.
    For batch-level queries, returns target ions with placeholder match data.

    :param sample_item_id: Unique identifier of the sample item, defaults to None
    :type sample_item_id: str | None
    :param sample_batch_id: Unique identifier of the sample batch, defaults to None
    :type sample_batch_id: str | None
    :param target_collection_id: Optional filter by specific target collection, defaults to None
    :type target_collection_id: str | None
    :return: Dictionary containing status, message, results count, and match ion records data
    :rtype: dict
    """
    if sample_item_id:
        sample = await fetch_sample(sample_item_id)
        entity_name = sample.sample_item_name
        entity_type = "sample"

        data = await _get_sample_match_ion_records(sample, target_collection_id)
    else:
        sample_batch = await fetch_sample_batch(sample_batch_id)
        entity_name = sample_batch.sample_batch_name
        entity_type = "batch"

        data = await _get_batch_match_ion_records(sample_batch, target_collection_id)

    if not data:
        return {
            "status": "success",
            "message": f"No match ions found for {entity_type} '{entity_name}'",
            "results": 0,
            "data": [],
        }

    return {
        "status": "success",
        "message": f"Successfully retrieved match ion records for {entity_type} '{entity_name}'",
        "results": len(data),
        "data": data,
    }


async def _get_sample_match_ion_records(
    sample: Sample, target_collection_id: str | None = None
) -> list[dict]:
    """
    Retrieves target ions with match ion data for a sample.

    :param sample: Sample item SQLAlchemy object
    :type sample: Sample
    :param target_collection_id: Optional target collection filter
    :type target_collection_id: str | None
    :return: List of ion records with nested match data
    :rtype: list[dict]
    """
    async with async_session() as session:
        # Get sample ionization mechanism IDs
        sample_ionization_mechanism_ids = await fetch_sample_ionization_mechanism_ids(
            sample.sample_item_id
        )

        query = (
            select(
                TargetIon,
                TargetCompound,
                IonizationMechanism,
                MatchIon,
                TargetCollection.target_collection_type.in_(
                    target_collection_config.APP_ALARMING_COLLECTION_TYPES
                ).label("alarming"),
            )
            .select_from(TargetIon)
            .join(
                IonizationMechanism,
                IonizationMechanism.ionization_mechanism_id
                == TargetIon.ionization_mechanism_id,
            )
            .join(
                TargetCompound,
                TargetCompound.target_compound_id == TargetIon.target_compound_id,
            )
            .join(
                TargetCompoundInTargetCollection,
                TargetCompoundInTargetCollection.target_compound_id
                == TargetCompound.target_compound_id,
            )
            .join(
                TargetCollection,
                TargetCollection.target_collection_id
                == TargetCompoundInTargetCollection.target_collection_id,
            )
            .join(
                TargetCollectionInSampleBatch,
                TargetCollectionInSampleBatch.target_collection_id
                == TargetCollection.target_collection_id,
            )
            .outerjoin(
                MatchIon,
                and_(
                    MatchIon.target_ion_id == TargetIon.target_ion_id,
                    MatchIon.sample_item_id == sample.sample_item_id,
                ),
            )
            .where(
                and_(
                    TargetCollectionInSampleBatch.sample_batch_id
                    == sample.sample_batch_id,
                    TargetIon.ionization_mechanism_id.in_(
                        sample_ionization_mechanism_ids
                    ),
                )
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
            ion_data = {
                "target_compound_id": row.TargetCompound.target_compound_id,
                "target_compound_name": row.TargetCompound.target_compound_name,
                "target_compound_formula": row.TargetCompound.target_compound_formula,
                "cas_number": row.TargetCompound.cas_number,
                "target_ion_id": row.TargetIon.target_ion_id,
                "target_ion_formula": row.TargetIon.target_ion_formula,
                "ionization_mechanism_id": row.TargetIon.ionization_mechanism_id,
                "ionization_mechanism": row.IonizationMechanism.ionization_mechanism,
                "ionization_mechanism_polarity": row.IonizationMechanism.ionization_mechanism_polarity,
                "reagent": row.IonizationMechanism.reagent,
                "filter_params": row.TargetIon.filter_params,
            }

            if row.MatchIon:
                match_data = {
                    "match_ion_id": row.MatchIon.match_ion_id,
                    "sample_item_id": row.MatchIon.sample_item_id,
                    "match_score": row.MatchIon.match_score,
                    "match_category": row.MatchIon.match_category,
                    "sample_peak_intensity_sum": row.MatchIon.sample_peak_intensity_sum,
                    "match_ion_utc_created": row.MatchIon.match_ion_utc_created,
                    "match_ion_utc_modified": row.MatchIon.match_ion_utc_modified,
                    "alarming": row.alarming,
                }
            else:
                match_data = {
                    "match_ion_id": None,
                    "sample_item_id": sample.sample_item_id,
                    "match_score": None,
                    "match_category": None,
                    "sample_peak_intensity_sum": None,
                    "match_ion_utc_created": None,
                    "match_ion_utc_modified": None,
                    "alarming": row.alarming,
                }

            ion_data["match"] = match_data
            data.append(ion_data)

        return data


async def _get_batch_match_ion_records(
    sample_batch: SampleBatch, target_collection_id: str | None = None
) -> list[dict]:
    """
    Retrieves target ions with placeholder match data for a batch.

    :param sample_batch: Sample batch SQLAlchemy object
    :type sample_batch: SampleBatch
    :param target_collection_id: Optional target collection filter
    :type target_collection_id: str | None
    :return: List of ion records with placeholder match data
    :rtype: list[dict]
    """
    async with async_session() as session:
        # Get all batch ionization mechanism IDs (used for any sample in batch)
        batch_ionization_mechanism_ids = await fetch_batch_ionization_mechanism_ids(
            sample_batch.sample_batch_id
        )

        query = (
            select(
                TargetIon,
                TargetCompound,
                IonizationMechanism,
                TargetCollection.target_collection_type.in_(
                    target_collection_config.APP_ALARMING_COLLECTION_TYPES
                ).label("alarming"),
            )
            .select_from(TargetIon)
            .join(
                IonizationMechanism,
                IonizationMechanism.ionization_mechanism_id
                == TargetIon.ionization_mechanism_id,
            )
            .join(
                TargetCompound,
                TargetCompound.target_compound_id == TargetIon.target_compound_id,
            )
            .join(
                TargetCompoundInTargetCollection,
                TargetCompoundInTargetCollection.target_compound_id
                == TargetCompound.target_compound_id,
            )
            .join(
                TargetCollection,
                TargetCollection.target_collection_id
                == TargetCompoundInTargetCollection.target_collection_id,
            )
            .join(
                TargetCollectionInSampleBatch,
                TargetCollectionInSampleBatch.target_collection_id
                == TargetCollection.target_collection_id,
            )
            .where(
                and_(
                    TargetCollectionInSampleBatch.sample_batch_id
                    == sample_batch.sample_batch_id,
                    TargetIon.ionization_mechanism_id.in_(
                        batch_ionization_mechanism_ids
                    ),
                )
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
            ion_data = {
                "target_compound_id": row.TargetCompound.target_compound_id,
                "target_compound_name": row.TargetCompound.target_compound_name,
                "target_compound_formula": row.TargetCompound.target_compound_formula,
                "cas_number": row.TargetCompound.cas_number,
                "target_ion_id": row.TargetIon.target_ion_id,
                "target_ion_formula": row.TargetIon.target_ion_formula,
                "ionization_mechanism_id": row.TargetIon.ionization_mechanism_id,
                "ionization_mechanism": row.IonizationMechanism.ionization_mechanism,
                "ionization_mechanism_polarity": row.IonizationMechanism.ionization_mechanism_polarity,
                "reagent": row.IonizationMechanism.reagent,
                "filter_params": row.TargetIon.filter_params,
            }

            ion_data["match"] = {
                "match_ion_id": None,
                "sample_item_id": None,
                "match_score": None,
                "match_category": None,
                "sample_peak_intensity_sum": None,
                "match_ion_utc_created": None,
                "match_ion_utc_modified": None,
                "alarming": None,
            }

            data.append(ion_data)

        return data
