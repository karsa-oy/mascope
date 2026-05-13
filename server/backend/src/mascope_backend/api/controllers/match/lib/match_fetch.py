"""
Match fetching utilities.

Provides consolidated queries for determining which match data need removal
by comparing current target isotope associations against existing match isotopes.
"""

from dataclasses import dataclass

from sqlalchemy import exists, select

from mascope_backend.api.new.ionization.modes.util import (
    fetch_batch_ionization_mechanism_ids,
    fetch_sample_ionization_mechanism_ids,
)
from mascope_backend.db import (
    IonizationMechanism,
    MatchIsotope,
    Sample,
    SampleBatch,
    TargetCollectionInSampleBatch,
    TargetCompound,
    TargetCompoundInTargetCollection,
    TargetIon,
    TargetIsotope,
    async_session,
)
from mascope_backend.runtime import runtime


@dataclass
class OrphanedMatchData:
    """
    All orphaned match data target IDs.
    Set of target references that should be removed when cleaning up orphaned
    matches.
    """

    target_isotope_ids: list[str]
    target_ion_ids: list[str]
    target_compound_ids: list[str]
    target_collection_ids: list[str]
    sample_item_ids: list[str]  # For match_samples deletion scope

    @property
    def has_orphaned_data(self) -> bool:
        """Check if any orphaned data was found."""
        return bool(self.target_isotope_ids)

    @property
    def isotopes_count(self) -> int:
        """Get count of orphaned match isotopes (base level)."""
        return len(self.target_isotope_ids)


async def fetch_sample_orphaned_match_data(sample: Sample) -> OrphanedMatchData:
    """
    Fetches orphaned match data for a specific sample.

    Detection model:
    - A MatchIsotope is orphan if no valid TargetIsotope chain reaches the
      sample's batch via TargetIon -> TargetCompound ->
      TargetCompoundInTargetCollection -> batch (with a matching ionization
      mechanism). The `NOT EXISTS(valid_targets_subquery)` clause captures this.

    NOTE Outer-join model:
    - The outer query LEFT OUTER joins TargetCompoundInTargetCollection.
      Inner-joining it would drop MatchIsotope rows whose compound has no
      junction row at all (e.g. when a compound is removed from a collection
      but its target_isotope/ion/compound rows still exist). With LEFT OUTER,
      those rows survive into the result; target_collection_id will be NULL
      for them and is filtered out before being returned.

    :param sample: Sample model object to analyze
    :type sample: Sample
    :return: Orphaned match data structure
    :rtype: OrphanedMatchData
    """
    async with async_session() as session:
        sample_ion_mechanism_ids = await fetch_sample_ionization_mechanism_ids(
            sample.sample_item_id
        )

        # subquery for valid target isotopes:
        # does a valid TargetIsotope chain reach this sample's batch?
        valid_targets_subquery = (
            select(1)
            .select_from(TargetIsotope)
            .join(TargetIon)
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
                TargetCollectionInSampleBatch,
                TargetCollectionInSampleBatch.target_collection_id
                == TargetCompoundInTargetCollection.target_collection_id,
            )
            .where(
                TargetIsotope.target_isotope_id == MatchIsotope.target_isotope_id,
                TargetCollectionInSampleBatch.sample_batch_id == sample.sample_batch_id,
                TargetIon.ionization_mechanism_id.in_(sample_ion_mechanism_ids),
            )
        )

        # Main query: get orphaned matches that don't have valid TargetIsotope
        # associations. LEFT OUTER on TargetCompoundInTargetCollection preserves
        # rows whose compound has no junction (the orphan case after
        # compound-from-collection removal).
        stmt = (
            select(
                MatchIsotope.target_isotope_id,
                TargetIon.target_ion_id,
                TargetCompound.target_compound_id,
                TargetCompoundInTargetCollection.target_collection_id,
            )
            .select_from(MatchIsotope)
            .join(
                TargetIsotope,
                TargetIsotope.target_isotope_id == MatchIsotope.target_isotope_id,
            )
            .join(TargetIon, TargetIon.target_ion_id == TargetIsotope.target_ion_id)
            .join(
                TargetCompound,
                TargetCompound.target_compound_id == TargetIon.target_compound_id,
            )
            .outerjoin(
                TargetCompoundInTargetCollection,
                TargetCompoundInTargetCollection.target_compound_id
                == TargetCompound.target_compound_id,
            )
            .where(
                MatchIsotope.sample_item_id == sample.sample_item_id,
                ~exists(valid_targets_subquery),
            )
            .distinct()
        )

        if not (rows := (await session.execute(stmt)).all()):
            runtime.logger.debug(
                f"No orphaned match data found for sample '{sample.sample_item_name}'"
            )
            return OrphanedMatchData([], [], [], [], [sample.sample_item_id])

        # Extract unique IDs. target_collection_id may be NULL for rows where the
        # compound was disassociated from all collections - skip those for the
        # collection ID list.
        target_isotope_ids = list({row.target_isotope_id for row in rows})
        target_ion_ids = list({row.target_ion_id for row in rows})
        target_compound_ids = list({row.target_compound_id for row in rows})
        target_collection_ids = list(
            {
                row.target_collection_id
                for row in rows
                if row.target_collection_id is not None
            }
        )

        runtime.logger.info(
            f"Found orphaned match data for sample '{sample.sample_item_name}': "
            f"{len(target_isotope_ids)} isotopes, {len(target_ion_ids)} ions, "
            f"{len(target_compound_ids)} compounds, "
            f"{len(target_collection_ids)} collections"
        )

        return OrphanedMatchData(
            target_isotope_ids=target_isotope_ids,
            target_ion_ids=target_ion_ids,
            target_compound_ids=target_compound_ids,
            target_collection_ids=target_collection_ids,
            sample_item_ids=[sample.sample_item_id],
        )


async def fetch_batch_orphaned_match_data(
    sample_batch: SampleBatch,
) -> OrphanedMatchData:
    """
    Fetches orphaned match data for all samples in a batch.

    Detection model:
    - A MatchIsotope is orphan if no valid TargetIsotope chain reaches the
      batch via TargetIon -> TargetCompound -> TargetCompoundInTargetCollection
      -> batch (with a matching ionization mechanism). Captured by
      `NOT EXISTS(valid_targets_subquery)`.

    NOTE Outer-join model:
    - The outer query LEFT OUTER joins TargetCompoundInTargetCollection so that
      orphan MatchIsotope rows whose compound has no junction (e.g. compound
      removed from a collection) survive into the result. target_collection_id
      is NULL for those rows and is filtered out of the returned collection-ID
      list.

    :param sample_batch: SampleBatch model object to analyze
    :type sample_batch: SampleBatch
    :return: Orphaned match data structure
    :rtype: OrphanedMatchData
    """
    async with async_session() as session:
        batch_ion_mechanism_ids = await fetch_batch_ionization_mechanism_ids(
            sample_batch.sample_batch_id
        )

        # Valid targets subquery: does a valid TargetIsotope chain reach this batch?
        valid_targets_subquery = (
            select(1)
            .select_from(TargetIsotope)
            .join(TargetIon)
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
                TargetCollectionInSampleBatch,
                TargetCollectionInSampleBatch.target_collection_id
                == TargetCompoundInTargetCollection.target_collection_id,
            )
            .join(
                Sample,
                Sample.sample_batch_id == TargetCollectionInSampleBatch.sample_batch_id,
            )
            .where(
                TargetIsotope.target_isotope_id == MatchIsotope.target_isotope_id,
                TargetCollectionInSampleBatch.sample_batch_id
                == sample_batch.sample_batch_id,
                # TODO: As is, this will only work if all samples in the batch
                # share the same ionization mechanisms
                TargetIon.ionization_mechanism_id.in_(batch_ion_mechanism_ids),
                Sample.sample_item_id == MatchIsotope.sample_item_id,
            )
        )

        # Outer query: collect orphan MatchIsotope rows with upstream target IDs.
        # LEFT OUTER on TargetCompoundInTargetCollection preserves rows whose
        # compound has no junction (compound-removed-from-collection case).
        stmt = (
            select(
                MatchIsotope.target_isotope_id,
                MatchIsotope.sample_item_id,
                TargetIon.target_ion_id,
                TargetCompound.target_compound_id,
                TargetCompoundInTargetCollection.target_collection_id,
            )
            .select_from(MatchIsotope)
            .join(Sample, Sample.sample_item_id == MatchIsotope.sample_item_id)
            .join(
                TargetIsotope,
                TargetIsotope.target_isotope_id == MatchIsotope.target_isotope_id,
            )
            .join(TargetIon, TargetIon.target_ion_id == TargetIsotope.target_ion_id)
            .join(
                TargetCompound,
                TargetCompound.target_compound_id == TargetIon.target_compound_id,
            )
            .outerjoin(
                TargetCompoundInTargetCollection,
                TargetCompoundInTargetCollection.target_compound_id
                == TargetCompound.target_compound_id,
            )
            .where(
                Sample.sample_batch_id == sample_batch.sample_batch_id,
                ~exists(valid_targets_subquery),
            )
            .distinct()
        )

        if not (rows := (await session.execute(stmt)).all()):
            # Get all sample IDs for the batch for match_samples scope
            sample_ids_stmt = select(Sample.sample_item_id).where(
                Sample.sample_batch_id == sample_batch.sample_batch_id
            )
            sample_item_ids = [row[0] for row in await session.execute(sample_ids_stmt)]

            runtime.logger.debug(
                f"No orphaned match data found for batch "
                f"'{sample_batch.sample_batch_name}'"
            )
            return OrphanedMatchData([], [], [], [], sample_item_ids)

        # Extract unique IDs. target_collection_id may be NULL for rows where the
        # compound was disassociated from all collections - skip those.
        target_isotope_ids = list({row.target_isotope_id for row in rows})
        target_ion_ids = list({row.target_ion_id for row in rows})
        target_compound_ids = list({row.target_compound_id for row in rows})
        target_collection_ids = list(
            {
                row.target_collection_id
                for row in rows
                if row.target_collection_id is not None
            }
        )
        sample_item_ids = list({row.sample_item_id for row in rows})

        runtime.logger.info(
            f"Found orphaned match data for sample batch "
            f"'{sample_batch.sample_batch_name}': "
            f"{len(target_isotope_ids)} isotopes, {len(target_ion_ids)} ions, "
            f"{len(target_compound_ids)} compounds, "
            f"{len(target_collection_ids)} collections "
            f"for {len(sample_item_ids)} samples"
        )

        return OrphanedMatchData(
            target_isotope_ids=target_isotope_ids,
            target_ion_ids=target_ion_ids,
            target_compound_ids=target_compound_ids,
            target_collection_ids=target_collection_ids,
            sample_item_ids=sample_item_ids,
        )
