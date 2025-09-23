from mascope_backend.api.new.ionization_mode.util import (
    fetch_sample_ionization_mechanism_ids,
)
import pandas as pd

from sqlalchemy import (
    select,
    and_,
)

from mascope_file.name import get_instrument_type
from mascope_match.params import BaseMatchParams

from mascope_backend.db import async_session
from mascope_backend.db.models import (
    Sample,
    SampleBatch,
    MatchIsotope,
    TargetCompound,
    TargetIon,
    IonizationMechanism,
    IonizationMode,
    TargetIsotope,
    TargetCompoundInTargetCollection,
    TargetCollection,
    TargetCollectionInSampleBatch,
)
from mascope_backend.api.lib.api_features import (
    api_controller,
)
from mascope_backend.api.lib.exceptions.api_exceptions import (
    NotFoundException,
)
from mascope_backend.api.controllers.match.lib.match_aggregate import (
    aggregate_match_isotopes,
    aggregate_match_ions,
    aggregate_match_compounds,
    aggregate_match_collections,
    aggregate_match_samples,
)
from mascope_backend.api.new.match.params import apply_match_params
from mascope_backend.api.controllers.match.lib.match_remove import remove_matches
from mascope_backend.api.controllers.sample.lib.sample_items_fetch import (
    fetch_sample_item_ids,
)
from mascope_backend.api.controllers.samples.lib.samples_fetch import fetch_sample
from mascope_backend.api.controllers.sample.lib.sample_batches_fetch import (
    fetch_sample_batch,
)
from mascope_backend.api.controllers.match.ions.match_ions_controller import (
    create_match_ions,
)
from mascope_backend.api.controllers.match.compounds.match_compounds_controller import (
    create_match_compounds,
)
from mascope_backend.api.controllers.match.collections.match_collections_controller import (
    create_match_collections,
)
from mascope_backend.api.controllers.match.samples.match_samples_controller import (
    create_match_samples,
)
from mascope_backend.api.models.match.ions.match_ion_pydantic_model import (
    MatchIonBase,
)
from mascope_backend.api.models.match.compounds.match_compound_pydantic_model import (
    MatchCompoundBase,
)
from mascope_backend.api.models.match.collections.match_collection_pydantic_model import (
    MatchCollectionBase,
)
from mascope_backend.api.models.match.samples.match_sample_pydantic_model import (
    MatchSampleBase,
)


from mascope_backend.runtime import runtime


@api_controller()
async def aggregate_match_isotope_filtered_data(
    sample_batch_id: str = None,
    sample_item_id: str = None,
    target_ion_id: str = None,
    match_params: BaseMatchParams = None,
) -> pd.DataFrame:
    async with async_session() as session:
        # Step 1: Verify existence of the entities and fetch required data
        if sample_item_id is not None:
            sample = await fetch_sample(sample_item_id)
            sample_batch_id = sample.sample_batch_id

            # Get target isotope resolution for the sample_item
            instrument_type = get_instrument_type(sample.filename)
            isotope_resolution = "LOW" if instrument_type == "tof" else "HIGH"
        else:
            isotope_resolution = None

        if target_ion_id is not None:
            ion = await session.get(TargetIon, target_ion_id)
            if not ion:
                raise NotFoundException(
                    f"Target ion with ID '{target_ion_id}' not found"
                )

        sample_batch = await session.get(SampleBatch, sample_batch_id)
        if not sample_batch:
            raise NotFoundException(
                f"Sample batch with ID '{sample_batch_id}' not found"
            )

        # Step 3: Construct and execute structured queries
        # a) Query for fetching basic samples information
        sample_query = select(
            Sample.sample_item_id,
            Sample.filename,
            Sample.instrument,
            Sample.sample_item_name,
            Sample.sample_item_type,
            Sample.polarity,
            Sample.ionization_mode_id,
        ).where(Sample.sample_batch_id == sample_batch_id)

        # Apply sample_item_id filter if provided
        if sample_item_id is not None:
            sample_query = sample_query.where(Sample.sample_item_id == sample_item_id)

        sample_result = await session.execute(sample_query)
        samples_df = pd.DataFrame([row._asdict() for row in sample_result.fetchall()])

        if samples_df.empty:
            message = (
                f"No samples found in the batch '{sample_batch.sample_batch_name}'"
            )
            runtime.logger.info(message)
            return samples_df

        sample_item_ids = samples_df["sample_item_id"].tolist()

        # Get all ionization mechanism ids related to the samples in the batch
        # TODO: Currently this does not take into account that samples may have different
        # ionization modes, and thus different ionization mechanisms.
        sample_ionization_mode_ids = samples_df["ionization_mode_id"].unique().tolist()
        sample_ionization_mechanism_ids = []
        result = await session.execute(
            select(IonizationMode.ionization_mechanism_ids).where(
                IonizationMode.ionization_mode_id.in_(sample_ionization_mode_ids)
            )
        )
        ionization_mechanism_id_lists = result.scalars().all()
        sample_ionization_mechanism_ids = list(
            set(im_id for im_list in ionization_mechanism_id_lists for im_id in im_list)
        )

        # b) Query to get relevant Target data
        target_query = (
            select(
                TargetCollection.target_collection_id,
                TargetCollection.target_collection_name,
                TargetCollection.target_collection_description,
                TargetCollection.target_collection_type,
                TargetCompound.target_compound_id,
                TargetCompound.target_compound_formula,
                TargetCompound.target_compound_name,
                TargetIon.target_ion_id,
                TargetIon.target_ion_formula,
                TargetIon.filter_params,
                IonizationMechanism.ionization_mechanism,
                TargetIsotope.target_isotope_id,
                TargetIsotope.mz,
                TargetIsotope.relative_abundance,
                TargetIsotope.resolution,
            )
            .select_from(TargetCollectionInSampleBatch)
            .where(TargetCollectionInSampleBatch.sample_batch_id == sample_batch_id)
            .join(
                TargetCollection,
                TargetCollection.target_collection_id
                == TargetCollectionInSampleBatch.target_collection_id,
            )
            .join(
                TargetCompoundInTargetCollection,
                TargetCompoundInTargetCollection.target_collection_id
                == TargetCollection.target_collection_id,
            )
            .join(
                TargetCompound,
                TargetCompound.target_compound_id
                == TargetCompoundInTargetCollection.target_compound_id,
            )
            .join(
                TargetIon,
                TargetIon.target_compound_id == TargetCompound.target_compound_id,
            )
            .join(
                IonizationMechanism,
                IonizationMechanism.ionization_mechanism_id
                == TargetIon.ionization_mechanism_id,
            )
            .where(
                IonizationMechanism.ionization_mechanism_id.in_(
                    sample_ionization_mechanism_ids
                ),
            )
            .join(
                TargetIsotope,
                TargetIsotope.target_ion_id == TargetIon.target_ion_id,
            )
        )

        if isotope_resolution is not None:
            # Filter out the isotopes of incorrect resolution
            target_query = target_query.where(
                TargetIsotope.resolution == isotope_resolution
            )

        # Apply target_ion_id filter if provided
        if target_ion_id is not None:
            target_query = target_query.where(TargetIon.target_ion_id == target_ion_id)

        target_result = await session.execute(target_query)
        targets_df = pd.DataFrame([row._asdict() for row in target_result.fetchall()])
        if targets_df.empty:
            runtime.logger.info(
                f"No targets found in the batch '{sample_batch.sample_batch_name}'"
            )
            return targets_df

        target_isotope_ids = targets_df["target_isotope_id"].tolist()

        # c. Combine sample and targets query to fetch relevant match isotopes data.
        # Fetch match isotopes
        match_isotopes_query = (
            select(
                MatchIsotope.sample_item_id,
                MatchIsotope.target_isotope_id,
                MatchIsotope.match_mz_error,
                MatchIsotope.match_abundance_error,
                MatchIsotope.match_isotope_similarity,
                MatchIsotope.sample_peak_intensity,
                MatchIsotope.sample_peak_intensity_relative,
                MatchIsotope.sample_peak_mz,
                MatchIsotope.sample_peak_tof,
                MatchIsotope.match_score,
            )
            .select_from(MatchIsotope)
            .where(
                and_(
                    MatchIsotope.sample_item_id.in_(sample_item_ids),
                    MatchIsotope.target_isotope_id.in_(target_isotope_ids),
                )
            )
        )

        match_isotopes_result = await session.execute(match_isotopes_query)
        match_isotopes_df = pd.DataFrame(match_isotopes_result.fetchall())
        if match_isotopes_df.empty:
            runtime.logger.info(
                f"No match isotopes found for the sample batch '{sample_batch.sample_batch_name}'"
            )
            return match_isotopes_df

        # Merge DataFrames
        combined_sample_match_isotopes_df = pd.merge(
            match_isotopes_df, samples_df, on="sample_item_id", how="inner"
        )
        aggregated_sample_match_isotope_data_df = pd.merge(
            combined_sample_match_isotopes_df,
            targets_df,
            on="target_isotope_id",
            how="inner",
        )

        # Define the desired column order
        column_order = [
            "sample_item_id",
            "filename",
            "instrument",
            "sample_item_name",
            "sample_item_type",
            "polarity",
            "target_collection_id",
            "target_collection_name",
            "target_collection_description",
            "target_collection_type",
            "target_compound_id",
            "target_compound_formula",
            "target_compound_name",
            "target_ion_id",
            "target_ion_formula",
            "filter_params",
            "ionization_mechanism",
            "target_isotope_id",
            "mz",
            "relative_abundance",
            "resolution",
            "match_mz_error",
            "match_abundance_error",
            "match_isotope_similarity",
            "sample_peak_intensity",
            "sample_peak_intensity_relative",
            "sample_peak_mz",
            "sample_peak_tof",
            "match_score",
        ]

        # Reorder the columns according to the defined order and sort the DataFrame by 'mz'
        aggregated_sample_match_isotope_data_df = (
            aggregated_sample_match_isotope_data_df[column_order]
            .sort_values(by="mz", kind="mergesort")
            .reset_index(drop=True)
        )

        # Step 5: Apply match_params (provided may be None) filtering match_score, sample_peak_intensity, setting match_category
        aggregated_match_isotope_filtered_data_df = apply_match_params(
            aggregated_sample_match_isotope_data_df, match_params
        )

        return aggregated_match_isotope_filtered_data_df


@api_controller()
async def aggregate_matches(
    sample_batch_id: str = None,
    sample_item_id: str = None,
    target_ion_id: str = None,
    match_params: BaseMatchParams = None,
    match_isotopes: bool = False,
) -> dict:
    # Aggregate match isotopes filtered data
    aggregated_match_isotope_filtered_data_df = (
        await aggregate_match_isotope_filtered_data(
            sample_batch_id=sample_batch_id,
            sample_item_id=sample_item_id,
            target_ion_id=target_ion_id,
            match_params=match_params,
        )
    )
    if aggregated_match_isotope_filtered_data_df.empty:
        return {"results": 0, "data": {}}

    # Aggregate match isotopes if specified (used for backwards compatibility of get_sample_and_aggregated_matches, may be removed further)
    if match_isotopes:
        _, match_isotopes_df = await aggregate_match_isotopes(
            aggregated_match_isotope_filtered_data_df
        )

    # Aggregate match ions
    match_ions_data_df, match_ions_df = await aggregate_match_ions(
        aggregated_match_isotope_filtered_data_df, match_params
    )

    # Aggregate fields for match compounds
    (
        match_compounds_data_df,
        match_compounds_df,
    ) = await aggregate_match_compounds(match_ions_data_df)

    # Aggregate fields for match collections
    match_collections_df = await aggregate_match_collections(match_compounds_data_df)

    # Aggregate fields for matchSamples
    match_samples_df = await aggregate_match_samples(match_compounds_data_df)

    # Populate the results and data with aggregated data
    aggregated_match_data_dict = {"results": {}, "data": {}}
    aggregated_match_data_dict["results"] = {
        "match_ions": len(match_ions_df),
        "match_compounds": len(match_compounds_df),
        "match_collections": len(match_collections_df),
        "match_samples": len(match_samples_df),
    }
    aggregated_match_data_dict["data"] = {
        "match_ions": match_ions_df.sort_values(
            by=["match_category", "match_score"], ascending=[False, False]
        ).to_dict("records"),
        "match_compounds": match_compounds_df.sort_values(
            by=["match_category", "match_score"], ascending=[False, False]
        ).to_dict("records"),
        "match_collections": match_collections_df.sort_values(
            by=["match_category", "match_score"], ascending=[False, False]
        ).to_dict("records"),
        "match_samples": match_samples_df.sort_values(
            by=["match_category", "match_score"], ascending=[False, False]
        ).to_dict("records"),
    }

    # Conditionally add match_isotopes to the dictionary (used for backwards compatibility of get_sample_and_aggregated_matches, may be removed further)
    if match_isotopes:
        aggregated_match_data_dict["data"]["match_isotopes"] = (
            match_isotopes_df.sort_values(
                by=["match_category", "match_score"], ascending=[False, False]
            ).to_dict("records")
        )

    return {
        "results": aggregated_match_data_dict["results"],
        "data": aggregated_match_data_dict["data"],
    }


@api_controller()
async def aggregate_and_create_matches(
    sample_batch_id: str | None = None,
    sample_item_id: str | None = None,
    target_ion_id: str | None = None,
    match_params: BaseMatchParams | None = None,
    match_ions: bool = True,
    match_compounds: bool = True,
    match_collections: bool = True,
    match_samples: bool = True,
) -> dict:
    """
    Processes aggregated match data by first aggregating data based on given filters and then creating
    entries for each type of match data.

    Steps:
    1. Aggregate match data based on the provided parameters.
    2. If data exists, create entries for each type of aggregated match data.
    3. Report on the success or lack of data for each operation.

    :param sample_batch_id: ID of the sample batch.
    :param sample_item_id: ID of the sample item.
    :param target_ion_id: ID of the target ion.
    :param match_params: Additional match parameters.
    :return: A dictionary with a message and log of actions taken.
    """
    try:
        _, sample_ref = await fetch_sample_item_ids(sample_item_id, sample_batch_id)
    except NotFoundException as e:
        return {
            "message": str(e),
        }
    # Aggregate the match data
    aggregated_result = await aggregate_matches(
        sample_batch_id=sample_batch_id,
        sample_item_id=sample_item_id,
        target_ion_id=target_ion_id,
        match_params=match_params,
    )

    if aggregated_result.get("results", 0) == 0:
        message = f"No match data found for {sample_ref}"
        return {
            "message": message,
        }

    match_data = aggregated_result.get("data", {})

    # Build operations list
    create_operations = []
    if match_ions and match_data.get("match_ions"):
        create_operations.append(
            (
                create_match_ions,
                match_data.get("match_ions", []),
                MatchIonBase,
                "match_ions",
            )
        )
    if match_compounds and match_data.get("match_compounds"):
        create_operations.append(
            (
                create_match_compounds,
                match_data.get("match_compounds", []),
                MatchCompoundBase,
                "match_compounds",
            )
        )
    if match_collections and match_data.get("match_collections"):
        create_operations.append(
            (
                create_match_collections,
                match_data.get("match_collections", []),
                MatchCollectionBase,
                "match_collections",
            )
        )
    if match_samples and match_data.get("match_samples"):
        create_operations.append(
            (
                create_match_samples,
                match_data.get("match_samples", []),
                MatchSampleBase,
                "match_samples",
            )
        )

    if not create_operations:
        message = f"No match data types selected for creation for {sample_ref}"
        runtime.logger.info(message)
        return {"message": message}

    # Execute operations
    statuses = []
    messages = []
    sample_item_ids = set()
    runtime.logger.info(f"Creating match aggregates for {sample_ref}")

    for create_func, raw_data, model_cls, level_name in create_operations:
        # Convert each data item to the corresponding Pydantic model
        model_data = [model_cls(**item) for item in raw_data]
        result = await create_func(model_data)
        statuses.append(result.get("status"))
        messages.append(f"{level_name}: {result['message']}")

        # Collect sample_item_ids from created records
        for record in result.get("data", []):
            sample_item_ids.add(record.get("sample_item_id"))

    # Determine overall status
    statuses_set = set(statuses)
    if "partial" in statuses_set or len(statuses_set) > 1:
        status = "partial"
    elif statuses_set == {"success"}:
        status = "success"
    else:  # all skipped
        status = "skipped"

    message = (
        f"Aggregate and create matches completed ({status}) for {sample_ref}: "
        + "; ".join(messages)
    )
    runtime.logger.info(message)

    return {
        "status": status,
        "message": message,
        "data": {"affected_sample_item_ids": list(sample_item_ids)},
    }


@api_controller()
async def aggregate_and_recreate_matches(
    sample_batch_id: str | None = None,
    sample_item_id: str | None = None,
    target_ion_id: str | None = None,
    match_params: BaseMatchParams | None = None,
    match_ions: bool = True,
    match_compounds: bool = True,
    match_collections: bool = True,
    match_samples: bool = True,
) -> dict:
    """
    Aggregates and re-creates match data by first removing existing aggregates based on flags,
    then aggregating and creating new entries for each type of match data.

    Used as rematching logic for match- agregated tables.

    Steps:
    1. Remove existing match data based on the provided parameters and flags.
    2. Aggregate and create match data based on the updated dataset.

    :param sample_batch_id: ID of the sample batch.
    :param sample_item_id: ID of the sample item.
    :param target_ion_id: ID of the target ion.
    :param match_params: Additional match parameters.
    :param match_ions: Controls the removal and recreation of ion match data.
    :param match_compounds: Controls the removal and recreation of compound match data.
    :param match_collections: Controls the removal and recreation of collection match data.
    :param match_samples: Controls the removal and recreation of sample match data.
    :return: A dictionary with a message and log of aggregate_and_create_matches actions.
    """
    # Step 1: Remove existing matches based on flags
    sample = None
    sample_batch = None
    if sample_item_id:
        sample = await fetch_sample(sample_item_id)
    if sample_batch_id:
        sample_batch = await fetch_sample_batch(sample_batch_id)
    await remove_matches(
        sample=sample,
        sample_batch=sample_batch,
        match_isotopes=False,
        match_ions=match_ions,
        match_compounds=match_compounds,
        match_collections=match_collections,
        match_samples=match_samples,
    )

    # Step 2: Aggregate and create new match data
    return await aggregate_and_create_matches(
        sample_batch_id=sample_batch_id,
        sample_item_id=sample_item_id,
        target_ion_id=target_ion_id,
        match_params=match_params,
        match_ions=match_ions,
        match_compounds=match_compounds,
        match_collections=match_collections,
        match_samples=match_samples,
    )
