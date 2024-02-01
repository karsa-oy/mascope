# -------------------------------------------------------------------
# Imports
# -------------------------------------------------------------------
import pandas as pd
from datetime import datetime
from typing import Optional, List
from fastapi import HTTPException
from sqlalchemy import (
    asc,
    desc,
    and_,
    select,
    func,
    cast,
    Float,
    literal,
)

from backend.db_api_rest import async_session

from ..models.models import (
    Sample,
    Match,
    TargetCompound,
    TargetIon,
    IonizationMechanism,
    TargetIsotope,
    MatchInterference,
    TargetCompoundInTargetCollection,
    TargetCollection,
    TargetCollectionInSampleBatch,
)

from ..models.pydantic_models.sample_pydantic_model import FilterParams

# TODO_configuration
# Default Filter Parameters
DEFAULT_MZ_TOLERANCE = 15
DEFAULT_MIN_ISOTOPE_ABUNDANCE = 0.15
DEFAULT_ISOTOPE_RATIO_TOLERANCE = 0.1
DEFAULT_PEAK_MIN_INTENSITY = 0.0
DEFAULT_MIN_ISOTOPE_CORRELATION = 0.8
DEFAULT_PROBABLE_MATCH_THRESHOLD = 0.8
DEFAULT_POSSIBLE_MATCH_THRESHOLD = 0.7


# -------------------------------------------------------------------
# Utility Functions
# -------------------------------------------------------------------


def aggregate_params(df: pd.DataFrame) -> pd.Series:
    """Aggregation function no get the aggregated parameters.

    Set match_score, match_category and alarm_mode of the top row (the most alarming row).
    Sums sample_peak_area_sum/sample_peak_interference_sum for the group.

    :param df: The DataFrame containing the data to be aggregated.
    :type df: pd.DataFrame
    :return: A Pandas Series containing the aggregated values.
    :rtype: pd.Series
    """
    top_row = df.iloc[0]
    return pd.Series(
        {
            "match_score": top_row["match_score"],
            "match_category": top_row["match_category"],
            "alarm_mode": top_row["alarm_mode"],
            "sample_peak_area_sum": df["sample_peak_area_sum"].sum(),
            "sample_peak_interference_sum": df["sample_peak_interference_sum"].sum(),
        }
    )


# -------------------------------------------------------------------
# Main Logic Functions
# -------------------------------------------------------------------


async def set_ions_match_category(
    match_ions_df: pd.DataFrame, filter_params: Optional[FilterParams] = None
) -> pd.DataFrame:
    """Set the match_category field for each ion in the DataFrame.

    This function determines the match_category for each ion based on match score and predefined thresholds.
    It uses provided filters, if no filters are provided then set the ion-specific filters are used, otherwise defaults used as a fall back thresholds.


    :param match_ions_df: DataFrame containing ion data with match scores.
    :type match_ions_df: pd.DataFrame
    :param filter_params: Optional ion-specific filter parameters.
    :type filter_params: Optional[FilterParams]
    :return: DataFrame with match_category field set for each ion.
    :rtype: pd.DataFrame
    """
    for index, row in match_ions_df.iterrows():
        # Default thresholds
        probable_match_threshold = DEFAULT_PROBABLE_MATCH_THRESHOLD
        possible_match_threshold = DEFAULT_POSSIBLE_MATCH_THRESHOLD

        # Override with provided filter parameters if available
        if filter_params:
            probable_match_threshold = filter_params.probable_match_threshold
            possible_match_threshold = filter_params.possible_match_threshold

        # Use ion-specific filters if available and no filter_params provided
        instrument = row["instrument"]
        filter_params_ion = row.get("filter_params")
        if not filter_params and filter_params_ion and instrument in filter_params_ion:
            ion_filters = filter_params_ion[row["instrument"]]
            probable_match_threshold = ion_filters["probable_match_threshold"]
            possible_match_threshold = ion_filters["possible_match_threshold"]
        # Determine match_category
        match_score = row["match_score"]
        match_ions_df.at[index, "match_category"] = (
            2
            if match_score >= probable_match_threshold
            else 1
            if possible_match_threshold <= match_score < probable_match_threshold
            else 0
        )

    match_ions_df["match_category"] = match_ions_df["match_category"].astype(int)

    return match_ions_df


async def set_alarm_mode(
    dataframe: pd.DataFrame, alarms_list: List[str]
) -> pd.DataFrame:
    """
    Set the alarm_mode field for each entry in the DataFrame based on the list of provided alarms_list.

    :param dataframe: DataFrame containing sample/batch match filter data.
    :param alarms_list: List of collection types that should have alarm_mode set to True.
    :type dataframe: pd.DataFrame
    :type alarms_list: List[str]
    :return: DataFrame with alarm_mode field set.
    :rtype: pd.DataFrame
    """
    # Set alarm_mode based on whether the target_collection_type is in the alarms_list
    dataframe["alarm_mode"] = dataframe["target_collection_type"].apply(
        lambda x: True if x in alarms_list else False
    )
    return dataframe


async def aggregate_match_isotopes(
    match_filter_df: pd.DataFrame,
) -> (pd.DataFrame, pd.DataFrame):
    """Aggregate fields for matchIsotopes from the provided sample/batch match filter dataframe.

    This function processes the sample/batch match filter dataframe to aggregate isotope data.
    It prepares two DataFrames:
    1) match_isotopes_data_df with detailed data for further aggregation,
    2) match_isotopes_df with reduced data for frontend display.

    :param match_filter_df: DataFrame containing sample/batch match filter data to aggregate.
    :type match_filter_df: pd.DataFrame
    :return: Tuple of DataFrames with aggregated matchIsotopes data.
    :rtype: (pd.DataFrame, pd.DataFrame)
    """
    # Select relevant columns for detailed aggregation (backend processing)
    match_isotopes_data_df = match_filter_df.loc[
        :,
        [
            "match_score",
            "match_category",
            "alarm_mode",
            "mz",
            "match_mz_error",
            "relative_abundance",
            "match_abundance_error",
            "match_isotope_correlation",
            "sample_peak_area",
            "sample_peak_area_relative",
            "sample_peak_mz",
            "sample_peak_tof",
            "sample_peak_interference",
            "instrument",
            "filename",
            "sample_item_name",
            "sample_item_id",
            "sample_item_type",
            "target_isotope_id",
            "target_ion_id",
            "target_ion_formula",
            "target_ion_mechanism",
            "filter_params",
            "target_compound_id",
            "target_collection_id",
            "target_collection_name",
            "target_collection_description",
            "target_collection_type",
            "target_compound_name",
            "target_compound_formula",
        ],
    ]

    # Prepare a simplified DataFrame for frontend
    match_isotopes_df = match_isotopes_data_df.drop(
        columns=[
            "target_collection_id",
            "target_collection_name",
            "target_collection_description",
            "target_collection_type",
            "alarm_mode",
            "target_compound_name",
            "target_compound_formula",
            "target_ion_formula",
            "target_ion_mechanism",
            "filter_params",
            "sample_item_type",
        ]
    ).drop_duplicates(subset=["target_isotope_id", "sample_item_id"])

    return match_isotopes_data_df, match_isotopes_df


async def aggregate_match_ions(
    isotopes_df: pd.DataFrame, filter_params: Optional[FilterParams] = None
) -> (pd.DataFrame, pd.DataFrame):
    """Aggregate fields for matchIons from isotopes dataframe.
     Provided filters are passed to set_ions_match_category, if none filter_params are provided, stored ion-specidic or default params will be applied.

    This function groups the isotopes dataframe by by target_ion_id and other related field.

    It prepares two DataFrames:
    1) match_ions_data_df with detailed data for further aggregation,
    2) match_ions_df with reduced data for frontend display.

    The match_score is calculated as a weighted sum of individual isotopes' match scores, weighted by their relative abundance.
    The sample_peak_area and sample_peak_interference are summed across all isotopes in the group, the _sum is added to the field name.

    :param isotopes_df: DataFrame containing isotope data to aggregate.
    :type isotopes_df: pd.DataFrame
    :param filter_params: Optional ion-specific filter parameters to set_ions_match_category.
    :type filter_params: Optional[FilterParams]
    :return: Tuple of DataFrames with aggregated matchIons data.
    :rtype: (pd.DataFrame, pd.DataFrame)
    """
    match_ions_data_df = (
        isotopes_df.groupby(
            [
                "target_ion_formula",
                "instrument",
                "target_compound_formula",
                "target_compound_name",
                "target_ion_mechanism",
                "target_ion_id",
                "target_compound_id",
                "filename",
                "sample_item_name",
                "sample_item_type",
                "sample_item_id",
                "target_collection_id",
                "target_collection_name",
                "target_collection_description",
                "target_collection_type",
                "alarm_mode",
            ]
        )
        .agg(
            {
                "match_score": lambda x: (
                    x * isotopes_df.loc[x.index, "relative_abundance"]
                ).sum(),
                "sample_peak_area": "sum",
                "sample_peak_interference": "sum",
                "filter_params": "first",
            }
        )
        .reset_index()
        .rename(
            columns={
                "sample_peak_area": "sample_peak_area_sum",
                "sample_peak_interference": "sample_peak_interference_sum",
            }
        )
    )

    # Prepare a simplified DataFrame for frontend
    # Drop duplicates for matchIons based on target_ion_id for each sample, so each sample would have the unique matchIons (even of there is some compound in the different collections of the batch)
    match_ions_df = match_ions_data_df.drop(
        columns=[
            "target_collection_id",
            "target_collection_name",
            "target_collection_description",
            "target_collection_type",
            "alarm_mode",
            "target_compound_name",
            "target_compound_formula",
            "sample_item_type",
        ]
    ).drop_duplicates(subset=["target_ion_id", "sample_item_id"])

    # set match_category field for ions
    match_ions_data_df = await set_ions_match_category(
        match_ions_data_df, filter_params
    )
    match_ions_df = await set_ions_match_category(match_ions_df, filter_params)

    return match_ions_data_df, match_ions_df


async def aggregate_match_compounds(
    ions_df: pd.DataFrame,
) -> (pd.DataFrame, pd.DataFrame):
    """Aggregate fields for matchCompounds from ions dataframe.

    This function sorts the ions dataframe by match_category and match_score in descending order
    and then groups by target_compound_id and other relevant fields to compute the aggregated
    values for match_score, match_category, sample_peak_area_sum, and sample_peak_interference_sum.
    It preserves the highest match_score of ion from the most alarming match_category (the most alarming ion)
    and sums up the sample_peak_area_sum and sample_peak_interference_sum for the entire group.

    It prepares two DataFrames:
    1) match_compounds_data_df with detailed data for further aggregation,
    2) match_compounds_df with reduced data for frontend display.

    :param ions_df: DataFrame containing ion data to aggregate.
    :type ions_df: pd.DataFrame
    :return: pandas DataFrame with aggregated matchCompounds data.
    :rtype: pd.DataFrame
    """
    match_compounds_data_df = (
        ions_df.sort_values(
            by=["match_category", "match_score"], ascending=[False, False]
        )
        .groupby(
            [
                "target_compound_id",
                "target_compound_name",
                "target_compound_formula",
                "filename",
                "sample_item_id",
                "sample_item_name",
                "sample_item_type",
                "target_collection_id",
                "target_collection_name",
                "target_collection_description",
                "target_collection_type",
            ]
        )
        .apply(aggregate_params)
        .reset_index()
    )
    # Explicitly cast match_category to int
    match_compounds_data_df["match_category"] = match_compounds_data_df[
        "match_category"
    ].astype(int)

    # Prepare a simplified DataFrame for frontend
    # Each sample would have the unique matchCompounds (even of there is some compound in the different collections of the batch)
    match_compounds_df = match_compounds_data_df.drop(
        columns=[
            "target_collection_id",
            "target_collection_name",
            "target_collection_description",
            "target_collection_type",
            "alarm_mode",
            "sample_item_type",
        ]
    ).drop_duplicates(subset=["target_compound_id", "sample_item_id"])

    return match_compounds_data_df, match_compounds_df


async def aggregate_match_collections(compounds_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate fields for matchCollections from compounds dataframe.

    This function sorts the compounds dataframe by match_category and match_score in descending order
    and then groups by target_collection_id and other relevant fields to compute the aggregated
    values for match_score, match_category, sample_peak_area_sum, and sample_peak_interference_sum.
    It preserves the highest match_score of compound from the most alarming match_category (the most alarming compound in collection)
    and sums up the sample_peak_area_sum and sample_peak_interference_sum for the entire group.

    :param compounds_df: DataFrame containing compound data to aggregate.
    :type compounds_df: pd.DataFrame
    :return: DataFrame with aggregated matchCollections data.
    :rtype: pd.DataFrame
    """
    match_collections_df = (
        compounds_df.sort_values(
            by=["match_category", "match_score"], ascending=[False, False]
        )
        .groupby(
            [
                "sample_item_id",
                "target_collection_id",
                "target_collection_name",
                "target_collection_description",
                "target_collection_type",
            ]
        )
        .apply(aggregate_params)
        .reset_index()
    )
    # Explicitly cast match_category to int
    match_collections_df["match_category"] = match_collections_df[
        "match_category"
    ].astype(int)

    return match_collections_df


async def aggregate_match_samples(compounds_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate fields for matchSamples from compounds dataframe.

    This function sorts the compounds dataframe by  alarm_mode, match_category and match_score in descending order
    and then groups by sample_item_id and other relevant fields to compute the aggregated
    values for match_score, match_category, sample_peak_area_sum, and sample_peak_interference_sum.
    It preserves the highest match_score of compound where alarm_mode and match_category is the highest (the most alarming compound of sample)
    and sums up the sample_peak_area_sum and sample_peak_interference_sum for the entire group.

    :param compounds_df: DataFrame containing compound data to aggregate.
    :type compounds_df: pd.DataFrame
    :return: pandas DataFrame with aggregated matchSamples data.
    :rtype: pd.DataFrame
    """
    match_samples_df = (
        compounds_df.sort_values(
            by=["alarm_mode", "match_category", "match_score"],
            ascending=[False, False, False],
        )
        .drop_duplicates(subset=["target_compound_id", "sample_item_id"])
        .groupby(
            [
                "filename",
                "sample_item_id",
                "sample_item_name",
            ]
        )
        .apply(aggregate_params)
        .reset_index()
    )
    # Cast match_category to int
    match_samples_df["match_category"] = match_samples_df["match_category"].astype(int)

    return match_samples_df


async def compile_samples_df(
    samples_df: pd.DataFrame,
    match_samples_df: pd.DataFrame,
) -> pd.DataFrame:
    """Compile samples dataframe data (from database SampleView) with aggregated match results.

    This function merges the samples dataframe with the aggregated match results from the match_samples dataframe.
    It adds the match_score, match_category, sample_peak_area_sum, and sample_peak_interference_sum fields to each sample.
    The 'matched' field is calculated to indicate whether the sample has any match results.

    The aggregation logic in match_samples_df ensures that each sample's aggregated fields represent:
      - The highest match_score of compound from the most alarming match_category (the most alarming compound of sample)
      - The sum of sample_peak_area and sample_peak_interference for all compounds of the sample

    NaN values in aggregated fields are replaced with 0, indicating no matches or data for those fields.

    :param samples_df: DataFrame containing original database sample data.
    :type samples_df: pd.DataFrame
    :param match_samples_df: DataFrame containing aggregated match results for samples.
    :type match_samples_df: pd.DataFrame
    :return: DataFrame with sample data and aggregated match results.
    :rtype: pd.DataFrame
    """
    # Select relevant columns from match_samples_df
    match_samples_df_short = match_samples_df[
        [
            "sample_item_id",
            "match_score",
            "match_category",
            "alarm_mode",
            "sample_peak_area_sum",
            "sample_peak_interference_sum",
        ]
    ]

    # Merge with samples_df
    samples_df = pd.merge(
        samples_df, match_samples_df_short, how="left", on="sample_item_id"
    )

    # Add matched column
    samples_df["matched"] = samples_df["match_score"].apply(
        lambda x: 0 if pd.isna(x) else 1
    )

    # Replace NaNs with 0
    samples_df[
        [
            "match_score",
            "match_category",
            "sample_peak_area_sum",
            "sample_peak_interference_sum",
            "alarm_mode",
        ]
    ] = samples_df[
        [
            "match_score",
            "match_category",
            "sample_peak_area_sum",
            "sample_peak_interference_sum",
            "alarm_mode",
        ]
    ].fillna(
        0
    )

    return samples_df


# -------------------------------------------------------------------
# Controller or Route Handlers
# -------------------------------------------------------------------


async def get_samples(
    sample_item_id: str = None,
    sample_item_id_active: str = None,
    sample_file_id: str = None,
    sample_batch_id: str = None,
    filename: str = None,
    instrument: str = None,
    sample_item_type: str = None,
    minDatetime: datetime = None,
    maxDatetime: datetime = None,
    sort: str = "datetime_utc",
    order: str = None,
    page: int = 0,
    limit: int = 10000,
    batch_matches_info: bool = False,
    match_samples: bool = False,
    match_compounds: bool = False,
    match_ions: bool = False,
    match_isotopes: bool = False,
    alarms_list: List[str] = None,
):
    message = ""
    async with async_session() as session:
        stmt = select(Sample)

        # Query filters
        if sample_item_id:
            stmt = stmt.filter(Sample.sample_item_id == sample_item_id)

        if sample_file_id:
            stmt = stmt.filter(Sample.sample_file_id == sample_file_id)

        if sample_batch_id:
            stmt = stmt.filter(Sample.sample_batch_id == sample_batch_id)

        if filename:
            stmt = stmt.filter(Sample.filename == filename)

        if instrument:
            stmt = stmt.filter(Sample.instrument == instrument)

        if sample_item_type:
            stmt = stmt.filter(Sample.sample_item_type == sample_item_type)

        if minDatetime and maxDatetime:
            stmt = stmt.where(
                and_(
                    cast(func.julianday(Sample.datetime_utc), Float)
                    >= func.julianday(minDatetime),
                    cast(func.julianday(Sample.datetime_utc), Float)
                    <= func.julianday(maxDatetime),
                )
            )

        if sort:
            if order == "desc":
                stmt = stmt.order_by(desc(getattr(Sample, sort)))
            else:
                stmt = stmt.order_by(asc(getattr(Sample, sort)))

        # Get total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await session.scalar(count_stmt)

        # Get paginated results
        stmt = stmt.offset(page * limit).limit(limit)

        result = await session.execute(stmt)
        samples = result.scalars().all()

        # Convert samples into dataframe
        samples_df = pd.DataFrame([sample.to_dict() for sample in samples])

        #  Add 'selection' field
        if sample_item_id_active is not None:
            samples_df["selection"] = samples_df["sample_item_id"].apply(
                lambda x: 3 if x == sample_item_id_active else 0
            )
        else:
            samples_df["selection"] = 0

        if sample_batch_id:
            # Calculate and add fields match_score, sample_peak_area_sum, sample_peak_interference_sum, matched
            batch_match_filter_result = await init_batch_match_filter(sample_batch_id)

            # Convert the result to a dataframe
            batch_match_filter_dict = batch_match_filter_result["data"]
            message = batch_match_filter_result["message"]
            batch_match_filter_df = pd.DataFrame(batch_match_filter_dict)

            # Calculate matchIsotopes, matchIons, matchCompounds, matchCollections

            # If batch_match_filter_df is empty, assign None to relevant fields and continue
            if batch_match_filter_df.empty:
                samples_df[
                    [
                        "match_score",
                        "match_category",
                        "sample_peak_area_sum",
                        "sample_peak_interference_sum",
                        "matched",
                    ]
                ] = (
                    None,
                    0,
                    None,
                    None,
                    0,
                )
                result_dict = {
                    "results": total,
                    "data": samples_df.to_dict("records"),
                    "message": message,
                }
                return result_dict

            # 1) Set the alarm_mode based on alarms_list
            batch_match_filter_df = await set_alarm_mode(
                batch_match_filter_df, alarms_list
            )

            # 2) Aggregate fields for matchIsotopes
            match_isotopes_data_df, match_isotopes_df = await aggregate_match_isotopes(
                batch_match_filter_df
            )

            # 3) Aggregate fields for matchIons
            match_ions_data_df, match_ions_df = await aggregate_match_ions(
                match_isotopes_data_df
            )

            # 4) Aggregate fields for matchCompounds
            (
                match_compounds_data_df,
                match_compounds_df,
            ) = await aggregate_match_compounds(match_ions_data_df)

            # 5)  Aggregate fields for matchSamples
            # Calculate and add fields match_score, sample_peak_area_sum, sample_peak_interference_sum, matched
            match_samples_df = await aggregate_match_samples(match_compounds_data_df)

            # 6)  Merge fields for samples data
            samples_df = await compile_samples_df(samples_df, match_samples_df)

        result_dict = {
            "results": total,
            "data": samples_df.to_dict("records"),
            "message": message,
        }

        # Conditionally add match data to the result if batch_matches_info is True
        if batch_matches_info and sample_batch_id:
            batch_matches_info_dict = {"matches": {}}

            # Add each match type conditionally
            if match_samples:
                batch_matches_info_dict["matches"]["match_samples"] = len(
                    match_samples_df
                )
                batch_matches_info_dict["match_samples"] = match_samples_df.sort_values(
                    by=["match_category", "match_score"], ascending=[False, False]
                ).to_dict("records")

            if match_compounds:
                batch_matches_info_dict["matches"]["match_compounds"] = len(
                    match_compounds_df
                )
                batch_matches_info_dict[
                    "match_compounds"
                ] = match_compounds_df.sort_values(
                    by=["match_category", "match_score"], ascending=[False, False]
                ).to_dict(
                    "records"
                )

            if match_ions:
                batch_matches_info_dict["matches"]["match_ions"] = len(match_ions_df)
                batch_matches_info_dict["match_ions"] = match_ions_df.sort_values(
                    by=["match_category", "match_score"], ascending=[False, False]
                ).to_dict("records")

            if match_isotopes:
                batch_matches_info_dict["matches"]["match_isotopes"] = len(
                    match_isotopes_df
                )
                batch_matches_info_dict[
                    "match_isotopes"
                ] = match_isotopes_df.sort_values(
                    by=["match_category", "match_score"], ascending=[False, False]
                ).to_dict(
                    "records"
                )

            result_dict["batch_matches_info"] = batch_matches_info_dict

        return result_dict


async def get_sample(
    sample_item_id: str,
    alarms_list: List[str] = None,
    sample_matches_info: bool = False,
) -> dict:
    """
    Retrieves detailed information for a specific sample, including match data if requested.

    This function fetches details for a given sample identified by its sample_item_id. It can optionally calculate and include match data
    as matchIsotopes, matchIons, matchCompounds, and matchCollections, based on the sample's association with target entities.

    If the `sample_matches_info` parameter is set to False, the function will return basic sample information without performing match calculations.
    Default is True for http requests, False when called from other controllers.

    :param sample_item_id: Unique identifier for the sample.
    :type sample_item_id: str
    :param alarms_list: List of alarming collections when fetching sample information, defaults to None
    :type alarms_list: List[str], optional
    :param sample_matches_info: Flag to determine if match information should be included, defaults to False.
    :type sample_matches_info: bool, optional
    :raises HTTPException: If the sample with the specified item ID is not found.
    :return: A dictionary containing the sample information. If `sample_matches_info` is True, additional match data is included.
    :rtype: dict

    The returned dictionary includes the following keys:
    - 'data': Contains the sample information and, if requested, aggregated match data.
    - 'message': A message indicating the status of the operation.

    """
    async with async_session() as session:
        stmt = select(Sample).filter(Sample.sample_item_id == sample_item_id)
        result = await session.execute(stmt)
        sample = result.scalars().first()

        if not sample:
            raise HTTPException(
                status_code=404,
                detail=f"Sample with ID {sample_item_id} not found",
            )

        sample_dict = sample.to_dict()

        # If no match information is required, return only the sample data
        if not sample_matches_info:
            return {
                "data": sample_dict,
                "message": "Sample retrieved successfully without match information.",
            }

        # Calculate matchIsotopes, matchIons, matchCompounds, matchCollections
        sample_match_filter_result = await init_sample_match_filter(
            sample.sample_item_id
        )

        # Convert the result to a dataframe
        sample_match_filter_dict = sample_match_filter_result["data"]
        message = sample_match_filter_result["message"]
        sample_match_filter_df = pd.DataFrame(sample_match_filter_dict)

        # If sample_match_filter_df is empty, return the sample dictionary with empty fields
        if sample_match_filter_df.empty:
            sample_dict.update(
                {
                    "match_score": 0,
                    "match_category": 0,
                    "sample_peak_area_sum": 0,
                    "sample_peak_interference_sum": 0,
                    "matched": 0,
                    "selection": 3,
                    "match_collections": [],
                    "match_compounds": [],
                    "match_ions": [],
                    "match_isotopes": [],
                }
            )
            return {
                "data": sample_dict,
                "message": message,
            }

        # 1) Set the alarm_mode based on alarms_list
        sample_match_filter_df = await set_alarm_mode(
            sample_match_filter_df, alarms_list
        )

        # 2) Aggregate fields for matchIsotopes
        match_isotopes_data_df, match_isotopes_df = await aggregate_match_isotopes(
            sample_match_filter_df
        )

        # 3) Aggregate fields for matchIons
        match_ions_data_df, match_ions_df = await aggregate_match_ions(
            match_isotopes_data_df
        )

        # 4) Aggregate fields for matchCompounds
        match_compounds_data_df, match_compounds_df = await aggregate_match_compounds(
            match_ions_data_df
        )

        # 5) Aggregate fields for matchCollections
        match_collections_df = await aggregate_match_collections(
            match_compounds_data_df
        )

        # 6) Aggregate fields for sample_df
        # Convert sample into dataframe
        sample_df = pd.DataFrame([sample_dict])

        # Calculate and add fields match_score, sample_peak_area_sum, sample_peak_interference_sum, matched, selection
        match_samples_df = await aggregate_match_samples(match_compounds_data_df)

        # 7)  Merge fields for samples data
        sample_df = await compile_samples_df(sample_df, match_samples_df)

        # Add the selection field
        sample_df["selection"] = 3

        sample_dict = sample_df.to_dict(orient="records")[0]

        # Add the matches field as a dictionary
        matches = {
            "matches": {
                "match_isotopes": len(match_isotopes_df),
                "match_ions": len(match_ions_df),
                "match_compounds": len(match_compounds_df),
                "match_collections": len(match_collections_df),
            }
        }

        sample_dict.update(matches)

        # Add the aggregated dataframes to the sample dictionary
        sample_dict["match_collections"] = match_collections_df.sort_values(
            by=["match_category", "match_score"], ascending=[False, False]
        ).to_dict("records")
        sample_dict["match_compounds"] = match_compounds_df.sort_values(
            by=["match_category", "match_score"], ascending=[False, False]
        ).to_dict("records")
        sample_dict["match_ions"] = match_ions_df.sort_values(
            by=["match_category", "match_score"], ascending=[False, False]
        ).to_dict("records")
        sample_dict["match_isotopes"] = match_isotopes_df.sort_values(
            by="mz", ascending=True
        ).to_dict("records")

        return {
            "data": sample_dict,
            "message": message,
        }


async def get_sample_ion_matches(
    sample_item_id: str,
    target_ion_id: str,
    target_collection_id: str,
    filter_params: FilterParams,
    alarms_list: List[str] = None,
):
    async with async_session() as session:
        # Retrieve the sample details
        stmt = select(Sample).filter(Sample.sample_item_id == sample_item_id)
        result = await session.execute(stmt)
        sample = result.scalars().first()

        if not sample:
            raise HTTPException(
                status_code=404,
                detail=f"Sample with ID {sample_item_id} not found",
            )

        # Initialize the sample match filter with target ion and ion-specific filter parameters
        sample_match_filter_result = await init_sample_match_filter(
            sample.sample_item_id, filter_params, target_ion_id
        )

        # Convert the result to a DataFrame
        sample_match_filter_dict = sample_match_filter_result["data"]
        message = sample_match_filter_result["message"]
        sample_match_filter_df = pd.DataFrame(sample_match_filter_dict)

        # Check if the DataFrame is empty
        if sample_match_filter_df.empty:
            return {
                "data": {
                    "matches": {
                        "match_ions": 0,
                        "match_isotopes": 0,
                    },
                    "match_ions": [],
                    "match_isotopes": [],
                },
                "message": message,
            }

        # 1) Set the alarm_mode based on alarms_list
        sample_match_filter_df = await set_alarm_mode(
            sample_match_filter_df, alarms_list
        )

        # 2) Aggregate fields for matchIsotopes
        match_isotopes_data_df, _ = await aggregate_match_isotopes(
            sample_match_filter_df
        )

        # Prepare a simplified DataFrame for frontend manually to keep alarm_mode and target_collection data
        # Filter match_isotopes_df  duplicates (if compound is present in 2 different collections) based on target_collection_id
        match_isotopes_df = match_isotopes_data_df[
            match_isotopes_data_df["target_collection_id"] == target_collection_id
        ].drop(
            columns=[
                "target_collection_name",
                "target_collection_description",
                "target_compound_name",
                "target_compound_formula",
                "target_ion_formula",
                "target_ion_mechanism",
                "filter_params",
                "sample_item_type",
            ]
        )

        # 3) Aggregate fields for matchIons
        match_ions_data_df, _ = await aggregate_match_ions(
            match_isotopes_data_df, filter_params
        )

        # Prepare a simplified DataFrame for frontend manually to keep alarm_mode and target_collection data
        # Filter match_ions_df  duplicates (if compound is present in 2 different collections) based on target_collection_id
        match_ions_df = match_ions_data_df[
            match_ions_data_df["target_collection_id"] == target_collection_id
        ].drop(
            columns=[
                "target_collection_name",
                "target_collection_description",
                "target_compound_name",
                "target_compound_formula",
                "sample_item_type",
            ]
        )

        # Prepare the final output.
        return {
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
            "message": message,
        }


async def init_batch_match_filter(sample_batch_id: str):
    async with async_session() as session:
        stmt = (
            select(
                Sample.filename,
                Sample.instrument,
                Sample.sample_item_id,
                Sample.sample_item_name,
                Sample.sample_item_type,
                TargetCollection.target_collection_id,
                TargetCollection.target_collection_name,
                TargetCollection.target_collection_description,
                TargetCollection.target_collection_type,
                TargetCompound.target_compound_formula,
                TargetCompound.target_compound_id,
                TargetCompound.target_compound_name,
                TargetIon.target_ion_formula,
                TargetIon.target_ion_id,
                TargetIon.filter_params,
                IonizationMechanism.ionization_mechanism.label("target_ion_mechanism"),
                TargetIsotope.target_isotope_id,
                TargetIsotope.mz,
                TargetIsotope.relative_abundance,
                MatchInterference.sample_peak_interference,
                Match.match_mz_error,
                Match.match_abundance_error,
                Match.match_isotope_correlation,
                Match.sample_peak_area,
                Match.sample_peak_area_relative,
                Match.sample_peak_mz,
                Match.sample_peak_tof,
                Match.match_score,
            )
            .select_from(Sample)
            .where(Sample.sample_batch_id == sample_batch_id)
            .join(Match, Sample.sample_item_id == Match.sample_item_id)
            .join(
                MatchInterference,
                and_(
                    Sample.sample_item_id == MatchInterference.sample_item_id,
                    Match.target_isotope_id == MatchInterference.target_isotope_id,
                ),
            )
            .join(
                TargetIsotope,
                Match.target_isotope_id == TargetIsotope.target_isotope_id,
            )
            .join(TargetIon, TargetIsotope.target_ion_id == TargetIon.target_ion_id)
            .join(
                IonizationMechanism,
                TargetIon.ionization_mechanism_id
                == IonizationMechanism.ionization_mechanism_id,
            )
            .join(
                TargetCompound,
                TargetIon.target_compound_id == TargetCompound.target_compound_id,
            )
            .join(
                TargetCompoundInTargetCollection,
                TargetCompound.target_compound_id
                == TargetCompoundInTargetCollection.target_compound_id,
            )
            .join(
                TargetCollection,
                TargetCompoundInTargetCollection.target_collection_id
                == TargetCollection.target_collection_id,
            )
            .join(
                TargetCollectionInSampleBatch,
                TargetCollection.target_collection_id
                == TargetCollectionInSampleBatch.target_collection_id,
            )
            .where(
                and_(
                    TargetCollectionInSampleBatch.sample_batch_id
                    == Sample.sample_batch_id,
                )
            )
            .order_by(TargetIsotope.mz)
        )

        result = await session.execute(stmt)
        batch_match_filter = result.fetchall()

        # Convert each Row object in the result into a dictionary
        batch_match_filter_dict = [row._asdict() for row in batch_match_filter]

        # Filtering match_score, sample_peak_area, and setting match_category
        for row in batch_match_filter_dict:
            # Extract the instrument and filter_params from the row
            instrument = row["instrument"]
            filter_params = row.get("filter_params")
            # Determine which filter parameters to use, fall back to batch-specific filters
            if filter_params and instrument in filter_params:
                # Use ion-specific filters (unique for different instruments)
                ion_filters = filter_params[instrument]
                mz_tolerance = ion_filters["mz_tolerance"]
                min_isotope_abundance = ion_filters["min_isotope_abundance"]
                isotope_ratio_tolerance = ion_filters["isotope_ratio_tolerance"]
                peak_min_intensity = ion_filters["peak_min_intensity"]
                min_isotope_correlation = ion_filters["min_isotope_correlation"]
                probable_match_threshold = ion_filters["probable_match_threshold"]
                possible_match_threshold = ion_filters["possible_match_threshold"]
            else:
                # Use default filter parameters if target ion-specific filter_params are not provided
                mz_tolerance = DEFAULT_MZ_TOLERANCE
                min_isotope_abundance = DEFAULT_MIN_ISOTOPE_ABUNDANCE
                isotope_ratio_tolerance = DEFAULT_ISOTOPE_RATIO_TOLERANCE
                peak_min_intensity = DEFAULT_PEAK_MIN_INTENSITY
                min_isotope_correlation = DEFAULT_MIN_ISOTOPE_CORRELATION
                probable_match_threshold = DEFAULT_PROBABLE_MATCH_THRESHOLD
                possible_match_threshold = DEFAULT_POSSIBLE_MATCH_THRESHOLD

            # Apply the filters to each row
            row["match_score"] = (
                row["match_score"]
                if all(
                    [
                        abs(row["match_mz_error"]) <= mz_tolerance,
                        abs(row["match_abundance_error"]) <= isotope_ratio_tolerance,
                        max(row["match_isotope_correlation"], 0)
                        >= min_isotope_correlation,
                        row["sample_peak_area"] >= peak_min_intensity,
                        row["relative_abundance"] >= min_isotope_abundance,
                    ]
                )
                else 0
            )

            row["sample_peak_area"] = (
                row["sample_peak_area"]
                if all(
                    [
                        abs(row["match_mz_error"]) <= mz_tolerance,
                        abs(row["match_abundance_error"]) <= isotope_ratio_tolerance,
                        max(row["match_isotope_correlation"], 0)
                        >= min_isotope_correlation,
                        row["relative_abundance"] >= min_isotope_abundance,
                    ]
                )
                else 0
            )

            # Assign match category based on thresholds
            match_score = row["match_score"]
            row["match_category"] = (
                2  # Probable match
                if match_score >= probable_match_threshold
                else 1  # Possible match
                if possible_match_threshold <= match_score < probable_match_threshold
                else 0  # No match
            )

        message = (
            "Batch match filter successfully initialized"
            if len(batch_match_filter_dict) > 0
            else "No matches found for the batch"
        )
        return {
            "message": message,
            "data": batch_match_filter_dict,
        }


async def init_sample_match_filter(
    sample_item_id: str,
    filter_params: FilterParams = None,
    target_ion_id: str = None,
):
    # Provided filter params are ion-specific, apply only when the target_ion_id is provided, in other cases the stored ion-specific or DEFAULT filters are used for match_score and sample_peak_area filtering

    # Set min_isotope_abundance filter parameter to the provided one or to the DEFAULT value for query
    min_isotope_abundance = (
        filter_params.min_isotope_abundance
        if filter_params
        else DEFAULT_MIN_ISOTOPE_ABUNDANCE
    )

    async with async_session() as session:
        stmt = (
            select(
                TargetIsotope.mz,
                Match.match_mz_error,
                Match.match_abundance_error,
                Match.match_isotope_correlation,
                Match.sample_item_id,
                Match.sample_peak_area,
                Match.sample_peak_area_relative,
                Match.sample_peak_mz,
                Match.sample_peak_tof,
                MatchInterference.sample_peak_interference,
                TargetIsotope.relative_abundance,
                Sample.filename,
                Sample.instrument,
                Sample.sample_item_name,
                Sample.sample_item_type,
                TargetCollection.target_collection_id,
                TargetCollection.target_collection_name,
                TargetCollection.target_collection_description,
                TargetCollection.target_collection_type,
                TargetCompound.target_compound_formula,
                TargetCompound.target_compound_id,
                TargetCompound.target_compound_name,
                TargetIon.target_ion_formula,
                TargetIon.target_ion_id,
                TargetIon.filter_params,
                IonizationMechanism.ionization_mechanism.label("target_ion_mechanism"),
                TargetIsotope.target_isotope_id,
                literal(2).label("selection"),
                Match.match_score,
            )
            .select_from(Sample)
            .where(
                Sample.sample_item_id == sample_item_id,
            )
            .join(Match, Sample.sample_item_id == Match.sample_item_id)
            .join(
                MatchInterference,
                and_(
                    Sample.sample_item_id == MatchInterference.sample_item_id,
                    Match.target_isotope_id == MatchInterference.target_isotope_id,
                ),
            )
            .join(
                TargetIsotope,
                Match.target_isotope_id == TargetIsotope.target_isotope_id,
            )
            .join(TargetIon, TargetIsotope.target_ion_id == TargetIon.target_ion_id)
            .join(
                IonizationMechanism,
                TargetIon.ionization_mechanism_id
                == IonizationMechanism.ionization_mechanism_id,
            )
            .join(
                TargetCompound,
                TargetIon.target_compound_id == TargetCompound.target_compound_id,
            )
            .join(
                TargetCompoundInTargetCollection,
                TargetCompound.target_compound_id
                == TargetCompoundInTargetCollection.target_compound_id,
            )
            .join(
                TargetCollection,
                TargetCompoundInTargetCollection.target_collection_id
                == TargetCollection.target_collection_id,
            )
            .join(
                TargetCollectionInSampleBatch,
                TargetCollection.target_collection_id
                == TargetCollectionInSampleBatch.target_collection_id,
            )
            .where(
                and_(
                    TargetCollectionInSampleBatch.sample_batch_id
                    == Sample.sample_batch_id,
                    Match.sample_item_id == sample_item_id,
                    TargetIsotope.relative_abundance >= min_isotope_abundance,
                )
            )
            .order_by(TargetIsotope.mz)
        )

        # Apply target_ion_id filter if provided
        if target_ion_id is not None:
            stmt = stmt.where(TargetIon.target_ion_id == target_ion_id)

        result = await session.execute(stmt)
        sample_match_filter = result.fetchall()

        # Convert each Row object in the result into a dictionary
        sample_match_filter_dict = [row._asdict() for row in sample_match_filter]

        # Filtering match_score, sample_peak_area, and setting match_category
        for row in sample_match_filter_dict:
            # Extract the instrument and filter_params from the database record
            instrument = row["instrument"]
            filter_params_ion = row.get("filter_params")
            # Apply appropriate filter parameters
            # if target_ion_id and filter_params:
            if filter_params:
                # Use provided ion-specific filter parameters for specified target_ion
                mz_tolerance = filter_params.mz_tolerance
                isotope_ratio_tolerance = filter_params.isotope_ratio_tolerance
                peak_min_intensity = filter_params.peak_min_intensity
                min_isotope_correlation = filter_params.min_isotope_correlation
                probable_match_threshold = filter_params.probable_match_threshold
                possible_match_threshold = filter_params.possible_match_threshold
            elif filter_params_ion and instrument in filter_params_ion:
                # Use ion-specific filters (unique for different instruments), fall back to DEFAULT filters
                ion_filters = filter_params_ion[instrument]
                mz_tolerance = ion_filters["mz_tolerance"]
                isotope_ratio_tolerance = ion_filters["isotope_ratio_tolerance"]
                peak_min_intensity = ion_filters["peak_min_intensity"]
                min_isotope_correlation = ion_filters["min_isotope_correlation"]
                probable_match_threshold = ion_filters["probable_match_threshold"]
                possible_match_threshold = ion_filters["possible_match_threshold"]
            else:
                # Use default filters
                mz_tolerance = DEFAULT_MZ_TOLERANCE
                isotope_ratio_tolerance = DEFAULT_ISOTOPE_RATIO_TOLERANCE
                peak_min_intensity = DEFAULT_PEAK_MIN_INTENSITY
                min_isotope_correlation = DEFAULT_MIN_ISOTOPE_CORRELATION
                probable_match_threshold = DEFAULT_PROBABLE_MATCH_THRESHOLD
                possible_match_threshold = DEFAULT_POSSIBLE_MATCH_THRESHOLD

            # Apply the filters to each row
            row["match_score"] = (
                row["match_score"]
                if all(
                    [
                        abs(row["match_mz_error"]) <= mz_tolerance,
                        abs(row["match_abundance_error"]) <= isotope_ratio_tolerance,
                        max(row["match_isotope_correlation"], 0)
                        >= min_isotope_correlation,
                        row["sample_peak_area"] >= peak_min_intensity,
                    ]
                )
                else 0
            )

            row["sample_peak_area"] = (
                row["sample_peak_area"]
                if all(
                    [
                        abs(row["match_mz_error"]) <= mz_tolerance,
                        abs(row["match_abundance_error"]) <= isotope_ratio_tolerance,
                        max(row["match_isotope_correlation"], 0)
                        >= min_isotope_correlation,
                    ]
                )
                else 0
            )

            # Assign match category based on thresholds
            match_score = row["match_score"]
            row["match_category"] = (
                2  # Probable match
                if match_score >= probable_match_threshold
                else 1  # Possible match
                if possible_match_threshold <= match_score < probable_match_threshold
                else 0  # No match
            )

        if target_ion_id and filter_params:
            message = (
                "Sample match filter for target ion successfully initialized"
                if len(sample_match_filter_dict) > 0
                else "No matches found for the specified target ion in the sample"
            )
        else:
            message = (
                "Sample match filter successfully initialized"
                if len(sample_match_filter_dict) > 0
                else "No matches found for the sample"
            )

        return {
            "message": message,
            "data": sample_match_filter_dict,
        }
