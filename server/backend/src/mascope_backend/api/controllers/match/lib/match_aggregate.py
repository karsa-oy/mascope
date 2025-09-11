from typing import Optional, Tuple
import pandas as pd
from mascope_match.params import (
    BaseMatchParams,
    DEFAULT_PROBABLE_MATCH_THRESHOLD,
    DEFAULT_POSSIBLE_MATCH_THRESHOLD,
)
from mascope_backend.api.controllers.match.lib.match_util import similarity_factor

    target_collection_config,
)

# TODO_configuration list of alarming collection types
APP_ALARMING_COLLECTION_TYPES = ["TARGETS"]


def aggregate_params(df: pd.DataFrame) -> pd.Series:
    """Aggregation function to get the aggregated parameters.

    Set match_score, match_category of the top row (the most alarming row).
    Sums sample_peak_intensity_sum for the group.

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
            "sample_peak_intensity_sum": df["sample_peak_intensity_sum"].sum(),
        }
    )


async def set_ions_match_category(
    match_ions_df: pd.DataFrame, match_params: Optional[BaseMatchParams] = None
) -> pd.DataFrame:
    """Set the match_category field for each ion in the DataFrame.

    This function determines the match_category for each ion based on match score and predefined thresholds.
    It uses provided filters, or defaults if none are provided, and falls back to ion-specific filters when available.

    :param match_ions_df: DataFrame containing ion data with match scores.
    :type match_ions_df: pd.DataFrame
    :param match_params: Optional ion-specific filter parameters.
    :type match_params: Optional[BaseMatchParams]
    :return: DataFrame with match_category field set for each ion.
    :rtype: pd.DataFrame
    """
    for index, row in match_ions_df.iterrows():
        # Default thresholds
        probable_match_threshold = DEFAULT_PROBABLE_MATCH_THRESHOLD
        possible_match_threshold = DEFAULT_POSSIBLE_MATCH_THRESHOLD

        # Override with provided filter parameters if available
        if match_params:
            probable_match_threshold = match_params.probable_match_threshold
            possible_match_threshold = match_params.possible_match_threshold

        # Use ion-specific filters if available and no match_params provided
        instrument = row["instrument"]
        match_params_ion = row.get("filter_params")
        if not match_params and match_params_ion and instrument in match_params_ion:
            ion_filters = match_params_ion[row["instrument"]]
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


async def set_alarm_mode(dataframe: pd.DataFrame) -> pd.DataFrame:
    """
    Set the alarm_mode field for each entry in the DataFrame based on the list of provided alarms_list.

    :param dataframe: DataFrame containing sample/batch match filter data.
    :type dataframe: pd.DataFrame
    :return: DataFrame with alarm_mode field set.
    :rtype: pd.DataFrame
    """
    # TODO_configuration list of alarming collection types
    alarms_list = APP_ALARMING_COLLECTION_TYPES
    # Set alarm_mode based on whether the target_collection_type is in the alarms_list
    dataframe["alarm_mode"] = dataframe["target_collection_type"].apply(
        lambda x: True if x in alarms_list else False
    )
    return dataframe


async def aggregate_match_isotopes(
    filtered_match_isotope_df: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Filter the fields of aggregated filtered match isotopes dataframe.
    (used for backwards compatibility of get_sample_aggregate_matches, may be removed further)

    This function processes the sample/batch match filter dataframe to aggregate isotope data.
    It prepares two DataFrames:
    1) match_isotopes_data_df with detailed data for further aggregation,
    2) match_isotopes_df with reduced data for frontend display.

    :param filtered_match_isotope_df: DataFrame containing sample/batch match filter data to aggregate.
    :type filtered_match_isotope_df: pd.DataFrame
    :return: Tuple of DataFrames with aggregated matchIsotopes data.
    :rtype: (pd.DataFrame, pd.DataFrame)
    (compute_match_isotopes, apply_match_params and combine data, aggregate_match_isotopes)
    """
    # Select relevant columns for detailed aggregation (backend processing)
    match_isotopes_data_df = filtered_match_isotope_df.loc[
        :,
        [
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
            "target_compound_name",
            "target_compound_formula",
            "target_ion_id",
            "target_ion_formula",
            "filter_params",
            "ionization_mechanism",
            "target_isotope_id",
            "mz",
            "relative_abundance",
            "match_mz_error",
            "match_abundance_error",
            "match_isotope_similarity",
            "sample_peak_intensity",
            "sample_peak_intensity_relative",
            "sample_peak_mz",
            "sample_peak_tof",
            "match_category",
            "match_score",
        ],
    ]

    # Prepare a simplified DataFrame for frontend
    match_isotopes_df = match_isotopes_data_df.drop(
        columns=[
            "sample_item_type",
            "target_ion_formula",
            "ionization_mechanism",
            "filter_params",
            "target_compound_name",
            "target_compound_formula",
            "target_collection_id",
            "target_collection_name",
            "target_collection_description",
            "target_collection_type",
        ]
    ).drop_duplicates(subset=["target_isotope_id", "sample_item_id"])

    return match_isotopes_data_df, match_isotopes_df


async def aggregate_match_ions(
    filtered_match_isotope_df: pd.DataFrame,
    match_params: Optional[BaseMatchParams] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Aggregate fields for match ions from aggregated filtered match isotopes dataframe.
    Provided filters are passed to set_ions_match_category, if none match_params are provided, stored ion-specidic or default params will be applied.

    It prepares two DataFrames:
    1) match_ions_data_df with detailed data for correct further aggregation on collection/sample lvl,
    2) match_ions_df with reduced data and dropped duplicates (same compound in different collections).

    The match_score is calculated as a weighted sum of individual isotopes' match scores, weighted by their relative abundance.
    The sample_peak_intensity is summed across all isotopes in the group, the _sum is added to the field name.

    :param filtered_match_isotope_df: DataFrame containing isotope data to aggregate.
    :type filtered_match_isotope_df: pd.DataFrame
    :param match_params: Optional ion-specific filter parameters to set_ions_match_category.
    :type match_params: Optional[BaseMatchParams]
    :return: Tuple of DataFrames with aggregated match ions data.
    :rtype: (pd.DataFrame, pd.DataFrame)
    """
    match_ions_data_df = (
        filtered_match_isotope_df.groupby(
            [
                "sample_item_id",
                "sample_item_name",
                "sample_item_type",
                "filename",
                "instrument",
                "target_ion_id",
                "target_ion_formula",
                "ionization_mechanism",
                "target_compound_id",
                "target_compound_formula",
                "target_compound_name",
                "target_collection_id",
                "target_collection_name",
                "target_collection_description",
                "target_collection_type",
            ]
        )
        .agg(
            {
                "match_score": lambda x: (
                    x
                    * similarity_factor(
                        filtered_match_isotope_df.loc[
                            x.index, "match_isotope_similarity"
                        ]
                    )
                    * filtered_match_isotope_df.loc[x.index, "relative_abundance"]
                    / filtered_match_isotope_df.loc[x.index, "relative_abundance"].sum()
                ).sum(),
                "sample_peak_intensity": "sum",
                "filter_params": "first",
            }
        )
        .reset_index()
        .rename(
            columns={
                "sample_peak_intensity": "sample_peak_intensity_sum",
            }
        )
    )
    # Prepare a simplified DataFrame for storing in database (keep instrument and match_params for correct set_ions_match_category)
    # Drop duplicates for match ions based on target_ion_id for each sample, so each sample would have the unique match ions
    # (even of there is same compound=>ion present in different target collections of the sample)
    match_ions_df = match_ions_data_df.drop(
        columns=[
            "target_compound_id",
            "target_collection_id",
            "target_collection_name",
            "target_collection_description",
            "target_collection_type",
        ]
    ).drop_duplicates(subset=["target_ion_id", "sample_item_id"])

    # set match_category field for ions
    match_ions_data_df = await set_ions_match_category(match_ions_data_df, match_params)
    match_ions_df = await set_ions_match_category(match_ions_df, match_params)

    return match_ions_data_df, match_ions_df


def aggregate_match_ions_light(
    filtered_match_isotope_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Aggregate fields for match ions from the lighter then in main pipeline (aggregate_match_ions) computed and filtered match isotope DataFrame.
    Used in the aggregate_sample_match_compound to aggregate simple match_ions_data_df after compute_match_isotopes and apply_match_params.

    This function groups the filtered match isotope DataFrame by 'target_ion_id' and aggregates relevant data,
    such as summing up 'sample_peak_intensity' and computing a weighted 'match_score'.

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
                    x
                    * filtered_match_isotope_df.loc[x.index, "relative_abundance"]
                    / filtered_match_isotope_df.loc[x.index, "relative_abundance"].sum()
                ).sum(),
            ),
            sample_peak_intensity_sum=("sample_peak_intensity", "sum"),
        )
        .reset_index()
    )

    return match_ions_df


async def aggregate_match_compounds(
    match_ions_df: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Aggregate fields for match compounds from aggregated match ions dataframe.

    This function sorts the ions dataframe by match_category and match_score in descending order
    and then groups by target_compound_id and other relevant fields to compute the aggregated
    values for match_score, match_category, sample_peak_intensity_sum.
    It preserves the highest match_score of ion from the most alarming match_category (the most alarming ion)
    and sums up the sample_peak_intensity_sum for the entire group.

    It prepares two DataFrames:
    1) match_compounds_data_df with detailed data for correct further aggregation on collection/sample lvl,
    2) match_compounds_df with reduced data and dropped duplicates (same compound in different collections).


    :param match_ions_df: DataFrame containing ion data to aggregate.
    :type match_ions_df: pd.DataFrame
    :return: pandas DataFrame with aggregated match compounds data.
    :rtype: pd.DataFrame
    """
    match_compounds_data_df = (
        match_ions_df.sort_values(
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
        )[match_ions_df.columns]
        .apply(aggregate_params)
        .reset_index()
    )
    # Explicitly cast match_category to int
    match_compounds_data_df["match_category"] = match_compounds_data_df[
        "match_category"
    ].astype(int)

    # Prepare a simplified DataFrame for storing in database
    # Drop duplicates for match compounds based on target_ion_id for each sample, so each sample would have the unique match compounds
    # (even of there is same compound present in different target collections of the sample)
    match_compounds_df = match_compounds_data_df.drop(
        columns=[
            "target_collection_id",
            "target_collection_name",
            "target_collection_description",
            "target_collection_type",
        ]
    ).drop_duplicates(subset=["target_compound_id", "sample_item_id"])

    return match_compounds_data_df, match_compounds_df


def aggregate_match_compounds_light(match_ions_df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate fields for match compounds from the lighter then in main pipeline (aggregate_match_compounds) match ions DataFrame.
    Used in the aggregate_sample_match_compound to aggregate simpler match_compounds_data_df from result of aggregate_match_ions_light.

    This function groups the match ions DataFrame by 'target_compound_id' and aggregates relevant data,
    such as computing a weighted 'match_score' and summing up 'sample_peak_intensity'.

    :param match_ions_df: DataFrame containing match ions data.
    :type match_ions_df: pd.DataFrame
    :return: DataFrame with aggregated match compounds data.
    :rtype: pd.DataFrame
    """
    match_compounds_df = (
        match_ions_df.groupby("target_compound_id")
        .agg(
            match_score=("match_score", "max"),
            sample_peak_intensity_sum=("sample_peak_intensity_sum", "sum"),
        )
        .reset_index()
    )

    return match_compounds_df


async def aggregate_match_collections(compounds_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate fields for match collections from aggregated match compounds dataframe.

    This function sorts the compounds dataframe by match_category and match_score in descending order
    and then groups by target_collection_id and other relevant fields to compute the aggregated
    values for match_score, match_category, sample_peak_intensity_sum.
    It preserves the highest match_score of compound from the most alarming match_category (the most alarming compound in collection)
    and sums up the sample_peak_intensity_sum for the entire group.

    :param compounds_df: DataFrame containing aggregated match compound data.
    :type compounds_df: pd.DataFrame
    :return: DataFrame with aggregated match collections data.
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
        )[compounds_df.columns]
        .apply(aggregate_params)
        .reset_index()
    )
    # Explicitly cast match_category to int
    match_collections_df["match_category"] = match_collections_df[
        "match_category"
    ].astype(int)

    return match_collections_df


async def aggregate_match_samples(compounds_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate fields for match samples from compounds dataframe.

    This function sorts the compounds dataframe by alarm_mode, match_category and match_score in descending order
    and then groups by sample_item_id and other relevant fields to compute the aggregated
    values for match_score, match_category, sample_peak_intensity_sum.
    It preserves the highest match_score of compound where alarm_mode and match_category is the highest (the most alarming compound of sample)
    and sums up the sample_peak_intensity_sum for the entire group.

    :param compounds_df: DataFrame containing aggregated match compound data.
    :type compounds_df: pd.DataFrame
    :return: pandas DataFrame with aggregated match samples data.
    :rtype: pd.DataFrame
    """
    # Set the alarm_mode based on alarms_list and target_collection_type
    compounds_df = await set_alarm_mode(compounds_df)
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
        )[compounds_df.columns]
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
    It adds the match_score, match_category, sample_peak_intensity_sum fields to each sample.
    The 'matched' field is calculated to indicate whether the sample has any match results.

    The aggregation logic in match_samples_df ensures that each sample's aggregated fields represent:
      - The highest match_score of compound from the most alarming match_category (the most alarming compound of sample)
      - The sum of sample_peak_intensity for all compounds of the sample

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
            "sample_peak_intensity_sum",
        ]
    ]

    # Merge with samples_df
    samples_df = pd.merge(
        samples_df, match_samples_df_short, how="left", on="sample_item_id"
    )

    # Add matched column
    samples_df["matched"] = samples_df["match_score"].apply(
        lambda x: int(not pd.isna(x))
    )

    # Replace NaNs with 0
    samples_df[
        [
            "tic",
            "match_score",
            "match_category",
            "sample_peak_intensity_sum",
        ]
    ] = samples_df[
        [
            "tic",
            "match_score",
            "match_category",
            "sample_peak_intensity_sum",
        ]
    ].fillna(
        0
    )

    return samples_df
