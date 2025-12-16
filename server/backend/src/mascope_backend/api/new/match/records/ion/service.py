"""
Ion-level match records service for target ions with match data.
"""

from sqlalchemy import func, select, and_

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
    IonizationMode,
    MatchIon,
)
from mascope_backend.api.lib.api_features import api_controller
from mascope_backend.api.controllers.samples.lib.samples_fetch import (
    fetch_samples,
)
from mascope_backend.api.controllers.sample.lib.sample_items_fetch import (
    fetch_sample_item_ids,
)
from mascope_backend.api.controllers.sample.lib.sample_batches_fetch import (
    fetch_sample_batch,
)
from mascope_backend.api.new.ionization.modes.util import (
    fetch_batch_ionization_mechanism_ids,
)
from mascope_backend.api.models.target.collections.config import (
    target_collection_config,
)


@api_controller()
async def get_match_ion_records(
    sample_item_ids: list[str] | None = None,
    sample_batch_id: str | None = None,
    target_collection_id: str | None = None,
    target_ion_ids: list[str] | None = None,
) -> dict:
    """
    Retrieves target ions with match ion data for samples or a batch.

    Handles entity validation and orchestrates the data retrieval process.
    For sample-level queries, returns target ions with actual match data.
    For batch-level queries, returns target ions with batch-level aggregate match data.

    :param sample_item_ids: List of unique identifiers of the sample items, defaults to None
    :type sample_item_ids: list[str] | None
    :param sample_batch_id: Unique identifier of the sample batch, defaults to None
    :type sample_batch_id: str | None
    :param target_collection_id: Optional filter by specific target collection, defaults to None
    :type target_collection_id: str | None
    :param target_ion_ids: Optional filter by specific target ions, defaults to None
    :type target_ion_ids: list[str] | None
    :return: Dictionary containing status, message, results count, and match ion records data
    :rtype: dict
    """
    if sample_item_ids:
        samples = await fetch_samples(sample_item_ids)
        entity_name = ", ".join(sample.sample_item_name for sample in samples)
        entity_type = "samples"

        data = await _get_sample_match_ion_records(
            samples, target_collection_id, target_ion_ids
        )
    else:
        sample_batch = await fetch_sample_batch(sample_batch_id)
        entity_name = sample_batch.sample_batch_name
        entity_type = "batch"

        data = await _get_batch_match_ion_records(
            sample_batch, target_collection_id, target_ion_ids
        )

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
    samples: list[Sample],
    target_collection_id: str | None = None,
    target_ion_ids: list[str] | None = None,
) -> list[dict]:
    """
    Retrieves target ions with match ion data for a list of samples.

    :param samples: List of sample item SQLAlchemy objects
    :type samples: list[Sample]
    :param target_collection_id: Optional target collection filter
    :type target_collection_id: str | None
    :param target_ion_ids: Optional target ion filter
    :type target_ion_ids: list[str] | None
    :return: List of ion records with nested match data
    :rtype: list[dict]
    """
    async with async_session() as session:
        sample_item_ids = [sample.sample_item_id for sample in samples]
        sample_batch_ids = set([sample.sample_batch_id for sample in samples])
        sample_ionization_mode_ids = set(
            [sample.ionization_mode_id for sample in samples]
        )
        result = await session.execute(
            select(IonizationMode.ionization_mechanism_ids).where(
                IonizationMode.ionization_mode_id.in_(sample_ionization_mode_ids)
            )
        )
        ionization_mechanism_id_lists = result.scalars().all()
        sample_ionization_mechanism_ids = set(
            ion_id for id_list in ionization_mechanism_id_lists for ion_id in id_list
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
                    MatchIon.sample_item_id.in_(sample_item_ids),
                ),
            )
            .where(
                and_(
                    TargetCollectionInSampleBatch.sample_batch_id.in_(sample_batch_ids),
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

        if target_ion_ids:
            query = query.where(TargetIon.target_ion_id.in_(target_ion_ids))

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
                    "sample_item_id": None,
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
    sample_batch: SampleBatch,
    target_collection_id: str | None = None,
    target_ion_ids: list[str] | None = None,
) -> list[dict]:
    """
    Retrieves target ions with batch-level aggregate match data.

    The aggregate match data represents the best match for the ion in the samples
    within the batch. The aggregation is performed via subquery and window function.

    Steps:
    - Get all ionization mechanism IDs and sample item IDs used in the batch.
    - Construct a subquery to get the best MatchIon per TargetIon across all samples in the batch.
    - Build the main query joining TargetIon, TargetCompound, IonizationMechanism, and the subquery.
    - Apply filters for target collection and target ions if provided.
    - Process the results to format the ion and match data.

    :param sample_batch: Sample batch SQLAlchemy object
    :type sample_batch: SampleBatch
    :param target_collection_id: Optional target collection filter
    :type target_collection_id: str | None
    :param target_ion_ids: Optional target ion filter
    :type target_ion_ids: list[str] | None
    :return: List of ion records with match data
    :rtype: list[dict]
    """

    async with async_session() as session:
        # --- Get all ionization mechanism IDs and sample item IDs used in the batch ---
        batch_ionization_mechanism_ids = await fetch_batch_ionization_mechanism_ids(
            sample_batch.sample_batch_id
        )
        batch_sample_item_ids, _ = await fetch_sample_item_ids(
            sample_batch_id=sample_batch.sample_batch_id
        )

        # --- Construct a subquery to get the best MatchIon per TargetIon across
        # all samples in the batch ---
        # Fetch all MatchIon entries for samples in the batch
        matchion_subq = select(
            MatchIon.target_ion_id.label("sub_target_ion_id"),
            MatchIon.match_ion_id.label("sub_match_ion_id"),
            MatchIon.sample_item_id.label("sub_sample_item_id"),
            MatchIon.match_score.label("sub_match_score"),
            MatchIon.match_category.label("sub_match_category"),
            MatchIon.sample_peak_intensity_sum.label("sub_sample_peak_intensity_sum"),
            MatchIon.match_ion_utc_created.label("sub_match_ion_utc_created"),
            MatchIon.match_ion_utc_modified.label("sub_match_ion_utc_modified"),
        ).where(MatchIon.sample_item_id.in_(batch_sample_item_ids))
        # Use window function to assign ranks based on match_score per TargetIon
        matchion_ranked = matchion_subq.add_columns(
            func.row_number()
            .over(
                partition_by=MatchIon.target_ion_id,
                order_by=MatchIon.match_score.desc(),
            )
            .label("rn")
        ).subquery()

        # --- Main query ---
        query = (
            select(
                TargetIon,
                TargetCompound,
                IonizationMechanism,
                matchion_ranked.c.sub_match_ion_id,
                matchion_ranked.c.sub_sample_item_id,
                matchion_ranked.c.sub_match_score,
                matchion_ranked.c.sub_match_category,
                matchion_ranked.c.sub_sample_peak_intensity_sum,
                matchion_ranked.c.sub_match_ion_utc_created,
                matchion_ranked.c.sub_match_ion_utc_modified,
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
                matchion_ranked,
                and_(
                    matchion_ranked.c.sub_target_ion_id == TargetIon.target_ion_id,
                    matchion_ranked.c.rn == 1,  # Pick top match score per target ion
                ),
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

        # --- Apply filters ---
        if target_collection_id:
            query = query.where(
                TargetCollection.target_collection_id == target_collection_id
            )

        if target_ion_ids:
            query = query.where(TargetIon.target_ion_id.in_(target_ion_ids))

        # --- Execute query and process results ---
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
                "filter_params": row.TargetIon.filter_params,
            }

            # Use the best MatchIon row if present
            if row.sub_match_ion_id is not None:
                ion_data["match"] = {
                    "match_ion_id": row.sub_match_ion_id,
                    "sample_item_id": row.sub_sample_item_id,
                    "match_score": row.sub_match_score,
                    "match_category": row.sub_match_category,
                    "sample_peak_intensity_sum": row.sub_sample_peak_intensity_sum,
                    "match_ion_utc_created": row.sub_match_ion_utc_created,
                    "match_ion_utc_modified": row.sub_match_ion_utc_modified,
                    "alarming": row.alarming,
                }
            else:
                ion_data["match"] = {
                    "match_ion_id": None,
                    "sample_item_id": None,
                    "match_score": None,
                    "match_category": None,
                    "sample_peak_intensity_sum": None,
                    "match_ion_utc_created": None,
                    "match_ion_utc_modified": None,
                    "alarming": row.alarming,
                }

            data.append(ion_data)

        return data
