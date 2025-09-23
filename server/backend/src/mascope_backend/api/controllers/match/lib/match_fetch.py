"""
Match fetching utilities.

Provides consolidated queries for determining which match data need removal
by comparing current target isotope associations against existing match isotopes.
"""

from dataclasses import dataclass

from sqlalchemy import select, exists
from mascope_backend.db import async_session
from mascope_backend.db.models import (
    Sample,
    SampleBatch,
    TargetIsotope,
    TargetIon,
    TargetCompound,
    TargetCompoundInTargetCollection,
    TargetCollectionInSampleBatch,
    IonizationMechanism,
    IonizationMode,
    MatchIsotope,
)
from mascope_backend.api.new.ionization_mode.util import (
    fetch_batch_ionization_mechanism_ids,
    fetch_sample_ionization_mechanism_ids,
)
from mascope_backend.runtime import runtime


@dataclass
class OrphanedMatchData:
    """
    All orphaned match data target IDs.
    Set of target references that should be removed when cleaning up orphaned matches.
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
    - Gets existing match_isotopes for the sample
    - Compares against current target_isotopes that should be associated with the sample
    - Determines all match data that should be removed
    - Returns hierarchical target IDs for precise deletion across all match levels.

    :param sample: Sample model object to analyze
    :type sample: Sample
    :return: Oorphaned match data structure
    :rtype: OrphanedMatchData
    """
    async with async_session() as session:
        sample_ion_mechanism_ids = await fetch_sample_ionization_mechanism_ids(
            sample.sample_item_id
        )

        # subquery for valid target isotopes
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

        # Main query: get orphaned matches that don't have valid TargetIsotope associations
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
            .join(
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

        # Extract unique IDs at each hierarchy level
        target_isotope_ids = list({row.target_isotope_id for row in rows})
        target_ion_ids = list({row.target_ion_id for row in rows})
        target_compound_ids = list({row.target_compound_id for row in rows})
        target_collection_ids = list({row.target_collection_id for row in rows})

        runtime.logger.info(
            f"Found orphaned match data for sample '{sample.sample_item_name}': "
            f"{len(target_isotope_ids)} isotopes, {len(target_ion_ids)} ions, "
            f"{len(target_compound_ids)} compounds, {len(target_collection_ids)} collections"
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

    Determines all match data across the batch that should be removed
    by comparing existing match isotopes against current target isotope
    associations for the samples in the batch.

    :param sample_batch: SampleBatch model object to analyze
    :type sample_batch: SampleBatch
    :return: Oorphaned match data structure
    :rtype: OrphanedMatchData
    """
    async with async_session() as session:
        batch_ion_mechanism_ids = await fetch_batch_ionization_mechanism_ids(
            sample_batch.sample_batch_id
        )

        # Valid targets subquery
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
                TargetIon.ionization_mechanism_id.in_(
                    batch_ion_mechanism_ids
                ),  # TODO: As is, this will only work if all samples in the batch share the same ionization mechanisms
                Sample.sample_item_id == MatchIsotope.sample_item_id,
            )
        )

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
            .join(
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
                f"No orphaned match data found for batch '{sample_batch.sample_batch_name}'"
            )
            return OrphanedMatchData([], [], [], [], sample_item_ids)

        # Extract unique IDs and affected samples
        target_isotope_ids = list({row.target_isotope_id for row in rows})
        target_ion_ids = list({row.target_ion_id for row in rows})
        target_compound_ids = list({row.target_compound_id for row in rows})
        target_collection_ids = list({row.target_collection_id for row in rows})
        sample_item_ids = list({row.sample_item_id for row in rows})

        runtime.logger.info(
            f"Found orphaned match data for sample batch '{sample_batch.sample_batch_name}': "
            f"{len(target_isotope_ids)} isotopes, {len(target_ion_ids)} ions, "
            f"{len(target_compound_ids)} compounds, {len(target_collection_ids)} collections "
            f"for {len(sample_item_ids)} samples"
        )

        return OrphanedMatchData(
            target_isotope_ids=target_isotope_ids,
            target_ion_ids=target_ion_ids,
            target_compound_ids=target_compound_ids,
            target_collection_ids=target_collection_ids,
            sample_item_ids=sample_item_ids,
        )
