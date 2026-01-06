"""
Target isotopes fetching utilities for match computation.

Provides consolidated queries for determining which target isotopes need match computation
by comparing current target associations against existing matches.
"""

import pandas as pd
from sqlalchemy import exists, select

from mascope_backend.api.new.ionization.modes.util import (
    fetch_sample_ionization_mechanism_ids,
)
from mascope_backend.api.new.match.params import default_match_params
from mascope_backend.db import (
    IonizationMechanism,
    MatchIsotope,
    Sample,
    TargetCollectionInSampleBatch,
    TargetCompound,
    TargetCompoundInTargetCollection,
    TargetIon,
    TargetIsotope,
    async_session,
)
from mascope_backend.runtime import runtime
from mascope_file.name import get_instrument_type
from mascope_match.params import BaseMatchParams


async def fetch_sample_unmatched_target_isotopes(
    sample: Sample,
    match_params: BaseMatchParams | None = None,
) -> pd.DataFrame:
    """
    Fetches target isotopes that need match computation for a specific sample.
    - Gets isotopes associated with sample's batch target collections
    - Filters by sample ionization mechanisms (from ionization mode)
    - Filters by sample polarity compatibility
    - Applies match parameter filtering based on sample instrument type
    - Excludes isotopes that already have matches for this sample in match_isotopes table

    :param sample: Sample model object
    :type sample: Sample
    :param match_params: Match parameters containing settings for the matching process, default to None
    :type match_params: BaseMatchParams | None
    :raises ApiException: When no targets associated with batch, no polarity-compatible targets, or all matches already exist
    :return: DataFrame of target isotopes ready for match computation
    :rtype: pd.DataFrame
    """
    if not match_params:
        match_params = await default_match_params(sample.sample_item_id)

    async with async_session() as session:
        ionization_mechanism_ids = await fetch_sample_ionization_mechanism_ids(
            sample.sample_item_id
        )

        # Determine resolution type based on instrument
        resolution_type = (
            "LOW" if (get_instrument_type(sample.filename)) == "tof" else "HIGH"
        )

        match_exists_subquery = (
            select(1)
            .select_from(MatchIsotope)
            .where(
                (MatchIsotope.target_isotope_id == TargetIsotope.target_isotope_id)
                & (MatchIsotope.sample_item_id == sample.sample_item_id)
            )
        )

        stmt = (
            select(
                TargetIsotope.target_isotope_id,
                TargetIsotope.target_ion_id,
                TargetIsotope.mz,
                TargetIsotope.relative_abundance,
                TargetIsotope.resolution,
                IonizationMechanism.ionization_mechanism_polarity,
                IonizationMechanism.ionization_mechanism,
            )
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
            .where(
                TargetCollectionInSampleBatch.sample_batch_id
                == sample.sample_batch_id,  # target collection association filtering
                TargetIon.ionization_mechanism_id.in_(
                    ionization_mechanism_ids
                ),  # sample ionization mechanism filtering
                IonizationMechanism.ionization_mechanism_polarity
                == sample.polarity,  # sample polarity filtering
                TargetIsotope.relative_abundance
                >= match_params.min_isotope_abundance,  # match_params filtering
                TargetIsotope.resolution == resolution_type,  # match_params filtering
                ~exists(match_exists_subquery),
            )
            .distinct()
        )
        if not (rows := (await session.execute(stmt)).all()):
            return pd.DataFrame()

        target_isotopes_df = pd.DataFrame([row._asdict() for row in rows])

        runtime.logger.info(
            f"Found {len(target_isotopes_df)} unmatched target isotopes for sample '{sample.sample_item_name}' "
            f"(polarity: {sample.polarity})"
        )

        return target_isotopes_df
