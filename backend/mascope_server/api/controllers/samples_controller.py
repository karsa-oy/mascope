# -------------------------------------------------------------------
# Imports
# -------------------------------------------------------------------
from datetime import datetime
from typing import List, Optional, Tuple
import pandas as pd
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
from mascope_lib.util import norm
from mascope_server.db.id import gen_id
from mascope_server.db import async_session
from ..utils.api_features import api_controller
from ..exceptions import NotFoundException
from .target_ions_controller import create_target_ions
from .matches_controller import compute_matches
from ..models.models import (
    Sample,
    SampleBatch,
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
from ..models.pydantic_models.sample_pydantic_model import FilterParams, AlarmsList

# TODO_configuration
# Default Filter Parameters
DEFAULT_MZ_TOLERANCE = 15
DEFAULT_MIN_ISOTOPE_ABUNDANCE = 0.15
DEFAULT_ISOTOPE_RATIO_TOLERANCE = 0.15
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


def apply_filter_params(matches_df, filter_params: FilterParams = None):
    """
    Apply filtering logic to a isotope-lvl matches DataFrame.

    :param matches_df: DataFrame containing match data.
    :type matches_df: pd.DataFrame
    :param filter_params: Optional; Pydantic model of filtering parameters.
    :type filter_params: FilterParams
    :return: DataFrame with applied filters.
    :rtype: pd.DataFrame
    """
    # Convert filter_params Pydantic model to dictionary if provided
    provided_params = filter_params.dict() if filter_params else None

    def get_params(row):
        """
        Determine the filter parameters to use based on the priority:
        1. Provided filter parameters
        2. Ion-specific filter parameters for the sample instrument
        3. Default filter parameters
        """
        # If provided_params are available, use them for all rows
        if provided_params:
            return provided_params

        # If row-specific filter_params are available for the instrument, use them
        if "filter_params" in row and row["instrument"] in row["filter_params"]:
            return row["filter_params"][row["instrument"]]

        # Define default filter parameters from the FilterParams Pydantic model
        default_params = FilterParams().dict()
        # Fallback to default parameters
        return default_params

    def filter_row(row):
        """
        Apply filtering logic to the given row based on the determined parameters.
        """
        # Determine which filter parameters to use for the current row
        params = get_params(row)

        # Apply filtering logic
        row["match_score"] = (
            row["match_score"]
            if all(
                [
                    abs(row["match_mz_error"]) <= params["mz_tolerance"],
                    abs(row["match_abundance_error"])
                    <= params["isotope_ratio_tolerance"],
                    max(row.get("match_isotope_correlation", 0), 0)
                    >= params["min_isotope_correlation"],
                    row["sample_peak_area"] >= params["peak_min_intensity"],
                    row["relative_abundance"] >= params["min_isotope_abundance"],
                ]
            )
            else 0
        )

        row["sample_peak_area"] = (
            row["sample_peak_area"]
            if all(
                [
                    abs(row["match_mz_error"]) <= params["mz_tolerance"],
                    abs(row["match_abundance_error"])
                    <= params["isotope_ratio_tolerance"],
                    max(row.get("match_isotope_correlation", 0), 0)
                    >= params["min_isotope_correlation"],
                    row["relative_abundance"] >= params["min_isotope_abundance"],
                ]
            )
            else 0
        )

        # Determine match category based on match_score
        match_score = row["match_score"]
        row["match_category"] = (
            2  # Probable match
            if match_score >= params["probable_match_threshold"]
            else (
                1  # Possible match
                if match_score >= params["possible_match_threshold"]
                else 0
            )  # No match
        )

        return row

    # Apply the filtering logic to each row
    filtered_df = matches_df.apply(filter_row, axis=1)

    return filtered_df


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
            else (
                1
                if possible_match_threshold <= match_score < probable_match_threshold
                else 0
            )
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
) -> Tuple[pd.DataFrame, pd.DataFrame]:
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
) -> Tuple[pd.DataFrame, pd.DataFrame]:
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
    # Drop duplicates for matchIons based on target_ion_id for each sample, so each sample would have the unique matchIons
    # (even of there is some compound in the different collections of the batch)
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


def aggregate_match_ions_simple(
    filtered_match_isotope_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Aggregate fields for match ions from the filtered match isotope DataFrame.
    Used in the get_sample_compound_matches to aggregate simpler match_isotope_df from compute_matches.

    This function groups the filtered match isotope DataFrame by 'target_ion_id' and aggregates relevant data,
    such as summing up 'sample_peak_area' and computing a weighted 'match_score'.

    :param filtered_match_isotope_df: DataFrame containing filtered match isotope data.
    :type filtered_match_isotope_df: pd.DataFrame
    :return: DataFrame with aggregated match ions data.
    :rtype: pd.DataFrame
    """
    match_ions_df = (
        filtered_match_isotope_df.groupby("target_ion_id")
        .agg(
            match_score=(
                "match_score",
                lambda x: (
                    x * filtered_match_isotope_df.loc[x.index, "relative_abundance"]
                ).sum(),
            ),
            sample_peak_area_sum=("sample_peak_area", "sum"),
        )
        .reset_index()
    )

    return match_ions_df


async def aggregate_match_compounds(
    ions_df: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
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


def aggregate_match_compounds_simple(match_ions_df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate fields for match compounds from the match ions DataFrame.
    Used in the get_sample_compound_matches to aggregate simpler match_ions_df from aggregate_match_ions_simple.

    This function groups the match ions DataFrame by 'target_compound_id' and aggregates relevant data,
    such as computing a weighted 'match_score' and summing up 'sample_peak_area'.

    :param match_ions_df: DataFrame containing match ions data.
    :type match_ions_df: pd.DataFrame
    :return: DataFrame with aggregated match compounds data.
    :rtype: pd.DataFrame
    """
    match_compounds_df = (
        match_ions_df.groupby("target_compound_id")
        .agg(
            match_score=("match_score", "max"),
            sample_peak_area_sum=("sample_peak_area_sum", "sum"),
        )
        .reset_index()
    )

    return match_compounds_df


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
            "tic",
            "match_score",
            "match_category",
            "sample_peak_area_sum",
            "sample_peak_interference_sum",
            "alarm_mode",
        ]
    ] = samples_df[
        [
            "tic",
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


@api_controller()
async def get_samples(
    sample_item_id: str = None,
    sample_item_id_active: str = None,
    sample_file_id: str = None,
    sample_batch_id: str = None,
    filename: str = None,
    instrument: str = None,
    sample_item_type: str = None,
    datetime_min: datetime = None,
    datetime_max: datetime = None,
    sort: str = "datetime_utc",
    order: str = "asc",
    page: int = 0,
    limit: int = 10000,
    batch_matches_info: bool = False,
    match_samples: bool = False,
    match_compounds: bool = False,
    match_ions: bool = False,
    match_isotopes: bool = False,
    alarms_list: AlarmsList = AlarmsList(),
) -> dict:
    """
    Retrieves samples (compinded sample item and sample file info) based on various filter criteria and pagination settings.
    Additionally, it can compute match information for the samples and return it as requested.

    Steps:
    1. Construct the base query with filters based on provided parameters.
    2. Apply sorting and pagination to the query.
    3. Execute the query and fetch results.
    4. Format the fetched samples into a dataframe for easier manipulation.
    5. If batch match info is requested, compute and merge match data with sample data.
    6. Optionally add detailed match information based on match_samples, match_compounds, match_ions, and match_isotopes flags.

    :param sample_item_id: Filter by sample item ID.
    :type sample_item_id: str, optional
    :param sample_item_id_active: Used to mark the active sample item in the response.
    :type sample_item_id_active: str, optional
    :param sample_file_id: Filter by sample file ID.
    :type sample_file_id: str, optional
    :param sample_batch_id: Filter by sample batch ID; required for batch match info.
    :type sample_batch_id: str, optional, required for batch match data
    :param filename: Filter by filename.
    :type filename: str, optional
    :param instrument: Filter by instrument name.
    :type instrument: str, optional
    :param sample_item_type: Filter by sample item type.
    :type sample_item_type: str, optional
    :param datetime_min: Filter samples after this datetime of the sample file.
    :type datetime_min: datetime, optional
    :param datetime_max: Filter samples before this datetime of the sample file.
    :type datetime_max: datetime, optional
    :param sort: Column to sort the results by.
    :type sort: str, optional
    :param order: Sort order ('asc' or 'desc').
    :type order: str, optional
    :param page: Pagination page number.
    :type page: int, optional
    :param limit: Number of results per page.
    :type limit: int, optional
    :param batch_matches_info: Flag indicating if batch match info should be computed.
    :type batch_matches_info: bool, optional
    :param match_samples, match_compounds, match_ions, match_isotopes: Flags for including detailed match info.
    :type match_samples: bool, optional
    :type match_ions: bool, optional
    :type match_isotopes: bool, optional
    :param alarms_list: List of collection types to set alarm mode to true.
    :type alarms_list: List[str], optional
    :return: A dictionary containing the total number of results, the formatted sample data, and optionally match information.
    :rtype: dict
    """
    async with async_session() as session:
        # Step 1: Construct base query with filters
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

        if datetime_min and datetime_max:
            stmt = stmt.where(
                and_(
                    cast(func.julianday(Sample.datetime_utc), Float)
                    >= func.julianday(datetime_min),
                    cast(func.julianday(Sample.datetime_utc), Float)
                    <= func.julianday(datetime_max),
                )
            )

        # Step 2: Apply sorting and pagination
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

        # Step 3: Execute query and fetch results
        result = await session.execute(stmt)
        samples = result.scalars().all()

        # Step 4: Format samples into dataframe
        samples_df = pd.DataFrame([sample.to_dict() for sample in samples])

        #  Add 'selection' field
        if sample_item_id_active is not None:
            samples_df["selection"] = samples_df["sample_item_id"].apply(
                lambda x: 3 if x == sample_item_id_active else 0
            )
        else:
            samples_df["selection"] = 0

        # Step 5: Compute and merge batch match info if requested
        if sample_batch_id and batch_matches_info:
            # Calculate and add fields match_score, sample_peak_area_sum, sample_peak_interference_sum, matched
            batch_match_filter_dict = await init_batch_match_filter(sample_batch_id)

            # Convert the result to a dataframe
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
                batch_matches_info_dict["match_compounds"] = (
                    match_compounds_df.sort_values(
                        by=["match_category", "match_score"], ascending=[False, False]
                    ).to_dict("records")
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
                batch_matches_info_dict["match_isotopes"] = (
                    match_isotopes_df.sort_values(
                        by=["match_category", "match_score"], ascending=[False, False]
                    ).to_dict("records")
                )

            result_dict["batch_matches_info"] = batch_matches_info_dict

        return result_dict


@api_controller()
async def get_sample(
    sample_item_id: str,
    alarms_list: AlarmsList = AlarmsList(),
    sample_matches_info: bool = False,
) -> dict:
    """
    Retrieves detailed information for a specific sample, optionally  including aggregated  match data.

    This function fetches the sample based on its unique identifier and conditionally computes matching data for  isotopes, ions,
    compounds, and collections, dependent on the association of the sample with target entities.

    Match calculations can be omitted based on the `sample_matches_info` parameter.
    Default is True for http requests, False when called from other controllers.

    Steps:
    1. Fetch the sample using the provided sample item ID to ensure it exists.
    2. If no match information is required, return the basic sample data immediately.
    3. Initialize match filtering for the sample and convert results to a DataFrame for further processing.
    4. Process the DataFrame to include additional match data as specified, applying alarm mode settings and aggregating data across different match categories.
    5. Compile the comprehensive sample data including all requested match information and return it in a structured dictionary format.

    :param sample_item_id: Unique identifier for the sample.
    :type sample_item_id: str
    :param alarms_list: :param alarms_list: List of collection types that set alarm_mode to true. By default, targets are alarming, diagnostics and calibrants are not, defaults to None
    :type alarms_list: List[str], optional
    :param sample_matches_info: Flag to determine if match information should be included, defaults to False.
    :type sample_matches_info: bool, optional
    :raises NotFoundException: If the sample with the specified item ID is not found.
    :return: A dictionary containing the sample information. If `sample_matches_info` is True, additional match data is included.
    :rtype: dict
    """
    async with async_session() as session:
        # Step 1: Fetch sample to verify its existence
        sample = await session.get(Sample, sample_item_id)
        if not sample:
            raise NotFoundException(f"Sample with ID '{sample_item_id}' not found")

        sample_dict = sample.to_dict()

        # Step 2: Return only basic sample data if match information is not requested.
        if not sample_matches_info:
            return sample_dict

        # Step 3: Initialize sample match filter and fetch match data.
        sample_match_filter_dict = await init_sample_match_filter(sample.sample_item_id)

        # Convert the result to a dataframe
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
            return sample_dict

        # Step 4: Process the DataFrame to include additional match data as specified,
        # applying alarm mode settings and aggregating data across different match categories.

        # Set the alarm_mode based on alarms_list
        sample_match_filter_df = await set_alarm_mode(
            sample_match_filter_df, alarms_list
        )

        # Aggregate fields for matchIsotopes
        match_isotopes_data_df, match_isotopes_df = await aggregate_match_isotopes(
            sample_match_filter_df
        )

        # Aggregate fields for matchIons
        match_ions_data_df, match_ions_df = await aggregate_match_ions(
            match_isotopes_data_df
        )

        # Aggregate fields for matchCompounds
        match_compounds_data_df, match_compounds_df = await aggregate_match_compounds(
            match_ions_data_df
        )

        # Aggregate fields for matchCollections
        match_collections_df = await aggregate_match_collections(
            match_compounds_data_df
        )

        # Step 5: Compile the final sample data dictionary.
        # Aggregate fields for sample_df
        # Convert sample into dataframe
        sample_df = pd.DataFrame([sample_dict])

        # Calculate and add fields match_score, sample_peak_area_sum, sample_peak_interference_sum, matched, selection
        match_samples_df = await aggregate_match_samples(match_compounds_data_df)

        #  Merge fields for samples data
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

        return sample_dict


@api_controller()
async def get_sample_ion_matches(
    sample_item_id: str,
    target_ion_id: str,
    target_collection_id: str,
    filter_params: FilterParams,
    alarms_list: AlarmsList = AlarmsList(),
) -> dict:
    """
    Retrieves ion-specific match information for a given sample item. This involves fetching match data at the isotopic level,
    filtering based on the provided parameters, and returning aggregated match data for ions and isotopes.

    Required ion-specific filter_params, the stored ion-specific or DEFAULT filters are NOT used for match_score/sample_peak_area filtering and setting match_category.

    Steps:
    1. Verify the existence of the specified sample item and target ion.
    2. Initialize the sample match filter with target ion and ion-specific filter parameters.
    3. Convert the filter results into a DataFrame for processing.
    4. If the DataFrame is empty, return a response indicating no matches were found.
    5. Set the alarm_mode based on the provided alarms_list.
    6. Aggregate fields for matchIsotopes and filter duplicates based on target_collection_id.
    7. Aggregate fields for matchIons and filter duplicates based on target_collection_id.
    8. Prepare the final output including the counts and details of matched ions and isotopes.

    :param sample_item_id: ID of the sample item for which to retrieve ion matches.
    :type sample_item_id: str
    :param target_ion_id: ID of the target ion for which matches are filtered.
    :type target_ion_id: str
    :param target_collection_id: ID of the target collection to filter out duplicates.
    :type target_collection_id: str
    :param filter_params: Ion-specific filter parameters for match score and sample peak area filtering.
    :type filter_params: FilterParams
    :param alarms_list: List of collection types that set alarm_mode to true. By default, targets are alarming, diagnostics and calibrants are not.
    :type alarms_list: List[str], optional
    :return: Dictionary containing aggregated match information for ions and isotopes.
    :rtype: dict
    """
    async with async_session() as session:
        # Step 1: Fetch sample and target ion to verify its existence
        sample = await session.get(Sample, sample_item_id)
        if not sample:
            raise NotFoundException(f"Sample with ID '{sample_item_id}' not found")
        ion = await session.get(TargetIon, target_ion_id)
        if not ion:
            raise NotFoundException(f"Target ion with ID '{target_ion_id}' not found")

        # Step 2: Initialize the sample match filter with target ion and ion-specific filter parameters
        sample_match_filter_dict = await init_sample_match_filter(
            sample.sample_item_id, filter_params, target_ion_id
        )

        # Step 3: Convert the result to a DataFrame
        sample_match_filter_df = pd.DataFrame(sample_match_filter_dict)

        # Step 4: Check if the DataFrame is empty
        if sample_match_filter_df.empty:
            return {
                "matches": {
                    "match_ions": 0,
                    "match_isotopes": 0,
                },
                "match_ions": [],
                "match_isotopes": [],
            }

        # Step 5: Set the alarm_mode based on alarms_list
        sample_match_filter_df = await set_alarm_mode(
            sample_match_filter_df, alarms_list
        )

        # Steps 6 & 7: Aggregate fields for matchIsotopes and matchIons, filtering duplicates
        # Aggregate fields for matchIsotopes
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

        #  Aggregate fields for matchIons
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

        # Step 8: Prepare the final output
        return {
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
        }


@api_controller()
async def get_sample_compound_matches(
    sample_item_id: str,
    target_compound_formula: str,
    target_compound_name: str = "Unknown Compound",
    filter_params: FilterParams = FilterParams(),
) -> dict:
    """
    Retrieves matches for compounds within a sample based on a target compound formula,
    applying specified filter parameters to filter the matches.

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
    :param target_compound_name: The name of the target compound, defaults to FilterParams()
    :type target_compound_name: str
    :param filter_params: Parameters to filter the match results, affecting which matches are considered significant, defaults to FilterParams()
    :type filter_params: FilterParams
    :raises NotFoundException: Raised if the sample item or sample batch cannot be found.
    :raises ValueError: Raised if no ion mechanisms are defined for the sample batch.
    :return: A dictionary containing aggregated match compounds, ions, and isotopes, each as a list of dictionaries.
    :rtype: dict
    """
    async with async_session() as session:
        # Step 1: Fetch sample related data and verify its existence
        sample = await get_sample(sample_item_id)
        filename = sample["filename"]

        # Fetch sample batch data and verify its existence
        sample_batch_id = sample["sample_batch_id"]
        sample_batch = await session.get(SampleBatch, sample_batch_id)
        if not sample_batch:
            raise NotFoundException(
                f"Sample batch with ID '{sample_batch_id}' not found"
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
        match_isotope_df = await compute_matches(
            filename=filename,
            target_isotopes_df=target_isotopes_df,
            min_isotope_abundance=filter_params.min_isotope_abundance,
        )

        # Drop the 'index' column from the match_isotope_df DataFrame
        match_isotope_df = match_isotope_df.drop(columns=["index"])

        # Step 5: Apply filters to the computed isotope matches based on the provided parameters.
        filtered_match_isotope_df = apply_filter_params(match_isotope_df, filter_params)

        # Step 6: Aggregate ion-level data from the filtered isotopes.
        match_ions_data_df = aggregate_match_ions_simple(filtered_match_isotope_df)
        match_ions_df = pd.merge(
            match_ions_data_df, created_ions_df, on="target_ion_id", how="left"
        )

        # Step 7: Aggregate compound-level data from the ions and merge with target compound information.
        match_compounds_data_df = aggregate_match_compounds_simple(match_ions_df)

        # Convert the dictionary into a DataFrame
        target_compound_df = pd.DataFrame([target_compound.to_dict()])

        # Merge match_compounds_data_df with target_compound_df
        merged_match_compounds_df = pd.merge(
            match_compounds_data_df,
            target_compound_df,
            on="target_compound_id",
            how="left",
        )

        return {
            "match_compounds": merged_match_compounds_df.to_dict("records"),
            "match_ions": match_ions_df.to_dict("records"),
            "match_isotopes": filtered_match_isotope_df.to_dict("records"),
        }


@api_controller()
async def init_batch_match_filter(
    sample_batch_id: str, include_match_interference: bool = True
) -> list:
    """
    Initializes and applies a batch-level match filter across all samples within a specified batch.
    This function aggregates isotopic level match data for all samples in the batch, applying ion-specific
    or default filtering parameters to each isotopic match. The result includes filtered match data.

    This function is used for aggregating batch-level match data. It is utilized in the get_samples endpoint to
    include aggregated match data (`batch_matches_info`) within the response.

    Steps:
    1. Verify the existence of the specified sample batch.
    2. Construct and execute structured queries to fetch relevant match data across the batch:
       a. Fetch basic sample information.
       b. Fetch associated target information including collections, compounds, ions, and isotopes.
       c. Combine these to fetch relevant match data.
    3. Optionally include match interference data if requested.
    4. Apply filtering criteria based on ion-specific parameters or default values to each isotopic match.
    5. Convert the filtered DataFrame to a list of dictionaries for the final output.

    :param sample_batch_id: ID of the sample batch for which to initialize and apply the match filter.
    :type sample_batch_id: str
    :param include_match_interference: Flag indicating whether to include match interference data.
    :rtype: bool
    :return: A list of dictionaries containing the filtered isotopic match data for the entire batch.
    :rtype: List[Dict]
    :raises NotFoundException: If the specified sample batch does not exist.
    """
    async with async_session() as session:
        # Verify existence of the sample batch
        sample_batch = await session.get(SampleBatch, sample_batch_id)
        if not sample_batch:
            raise NotFoundException(
                f"Sample batch with ID '{sample_batch_id}' not found"
            )

        # Step 2: Extract ion mechanisms from sample batch's build parameters
        build_params = sample_batch.build_params
        sample_batch_ion_mechanisms = build_params.get("ion_mechanisms", [])

        # Query for fetching basic samples information
        sample_query = select(
            Sample.sample_item_id,
            Sample.filename,
            Sample.instrument,
            Sample.sample_item_name,
            Sample.sample_item_type,
        ).where(Sample.sample_batch_id == sample_batch_id)

        sample_result = await session.execute(sample_query)
        samples_df = pd.DataFrame([row._asdict() for row in sample_result.fetchall()])

        if samples_df.empty:
            print(f"No samples found in the batch '{sample_batch.sample_batch_name}'")
            return {}

        sample_item_ids = samples_df["sample_item_id"].tolist()

        # Subquery to get relevant Target data
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
                IonizationMechanism.ionization_mechanism.label("target_ion_mechanism"),
                TargetIsotope.target_isotope_id,
                TargetIsotope.mz,
                TargetIsotope.relative_abundance,
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
                    sample_batch_ion_mechanisms
                ),
            )
            .join(
                TargetIsotope,
                TargetIsotope.target_ion_id == TargetIon.target_ion_id,
            )
        )

        target_result = await session.execute(target_query)
        targets_df = pd.DataFrame([row._asdict() for row in target_result.fetchall()])
        if targets_df.empty:
            print(f"No targets found in the batch '{sample_batch.sample_batch_name}'")
            return {}

        target_isotope_ids = targets_df["target_isotope_id"].tolist()

        # Fetch matches
        match_query = (
            select(
                Match.sample_item_id,
                Match.target_isotope_id,
                Match.match_mz_error,
                Match.match_abundance_error,
                Match.match_isotope_correlation,
                Match.sample_peak_area,
                Match.sample_peak_area_relative,
                Match.sample_peak_mz,
                Match.sample_peak_tof,
                Match.match_score,
            )
            .select_from(Match)
            .where(
                and_(
                    Match.sample_item_id.in_(sample_item_ids),
                    Match.target_isotope_id.in_(target_isotope_ids),
                )
            )
        )

        match_result = await session.execute(match_query)
        matches_df = pd.DataFrame(match_result.fetchall())

        # Fetch match interference if the flag is true
        if include_match_interference:
            match_interference_query = (
                select(
                    MatchInterference.sample_peak_interference,
                    MatchInterference.sample_item_id,
                    MatchInterference.target_isotope_id,
                )
                .select_from(MatchInterference)
                .where(
                    and_(
                        MatchInterference.sample_item_id.in_(sample_item_ids),
                        MatchInterference.target_isotope_id.in_(target_isotope_ids),
                    )
                )
            )

            match_interference_result = await session.execute(match_interference_query)
            match_interference_df = pd.DataFrame(match_interference_result.fetchall())

            if match_interference_df.empty:
                print(
                    f"No match interference found for the sample batch '{sample_batch.sample_batch_name}'"
                )
                return {}

            # Merge interference data into the matches DataFrame
            matches_df = pd.merge(
                matches_df,
                match_interference_df,
                on=["sample_item_id", "target_isotope_id"],
                how="left",
            )

        # Merge DataFrames
        if matches_df.empty:
            print(
                f"No matches found for the sample batch '{sample_batch.sample_batch_name}'"
            )
            return {}
        combined_sample_matches_df = pd.merge(
            matches_df, samples_df, on="sample_item_id", how="inner"
        )
        batch_match_data_df = pd.merge(
            combined_sample_matches_df, targets_df, on="target_isotope_id", how="inner"
        )

        # Define the desired column order
        column_order = [
            "sample_item_id",
            "filename",
            "instrument",
            "sample_item_name",
            "sample_item_type",
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
            "target_ion_mechanism",
            "target_isotope_id",
            "mz",
            "relative_abundance",
            "match_mz_error",
            "match_abundance_error",
            "match_isotope_correlation",
            "sample_peak_area",
            "sample_peak_area_relative",
            "sample_peak_mz",
            "sample_peak_tof",
            "match_score",
        ]
        if include_match_interference:
            column_order.append("sample_peak_interference")

        # Reorder the columns according to the defined order and sort the DataFrame by 'mz'
        batch_match_data_df = (
            batch_match_data_df[column_order]
            .sort_values(by="mz", kind="mergesort")
            .reset_index(drop=True)
        )

        # Step 4: Apply filtering match_score, sample_peak_area
        batch_match_data_filtered_df = apply_filter_params(batch_match_data_df)

        return batch_match_data_filtered_df.to_dict("records")


@api_controller()
async def init_sample_match_filter(
    sample_item_id: str,
    filter_params: FilterParams = None,
    target_ion_id: str = None,
) -> list:
    """
    Initializes and applies the sample match filter for a specific sample item, representing isotope-level data.
    This function fetches isotope match data for a given sample item, applies filtering based on provided
    ion-specific parameters or default values, and returns the filtered match data.

    This function may be utilized to filter matches by target ion, for example in the get_sample_ion_matches endpoint.

    Filter params are ion-specific. If filter_params are not provided the stored ion-specific or DEFAULT filters are used
    for match_score/sample_peak_area filtering and setting match_category

    Steps:
    1. Verify the existence of the specified sample item.
    2. If a target ion ID is provided, verify its existence and use the provided filter parameters.
    3. Construct and execute a database query to fetch relevant isotopic match data.
    4. Convert query result to DataFrame.
    5. Apply filtering based on provided filter parameters or using the stored ion-specific or DEFAULT filter parameters.
    6. Convert the filtered DataFrame to a list of dictionaries.

    :param sample_item_id: ID of the sample item for which to initialize the match filter.
    :type sample_item_id: str
    :param filter_params: Optional ion-specific filter parameters for match score and sample peak area filtering.
    :type filter_params: FilterParams, optional
    :param target_ion_id: Optional target ion ID to filter the matches at an isotopic level.
    :type target_ion_id: str, optional
    :return: A list of dictionaries containing the filtered isotopic match data.
    :rtype: List[Dict]
    :raises NotFoundException: If the specified sample item or target ion does not exist.
    """
    # Set min_isotope_abundance filter parameter to the provided one or to the DEFAULT value for query
    min_isotope_abundance = (
        filter_params.min_isotope_abundance
        if filter_params
        else DEFAULT_MIN_ISOTOPE_ABUNDANCE
    )

    async with async_session() as session:
        # Step 1: Fetch sample item to verify its existence
        sample = await session.get(Sample, sample_item_id)
        if not sample:
            raise NotFoundException(f"Sample with ID '{sample_item_id}' not found")

        # Step 2: Fetch target ion to verify its existence (if target_ion_id is provided)
        if target_ion_id is not None:
            ion = await session.get(TargetIon, target_ion_id)
            if not ion:
                raise NotFoundException(
                    f"Target ion with ID '{target_ion_id}' not found"
                )

        # Step 3: Construct and execute query to fetch match data
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

        if target_ion_id is not None:
            # Apply target_ion_id filter if provided
            stmt = stmt.where(TargetIon.target_ion_id == target_ion_id)

        result = await session.execute(stmt)
        sample_match_filter = result.fetchall()

        # Step 4: Convert query result to DataFrame
        sample_match_filter_df = pd.DataFrame(
            [row._asdict() for row in sample_match_filter]
        )

        # Step 5: Apply filtering criteria, filtering match_score, sample_peak_area, and setting match_category
        filtered_sample_match_filter_df = apply_filter_params(
            sample_match_filter_df, filter_params
        )

        # Step 6: Convert the filtered DataFrame to a list of dictionaries
        filtered_sample_match_filter_dicts = filtered_sample_match_filter_df.to_dict(
            "records"
        )

        return filtered_sample_match_filter_dicts
