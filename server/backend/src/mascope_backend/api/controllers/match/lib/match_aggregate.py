from typing import Optional, Tuple

import pandas as pd

from mascope_backend.api.models.target.collections.config import (
    target_collection_config,
)
from mascope_match.params import (
    DEFAULT_POSSIBLE_MATCH_THRESHOLD,
    DEFAULT_PROBABLE_MATCH_THRESHOLD,
    BaseMatchParams,
)


async def set_ions_match_category(
    match_ions_df: pd.DataFrame, match_params: Optional[BaseMatchParams] = None
) -> pd.DataFrame:
    """Set the match_category field for each ion in the DataFrame.

    This function determines the match_category for each ion based on match score and
    predefined thresholds. It uses provided filters, or defaults if none are provided,
    and falls back to ion-specific filters when available.

    :param match_ions_df: DataFrame containing ion data with match scores.
    :type match_ions_df: pd.DataFrame
    :param match_params: Optional ion-specific filter parameters.
    :type match_params: Optional[BaseMatchParams]
    :return: DataFrame with match_category field set for each ion.
    :rtype: pd.DataFrame
    """
    if match_ions_df.empty:
        match_ions_df["match_category"] = pd.Series(dtype=int)
        return match_ions_df

    # --- Resolve per-ion thresholds (vectorized) ---
    if match_params:
        # Provided parameters take priority for every ion.
        probable = pd.Series(
            match_params.probable_match_threshold, index=match_ions_df.index
        )
        possible = pd.Series(
            match_params.possible_match_threshold, index=match_ions_df.index
        )
    else:
        # Ion-specific overrides (filter_params keyed by instrument), falling
        # back to the module defaults.
        probable = pd.Series(
            DEFAULT_PROBABLE_MATCH_THRESHOLD, index=match_ions_df.index, dtype=float
        )
        possible = pd.Series(
            DEFAULT_POSSIBLE_MATCH_THRESHOLD, index=match_ions_df.index, dtype=float
        )
        if "filter_params" in match_ions_df.columns:
            for i, (instrument, filter_params) in enumerate(
                zip(match_ions_df["instrument"], match_ions_df["filter_params"])
            ):
                if isinstance(filter_params, dict) and instrument in filter_params:
                    ion_filters = filter_params[instrument]
                    idx = match_ions_df.index[i]
                    probable.at[idx] = ion_filters["probable_match_threshold"]
                    possible.at[idx] = ion_filters["possible_match_threshold"]

    # Determine match_category from match_score against the resolved thresholds.
    match_score = match_ions_df["match_score"]
    category = pd.Series(0, index=match_ions_df.index, dtype=int)
    category[match_score >= possible] = 1
    category[match_score >= probable] = 2
    match_ions_df["match_category"] = category

    return match_ions_df


async def set_alarm_mode(dataframe: pd.DataFrame) -> pd.DataFrame:
    """
    Set the alarm_mode field for each entry in the DataFrame based on the list of
    provided alarms_list.

    :param dataframe: DataFrame containing sample/batch match filter data.
    :type dataframe: pd.DataFrame
    :return: DataFrame with alarm_mode field set.
    :rtype: pd.DataFrame
    """
    alarms_list = target_collection_config.APP_ALARMING_COLLECTION_TYPES
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
    (used for backwards compatibility of get_sample_aggregate_matches, may be removed
    further)

    This function processes the sample/batch match filter dataframe to aggregate isotope
    data. It prepares two DataFrames:
    1) match_isotopes_data_df with detailed data for further aggregation,
    2) match_isotopes_df with reduced data for frontend display.

    :param filtered_match_isotope_df: DataFrame containing sample/batch match filter
      data to aggregate.
    :type filtered_match_isotope_df: pd.DataFrame
    :return: Tuple of DataFrames with aggregated matchIsotopes data.
    :rtype: (pd.DataFrame, pd.DataFrame)
      (compute_match_isotopes, apply_match_params and combine data,
      aggregate_match_isotopes)
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
    Provided filters are passed to set_ions_match_category, if none match_params are
    provided, stored ion-specific or default params will be applied.

    It prepares two DataFrames:
    1) match_ions_data_df with detailed data for correct further aggregation on
       collection/sample level,
    2) match_ions_df with reduced data and dropped duplicates (same compound in
       different collections).

    The match_score is calculated as a weighted sum of individual isotopes' match scores
    weighted by their relative abundance.
    The sample_peak_intensity is summed across all isotopes in the group, the _sum is
    added to the field name.

    :param filtered_match_isotope_df: DataFrame containing isotope data to aggregate.
    :type filtered_match_isotope_df: pd.DataFrame
    :param match_params: Optional ion-specific filter parameters to
      set_ions_match_category.
    :type match_params: Optional[BaseMatchParams]
    :return: Tuple of DataFrames with aggregated match ions data.
    :rtype: (pd.DataFrame, pd.DataFrame)
    """
    # Precompute the abundance-weighted score once so the groupby can sum it
    # directly instead of re-indexing relative_abundance per group.
    weighted = filtered_match_isotope_df.assign(
        _weighted_score=filtered_match_isotope_df["match_score"]
        * filtered_match_isotope_df["relative_abundance"]
    )
    match_ions_data_df = (
        weighted.groupby(
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
            match_score=("_weighted_score", "sum"),
            sample_peak_intensity_sum=("sample_peak_intensity", "sum"),
            filter_params=("filter_params", "first"),
        )
        .reset_index()
    )
    # Prepare a simplified DataFrame for storing in database (keep instrument and
    # match_params for correct set_ions_match_category)
    # Drop duplicates for match ions based on target_ion_id for each sample, so each
    # sample would have the unique match ions
    # (even if there is same compound=>ion present in different target collections of
    # the sample)
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
    Aggregate fields for match ions from the lighter then in main pipeline
    (aggregate_match_ions) computed and filtered match isotope DataFrame.
    Used in the aggregate_sample_match_compound to aggregate simple match_ions_data_df
    after compute_match_isotopes and apply_match_params.

    This function groups the filtered match isotope DataFrame by 'target_ion_id' and
    aggregates relevant data, such as summing up 'sample_peak_intensity' and computing
    a weighted 'match_score'.

    :param filtered_match_isotope_df: DataFrame containing filtered match isotope data.
    :type filtered_match_isotope_df: pd.DataFrame
    :return: DataFrame with aggregated match ions data.
    :rtype: pd.DataFrame
    """
    weighted = filtered_match_isotope_df.assign(
        _weighted_score=filtered_match_isotope_df["match_score"]
        * filtered_match_isotope_df["relative_abundance"]
    )
    match_ions_df = (
        weighted.groupby("target_ion_id")
        .agg(
            match_score=("_weighted_score", "sum"),
            sample_peak_intensity_sum=("sample_peak_intensity", "sum"),
        )
        .reset_index()
    )

    return match_ions_df


async def aggregate_match_compounds(
    match_ions_df: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Aggregate fields for match compounds from aggregated match ions dataframe.

    This function sorts the ions dataframe by match_category and match_score in
    descending order and then groups by target_compound_id and other relevant fields to
    compute the aggregated values for match_score, match_category,
    sample_peak_intensity_sum. It preserves the highest match_score of ion from the most
    alarming match_category (the most alarming ion) and sums up the
    sample_peak_intensity_sum for the entire group.

    It prepares two DataFrames:
    1) match_compounds_data_df with detailed data for correct further aggregation on
       collection/sample lvl,
    2) match_compounds_df with reduced data and dropped duplicates (same compound in
       different collections).


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
            ],
            sort=False,
        )
        .agg(
            # The frame is pre-sorted by (match_category, match_score) desc, so
            # "first" preserves the most alarming row's score and category.
            match_score=("match_score", "first"),
            match_category=("match_category", "first"),
            sample_peak_intensity_sum=("sample_peak_intensity_sum", "sum"),
        )
        .reset_index()
    )
    # Explicitly cast match_category to int
    match_compounds_data_df["match_category"] = match_compounds_data_df[
        "match_category"
    ].astype(int)

    # Prepare a simplified DataFrame for storing in database
    # Drop duplicates for match compounds based on target_ion_id for each sample, so
    # each sample would have the unique match compounds
    # (even if there is same compound present in different target collections of the
    # sample)
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
    Aggregate fields for match compounds from the lighter then in main pipeline
    (aggregate_match_compounds) match ions DataFrame. Used in the
    aggregate_sample_match_compound to aggregate simpler match_compounds_data_df from
    result of aggregate_match_ions_light.

    This function groups the match ions DataFrame by 'target_compound_id' and aggregates
    relevant data, such as computing a weighted 'match_score' and summing up
    'sample_peak_intensity'.

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

    This function sorts the compounds dataframe by match_category and match_score in
    descending order and then groups by target_collection_id and other relevant fields
    to compute the aggregated values for match_score, match_category,
    sample_peak_intensity_sum. It preserves the highest match_score of compound from the
    most alarming match_category (the most alarming compound in collection) and sums up
    the sample_peak_intensity_sum for the entire group.

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
            ],
            sort=False,
        )
        .agg(
            # Pre-sorted desc, so "first" is the most alarming compound.
            match_score=("match_score", "first"),
            match_category=("match_category", "first"),
            sample_peak_intensity_sum=("sample_peak_intensity_sum", "sum"),
        )
        .reset_index()
    )
    # Explicitly cast match_category to int
    match_collections_df["match_category"] = match_collections_df[
        "match_category"
    ].astype(int)

    return match_collections_df


async def aggregate_match_samples(compounds_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate fields for match samples from compounds dataframe.

    This function sorts the compounds dataframe by alarm_mode, match_category and
    match_score in descending order and then groups by sample_item_id and other relevant
    fields to compute the aggregated values for match_score, match_category,
    sample_peak_intensity_sum. It preserves the highest match_score of compound where
    alarm_mode and match_category is the highest (the most alarming compound of sample)
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
            ],
            sort=False,
        )
        .agg(
            # Pre-sorted by (alarm_mode, match_category, match_score) desc, so
            # "first" is the most alarming compound of the sample.
            match_score=("match_score", "first"),
            match_category=("match_category", "first"),
            sample_peak_intensity_sum=("sample_peak_intensity_sum", "sum"),
        )
        .reset_index()
    )
    # Cast match_category to int
    match_samples_df["match_category"] = match_samples_df["match_category"].astype(int)

    return match_samples_df


async def compile_samples_df(
    samples_df: pd.DataFrame,
    match_samples_df: pd.DataFrame,
) -> pd.DataFrame:
    """Compile samples dataframe data (from database SampleView) with aggregated match
    results.

    This function merges the samples dataframe with the aggregated match results from
    the match_samples dataframe. It adds the match_score, match_category,
    sample_peak_intensity_sum fields to each sample. The 'matched' field is calculated
    to indicate whether the sample has any match results.

    The aggregation logic in match_samples_df ensures that each sample's aggregated
    fields represent:
      - The highest match_score of compound from the most alarming match_category
        (the most alarming compound of sample)
      - The sum of sample_peak_intensity for all compounds of the sample

    NaN values in aggregated fields are replaced with 0, indicating no matches or data
    for those fields.

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
    ].fillna(0)

    return samples_df
