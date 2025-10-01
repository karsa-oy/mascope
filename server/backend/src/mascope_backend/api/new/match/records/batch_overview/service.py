"""
Batch overview match records service for chart visualization.

Returns flattened records optimized for trace building - minimal data,
pre-joined, filtered by match validity (match_category > 0).
"""

from sqlalchemy import select, and_

from mascope_backend.db import async_session
from mascope_backend.db.models import (
    Sample,
    TargetCollection,
    TargetCollectionInSampleBatch,
    TargetCompoundInTargetCollection,
    TargetCompound,
    TargetIon,
    IonizationMechanism,
    MatchIon,
)
from mascope_backend.api.lib.api_features import api_controller
from mascope_backend.api.controllers.sample.lib.sample_batches_fetch import (
    fetch_sample_batch,
)


@api_controller()
async def get_batch_overview_match_records(
    sample_batch_id: str,
    target_collection_id: str,
) -> dict:
    """
    Retrieves match records for batch overview chart visualization.

    Returns flattened records with minimal data needed for trace building:
    - One record per sample-ion combination where valid match exists
    - Pre-filtered by match_category > 0
    - Includes compound/ion metadata for trace naming
    - Optimized for frontend grouping by target_ion_id

    :param sample_batch_id: Unique identifier of the sample batch
    :type sample_batch_id: str
    :param target_collection_id: Filter by specific target collection
    :type target_collection_id: str
    :return: Dictionary containing status, message, results count, and flattened match records
    :rtype: dict
    """
    sample_batch = await fetch_sample_batch(sample_batch_id)

    async with async_session() as session:
        # Query: Join all relevant entities for batch samples
        query = (
            select(
                Sample.sample_item_id,
                TargetIon.target_ion_id,
                TargetIon.target_ion_formula,
                TargetCompound.target_compound_name,
                TargetCompound.target_compound_formula,
                IonizationMechanism.ionization_mechanism,
                MatchIon.match_ion_id,
                MatchIon.sample_peak_intensity_sum,
                MatchIon.match_category,
                MatchIon.match_score,
            )
            .select_from(Sample)
            .join(
                MatchIon,
                MatchIon.sample_item_id == Sample.sample_item_id,
            )
            .join(
                TargetIon,
                TargetIon.target_ion_id == MatchIon.target_ion_id,
            )
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
                    Sample.sample_batch_id == sample_batch_id,
                    TargetCollection.target_collection_id == target_collection_id,
                    TargetCollectionInSampleBatch.sample_batch_id == sample_batch_id,
                    MatchIon.match_category > 0,  # Only valid matches for chart
                )
            )
        )

        result = await session.execute(query)
        rows = result.all()

        # Build flat records optimized for frontend trace grouping
        data = [
            {
                # Identifiers (for mapping and focusing)
                "sample_item_id": row.sample_item_id,
                "target_ion_id": row.target_ion_id,
                "match_ion_id": row.match_ion_id,
                # Display data (for trace building)
                "target_ion_formula": row.target_ion_formula,
                "target_compound_name": row.target_compound_name,
                "target_compound_formula": row.target_compound_formula,
                "ionization_mechanism": row.ionization_mechanism,
                # Chart data (for plotting)
                "sample_peak_intensity_sum": (
                    float(row.sample_peak_intensity_sum)
                    if row.sample_peak_intensity_sum
                    else None
                ),
                "match_category": row.match_category,
                # unused in chart, but useful for debugging
                "match_score": float(row.match_score) if row.match_score else None,
            }
            for row in rows
        ]
    message = f"Successfully retrieved {len(data)} batch overview match ion records for batch '{sample_batch.sample_batch_name}'"
    return {
        "status": "success",
        "message": message,
        "results": len(data),
        "data": data,
    }
