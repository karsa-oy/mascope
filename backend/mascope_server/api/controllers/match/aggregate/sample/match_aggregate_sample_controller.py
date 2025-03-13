import pandas as pd
from sqlalchemy import (
    select,
)
from mascope_lib.util import norm
from mascope_server.db.id import gen_id
from mascope_server.db import async_session
from mascope_server.db.models import (
    SampleBatch,
    TargetCompound,
    TargetIon,
    IonizationMechanism,
)
from mascope_server.api.lib.api_features import api_controller
from mascope_server.api.lib.exceptions.api_exceptions import NotFoundException
from mascope_server.api.controllers.target.ions.target_ions_controller import (
    create_target_ions,
)
from mascope_server.api.controllers.samples.lib.samples_fetch import fetch_sample
from mascope_server.api.new.match.params import apply_match_params
from mascope_server.api.controllers.match.lib.match_compute import (
    compute_match_isotopes,
)
from mascope_server.api.controllers.match.lib.match_aggregate import (
    aggregate_match_ions,
    aggregate_match_ions_light,
    aggregate_match_compounds_light,
    compile_samples_df,
)
from mascope_server.api.controllers.match.aggregate.match_aggregate_controller import (
    aggregate_match_isotope_filtered_data,
    aggregate_matches,
)
from mascope_server.api.new.match.params import BaseMatchParams, default_match_params


@api_controller()
async def aggregate_sample_match_ion(
    sample_item_id: str,
    target_ion_id: str,
    target_collection_id: str,
    match_params: BaseMatchParams,
) -> dict:
    """
    Aggregates ion-specific match information for a given sample item by fetching match data at the isotope level,
    applying the provided filter parameters, and returning aggregated match data for ions and isotopes.

    Key Points:
    - Ion-specific `match_params` are required; stored or default parameters are NOT used for filtering.
    - The function directly processes the aggregated match isotope data without unnecessary intermediate steps.

    Steps:
    1. Verify the existence of the specified sample item and target ion.
    2. Aggregate and filter the match data at the isotopic level using the provided filter parameters.
    3. If the DataFrame is empty, return a response indicating no matches were found.
    4. Filter the aggregated match isotopes data by `target_collection_id` to remove potential duplicates.
    5. Aggregate the data for match ions and filter it by `target_collection_id`.
    6. Prepare the final output, including the counts and details of matched ions and isotopes.

    :param sample_item_id: ID of the sample item for which to retrieve ion matches.
    :type sample_item_id: str
    :param target_ion_id: ID of the target ion for which matches are filtered.
    :type target_ion_id: str
    :param target_collection_id: ID of the target collection to filter out duplicates.
    :type target_collection_id: str
    :param match_params: Ion-specific filter parameters for match score and sample peak area filtering.
    :type match_params: BaseMatchParams
    :return: Dictionary containing aggregated match information for ions and isotopes.
    :rtype: dict
    """
    async with async_session() as session:
        # Step 1: Fetch sample and target ion to verify its existence
        sample = await fetch_sample(sample_item_id)
        ion = await session.get(TargetIon, target_ion_id)
        if not ion:
            raise NotFoundException(f"Target ion with ID '{target_ion_id}' not found")

        # Step 2: Aggregate and filter match data at the isotope level using the provided filter parameters
        aggregated_match_isotope_filtered_data_df = (
            await aggregate_match_isotope_filtered_data(
                sample_item_id=sample.sample_item_id,
                target_ion_id=target_ion_id,
                match_params=match_params,
            )
        )

        # Step 3: Check if the DataFrame is empty
        if aggregated_match_isotope_filtered_data_df.empty:
            return {
                "matches": {
                    "match_ions": 0,
                    "match_isotopes": 0,
                },
                "match_ions": [],
                "match_isotopes": [],
            }

        # Step 4: Filter and prepare match isotope data
        # Filter match_isotopes_df  duplicates (if compound is present in 2 different collections) based on target_collection_id
        match_isotopes_df = aggregated_match_isotope_filtered_data_df[
            aggregated_match_isotope_filtered_data_df["target_collection_id"]
            == target_collection_id
        ].drop(
            columns=[
                "sample_item_type",
                "target_collection_name",
                "target_collection_description",
                "target_compound_name",
                "target_compound_formula",
                "target_ion_formula",
                "filter_params",
                "ionization_mechanism",
            ]
        )

        # Step 5: Aggregate fields for match ions and filter duplicates based on target_collection_id
        match_ions_data_df, _ = await aggregate_match_ions(
            aggregated_match_isotope_filtered_data_df, match_params
        )
        match_ions_df = match_ions_data_df[
            match_ions_data_df["target_collection_id"] == target_collection_id
        ].drop(
            columns=[
                "target_collection_description",
                "target_compound_name",
                "target_compound_formula",
                "sample_item_type",
            ]
        )

        # Step 6: Prepare the final output
        if len(match_ions_df) and len(match_isotopes_df):
            message = "Match information retrieved successfully"
        else:
            message = "No matches found for the specified criteria"

        return {
            "message": message,
            "data": {
                "matches": {
                    "match_ions": len(match_ions_df),
                    "match_isotopes": len(match_isotopes_df),
                },
                "match_ions": match_ions_df.sort_values(
                    by=["match_category", "match_score"], ascending=[False, False]
                ).to_dict("records"),
                "match_isotopes": match_isotopes_df.sort_values(
                    by="mz", ascending=True
                ).to_dict("records"),
            },
        }


@api_controller()
async def aggregate_sample_match_compound(
    sample_item_id: str,
    target_compound_formula: str,
    match_params: BaseMatchParams | None = None,
    target_compound_name: str = "Unknown Compound",
) -> dict:
    """
    Retrieves matches for compounds within a sample based on a target compound formula,
    applying specified match parameters to filter the matches.

    Steps:
    1. Verify the existence of the sample and its batch, extract ion mechanisms.
    2. Prepare the target compound by normalizing its formula and creating a target compound instance.
    3. Generate and create target ions and isotopes for the compound.
    4. Compute matches for the created isotopes within the sample file.
    5. Apply filters to the computed isotope matches based on the provided parameters.
    6. Aggregate ion-level data from the filtered isotopes.
    7. Aggregate compound-level data from the ions and merge with target compound information.

    :param sample_item_id: Unique identifier of the sample item to analyze.
    :type sample_item_id: str
    :param target_compound_formula: Chemical formula of the target compound.
    :type target_compound_formula: str
    :param target_compound_name: The name of the target compound
    :type target_compound_name: str
    :param match_params: Parameters to filter the match results, affecting which matches are considered significant
    :type match_params: BaseMatchParams
    :raises NotFoundException: Raised if the sample item or sample batch cannot be found.
    :raises ValueError: Raised if no ion mechanisms are defined for the sample batch.
    :return: A dictionary containing aggregated match compounds, ions, and isotopes, each as a list of dictionaries.
    :rtype: dict
    """
    # match param defaults depend on instrument
    # so we use a helper to infer them:
    if not match_params:
        match_params = await default_match_params(sample_item_id)
    # data retrieval
    async with async_session() as session:
        # Step 1: Fetch sample related data and verify its existence
        sample = await fetch_sample(sample_item_id)

        # Fetch sample batch data and verify its existence
        sample_batch = await session.get(SampleBatch, sample.sample_batch_id)
        if not sample_batch:
            raise NotFoundException(
                f"Sample batch with ID '{sample.sample_batch_id}' not found"
            )

        # Extract ion_mechanisms IDs from build_params
        ion_mechanisms_ids = sample_batch.build_params.get("ion_mechanisms", [])
        if not ion_mechanisms_ids:
            raise ValueError(
                f"There are no ion mechanisms for sample batch '{sample_batch.sample_batch_name}'."
            )

        # Fetch the ionization mechanisms from the database using the extracted IDs
        restult = await session.execute(
            select(IonizationMechanism).filter(
                IonizationMechanism.ionization_mechanism_id.in_(ion_mechanisms_ids)
            )
        )
        ionization_mechanisms = restult.scalars().all()
        if not ionization_mechanisms:
            raise NotFoundException(
                f"Ionization mechanisms with IDs {ion_mechanisms_ids} not found"
            )

        # Step 2: Prepare target compound
        # Normalize the compound formula for consistency
        normalized_formula = norm(target_compound_formula)

        # Attempt to parse the target compound formula as a mass if applicable
        try:
            target_compound_mass = float(normalized_formula)
        except ValueError:
            target_compound_mass = None  # If parsing fails, proceed without a mass

        # Initialize the target compound with the normalized formula
        target_compound = TargetCompound(
            target_compound_id=gen_id(),
            target_compound_name=target_compound_name,
            target_compound_formula=normalized_formula,
        )

        # Step 3: Generate and create target ions and isotopes.
        # Create target ions for the compound
        ion_creation_result = await create_target_ions(
            target_compound=target_compound,
            ionization_mechanisms=ionization_mechanisms,
            target_compound_mass=target_compound_mass,
            independent_transaction=False,
            session=session,
        )

        # Convert 'created_ions' list into a DataFrame
        created_ions_df = pd.DataFrame(ion_creation_result["created_ions"])
        # Convert created isotopes to pandas DataFrame
        target_isotopes_df = pd.DataFrame(ion_creation_result["created_isotopes"])

        # Step 4: Compute matches for the isotopes in the sample file.
        match_isotope_df = await compute_match_isotopes(
            filename=sample.filename,
            target_isotopes_df=target_isotopes_df,
            min_isotope_abundance=match_params.min_isotope_abundance,
        )

        # Drop the 'index' column from the match_isotope_df DataFrame
        match_isotope_df = match_isotope_df.drop(columns=["index"])
        # Step 5: Apply filters to the computed isotope matches based on the provided parameters.
        filtered_match_isotope_df = apply_match_params(match_isotope_df, match_params)

        # Step 6: Aggregate ion-level data from the filtered isotopes.
        match_ions_data_df = aggregate_match_ions_light(filtered_match_isotope_df)
        match_ions_df = pd.merge(
            match_ions_data_df, created_ions_df, on="target_ion_id", how="left"
        )

        # Step 7: Aggregate compound-level data from the ions and merge with target compound information.
        match_compounds_data_df = aggregate_match_compounds_light(match_ions_df)

        # Convert the dictionary into a DataFrame
        target_compound_df = pd.DataFrame([target_compound.to_dict()])

        # Merge match_compounds_data_df with target_compound_df
        merged_match_compounds_df = pd.merge(
            match_compounds_data_df,
            target_compound_df,
            on="target_compound_id",
            how="left",
        )

        # Step 6: Prepare the final output
        if len(merged_match_compounds_df) > 0:
            message = f"Match information for compound '{target_compound_formula}' retrieved successfully"
        else:
            message = f"No matches found for the specified compound '{target_compound_formula}'"

        return {
            "message": message,
            "data": {
                "match_compounds": merged_match_compounds_df.to_dict("records"),
                "match_ions": match_ions_df.to_dict("records"),
                "match_isotopes": filtered_match_isotope_df.to_dict("records"),
            },
        }


@api_controller()
async def get_sample_and_aggregated_matches(
    sample_item_id: str,
) -> dict:
    """
    Retrieves detailed information for a specific sample, including aggregated match data for isotopes, ions,
    compounds, and collections. This function is an updated version of the deprecated `get_sample_aggregate_matches` (old get_sample)

    NOTE: This function is currently deprecated and may be removed in the future. It is being retained temporarily for testing purposes and is not used in the current frontend of mascope.

    Steps:
    1. Fetch the sample using the provided sample item ID to ensure it exists.
    2. Aggregate match data for the sample, including isotopes, ions, compounds, and collections, using the new aggregation controllers.
    3. If no match data is found, return a message indicating the absence of match data.
    4. Compile the sample data, merging it with the aggregated match data.
    5. Prepare the final output, including the sample data and aggregated match details, and return it in a structured dictionary format.

    :param sample_item_id: Unique identifier for the sample.
    :type sample_item_id: str
    :raises NotFoundException: If the sample with the specified item ID is not found.
    :return: A dictionary containing the sample information and aggregated match data.
    :rtype: dict
    """
    # Step 1: Fetch sample to verify its existence
    sample = await fetch_sample(sample_item_id)

    sample_dict = sample.to_dict()

    # Step 2: Aggregate the match data using the new aggregation controllers
    aggregated_result = await aggregate_matches(
        sample_item_id=sample_item_id, match_isotopes=True
    )

    if aggregated_result.get("results", 0) == 0:
        message = f"No match data found for sample '{sample.sample_item_name}'"
        return {
            "message": message,
        }

    # Step 3: Unpack the aggregated match data
    match_data = aggregated_result.get("data", {})
    match_isotopes = match_data.get("match_isotopes", [])
    match_ions = match_data.get("match_ions", [])
    match_compounds = match_data.get("match_compounds", [])
    match_collections = match_data.get("match_collections", [])
    match_samples = match_data.get("match_samples", [])

    # Step 4: Compile the sample data, merging it with the aggregated match data
    sample_df = pd.DataFrame([sample_dict])
    match_samples_df = pd.DataFrame(match_samples)
    sample_df = await compile_samples_df(sample_df, match_samples_df)

    # Step 5: Prepare the final output
    result = {}
    result["sample"] = sample_df.to_dict(orient="records")[0]

    # Add the matches field as a dictionary
    matches = {
        "matches": {
            "match_isotopes": len(match_isotopes),
            "match_ions": len(match_ions),
            "match_compounds": len(match_compounds),
            "match_collections": len(match_collections),
        }
    }

    result.update(matches)

    # Add the aggregated dataframes to the sample dictionary
    result["match_collections"] = match_collections
    result["match_compounds"] = match_compounds
    result["match_ions"] = match_ions
    result["match_isotopes"] = match_isotopes

    return result
