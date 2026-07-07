"""
Ion-level match records service for target ions with match data.
"""

from sqlalchemy import and_, select, true

from mascope_backend.api.controllers.sample.lib.sample_batches_fetch import (
    fetch_sample_batch,
)
from mascope_backend.api.controllers.samples.lib.samples_fetch import (
    fetch_samples,
)
from mascope_backend.api.lib.api_features import api_controller
from mascope_backend.api.models.target.collections.config import (
    target_collection_config,
)
from mascope_backend.api.new.ionization.modes.util import (
    fetch_batch_ionization_mechanism_ids,
)
from mascope_backend.db import (
    IonizationMechanism,
    IonizationMode,
    MatchIon,
    Sample,
    SampleBatch,
    SampleItem,
    TargetCollection,
    TargetCollectionInSampleBatch,
    TargetCompound,
    TargetCompoundInTargetCollection,
    TargetIon,
    async_session,
)


@api_controller()
async def get_match_ion_series(
    sample_item_ids: list[str] | None = None,
    sample_batch_id: str | None = None,
    target_collection_id: str | None = None,
    target_ion_ids: list[str] | None = None,
) -> dict:
    """
    Retrieves per-sample match ion data in a compact columnar form.

    Returns one record per requested target ion carrying the ion metadata once,
    plus a `match_series` object of parallel arrays (`sample_item_ids`,
    `sample_peak_intensity_sums`, `match_categories`) holding the per-sample
    match values. Compared to the row-per-(ion, sample) shape of
    `get_match_ion_records`, this avoids repeating the ion metadata for every
    sample, which keeps chart-data responses for large batches small.

    Samples are scoped either by an explicit sample item ID list or by a
    sample batch ID (resolved via a join, so no per-sample bound parameters).
    Ions are scoped by explicit target ion IDs or by a target collection.

    :param sample_item_ids: Sample item IDs to include, defaults to None
    :type sample_item_ids: list[str] | None
    :param sample_batch_id: Sample batch whose samples to include, defaults to None
    :type sample_batch_id: str | None
    :param target_collection_id: Target collection scoping the ions, defaults to None
    :type target_collection_id: str | None
    :param target_ion_ids: Explicit target ion filter, defaults to None
    :type target_ion_ids: list[str] | None
    :return: Dictionary containing status, message, results count, and series data
    :rtype: dict
    """
    if sample_batch_id:
        sample_batch = await fetch_sample_batch(sample_batch_id)
        entity_name = sample_batch.sample_batch_name
        entity_type = "batch"
    else:
        entity_name = f"{len(sample_item_ids)} samples"
        entity_type = "samples"

    async with async_session() as session:
        # --- Ion scope ---
        ion_query = (
            select(TargetIon, TargetCompound, IonizationMechanism)
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
        )
        if target_ion_ids:
            ion_query = ion_query.where(TargetIon.target_ion_id.in_(target_ion_ids))
        else:
            ion_query = ion_query.join(
                TargetCompoundInTargetCollection,
                TargetCompoundInTargetCollection.target_compound_id
                == TargetIon.target_compound_id,
            ).where(
                TargetCompoundInTargetCollection.target_collection_id
                == target_collection_id
            )

        ion_rows = (await session.execute(ion_query)).all()
        requested_ion_ids = [row.TargetIon.target_ion_id for row in ion_rows]

        # --- Match values, one slim row per (ion, sample) ---
        match_query = select(
            MatchIon.target_ion_id,
            MatchIon.sample_item_id,
            MatchIon.sample_peak_intensity_sum,
            MatchIon.match_category,
        ).where(MatchIon.target_ion_id.in_(requested_ion_ids))
        if sample_batch_id:
            match_query = match_query.join(
                SampleItem,
                SampleItem.sample_item_id == MatchIon.sample_item_id,
            ).where(SampleItem.sample_batch_id == sample_batch_id)
        else:
            match_query = match_query.where(
                MatchIon.sample_item_id.in_(sample_item_ids)
            )

        match_rows = (await session.execute(match_query)).all()

        # --- Group match values into parallel arrays per ion ---
        series_by_ion: dict[str, dict[str, list]] = {}
        for target_ion_id, sample_item_id, intensity_sum, category in match_rows:
            series = series_by_ion.setdefault(
                target_ion_id,
                {
                    "sample_item_ids": [],
                    "sample_peak_intensity_sums": [],
                    "match_categories": [],
                },
            )
            series["sample_item_ids"].append(sample_item_id)
            series["sample_peak_intensity_sums"].append(intensity_sum)
            series["match_categories"].append(category)

        data = [
            {
                "target_compound_id": row.TargetCompound.target_compound_id,
                "target_compound_name": row.TargetCompound.target_compound_name,
                "target_compound_formula": row.TargetCompound.target_compound_formula,
                "target_ion_id": row.TargetIon.target_ion_id,
                "target_ion_formula": row.TargetIon.target_ion_formula,
                "ionization_mechanism_id": row.TargetIon.ionization_mechanism_id,
                "ionization_mechanism": row.IonizationMechanism.ionization_mechanism,
                "match_series": series_by_ion.get(
                    row.TargetIon.target_ion_id,
                    {
                        "sample_item_ids": [],
                        "sample_peak_intensity_sums": [],
                        "match_categories": [],
                    },
                ),
            }
            for row in ion_rows
        ]

    return {
        "status": "success",
        "message": (
            f"Successfully retrieved match ion series for {entity_type} '{entity_name}'"
        ),
        "results": len(data),
        "data": data,
    }


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
        # Name only small requests explicitly; batch-sized requests would bloat
        # every response message with thousands of sample names.
        if len(samples) <= 5:
            entity_name = ", ".join(sample.sample_item_name for sample in samples)
        else:
            entity_name = f"{len(samples)} samples"
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
    within the batch. The aggregation uses a LATERAL top-1 probe per requested
    target ion: each probe walks the (target_ion_id, match_score) index in
    descending score order and stops at the first row belonging to the batch,
    so the cost scales with the number of requested ions instead of every
    match row in the batch.

    Steps:
    - Get all ionization mechanism IDs used in the batch.
    - Build a subquery of the requested target ion IDs (collection/ion filters applied).
    - LATERAL-join a best-scoring-MatchIon-in-batch probe against those ions.
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
        # --- Get all ionization mechanism IDs used in the batch ---
        batch_ionization_mechanism_ids = await fetch_batch_ionization_mechanism_ids(
            sample_batch.sample_batch_id
        )

        # --- Subquery of the target ion IDs this request is actually about ---
        # Restricting the best-match aggregation to these ions keeps its cost
        # proportional to the requested collection instead of every match row
        # produced by any collection attached to the batch.
        relevant_ion_ids = (
            select(TargetIon.target_ion_id)
            .join(
                TargetCompoundInTargetCollection,
                TargetCompoundInTargetCollection.target_compound_id
                == TargetIon.target_compound_id,
            )
            .join(
                TargetCollectionInSampleBatch,
                TargetCollectionInSampleBatch.target_collection_id
                == TargetCompoundInTargetCollection.target_collection_id,
            )
            .where(
                TargetCollectionInSampleBatch.sample_batch_id
                == sample_batch.sample_batch_id,
                TargetIon.ionization_mechanism_id.in_(batch_ionization_mechanism_ids),
            )
        )
        if target_collection_id:
            relevant_ion_ids = relevant_ion_ids.where(
                TargetCompoundInTargetCollection.target_collection_id
                == target_collection_id
            )
        if target_ion_ids:
            relevant_ion_ids = relevant_ion_ids.where(
                TargetIon.target_ion_id.in_(target_ion_ids)
            )

        # --- Best MatchIon per TargetIon across the batch's samples ---
        # LATERAL top-1 probe per ion: walks the (target_ion_id, match_score)
        # index backward (descending score) and returns the first row whose
        # sample belongs to the batch. Ions without a match simply produce no
        # row and surface as NULL match data through the main query's outer join.
        relevant_ions = relevant_ion_ids.distinct().subquery("relevant_ion")
        best_match = (
            select(
                MatchIon.match_ion_id.label("sub_match_ion_id"),
                MatchIon.sample_item_id.label("sub_sample_item_id"),
                MatchIon.match_score.label("sub_match_score"),
                MatchIon.match_category.label("sub_match_category"),
                MatchIon.sample_peak_intensity_sum.label(
                    "sub_sample_peak_intensity_sum"
                ),
                MatchIon.match_ion_utc_created.label("sub_match_ion_utc_created"),
                MatchIon.match_ion_utc_modified.label("sub_match_ion_utc_modified"),
            )
            .join(
                SampleItem,
                SampleItem.sample_item_id == MatchIon.sample_item_id,
            )
            .where(
                MatchIon.target_ion_id == relevant_ions.c.target_ion_id,
                SampleItem.sample_batch_id == sample_batch.sample_batch_id,
            )
            .order_by(MatchIon.match_score.desc())
            .limit(1)
            .lateral("best_match")
        )
        matchion_best = (
            select(
                relevant_ions.c.target_ion_id.label("sub_target_ion_id"),
                best_match.c.sub_match_ion_id,
                best_match.c.sub_sample_item_id,
                best_match.c.sub_match_score,
                best_match.c.sub_match_category,
                best_match.c.sub_sample_peak_intensity_sum,
                best_match.c.sub_match_ion_utc_created,
                best_match.c.sub_match_ion_utc_modified,
            )
            .select_from(relevant_ions)
            .join(best_match, true())
            .subquery()
        )

        # --- Main query ---
        query = (
            select(
                TargetIon,
                TargetCompound,
                IonizationMechanism,
                matchion_best.c.sub_match_ion_id,
                matchion_best.c.sub_sample_item_id,
                matchion_best.c.sub_match_score,
                matchion_best.c.sub_match_category,
                matchion_best.c.sub_sample_peak_intensity_sum,
                matchion_best.c.sub_match_ion_utc_created,
                matchion_best.c.sub_match_ion_utc_modified,
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
                matchion_best,
                matchion_best.c.sub_target_ion_id == TargetIon.target_ion_id,
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
