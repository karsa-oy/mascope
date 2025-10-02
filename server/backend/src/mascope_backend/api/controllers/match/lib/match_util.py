import pandas as pd
import numpy as np


def sort_and_paginate_match_sample_df(
    df: pd.DataFrame,
    order: str,
    page: int | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    """
    Sorts and optionally paginates the DataFrame for match sample data. Used in endpoints match_sample_targets_controller.
    Handles NaN values by treating them as -1 for sorting purposes and ensures JSON compatibility.

    Steps:
    1. Validate pagination parameters: both 'page' and 'limit' must be provided together or both omitted.
    2. Replace NaN values in 'match_score' and 'match_category' with -1 for sorting purposes.
    3. Convert 'match_category' to integer type.
    4. Sort the DataFrame by 'target_collection_id', 'match_category', and 'match_score'.
    5. If pagination parameters are provided, paginate the sorted DataFrame based on the 'page' and 'limit' parameters.
    6. Replace -1 back to None for 'match_score' and 'match_category'.
    7. Replace all other NaN and NaT values with None for JSON compatibility.

    :param df: DataFrame containing the match sample data to be sorted and optionally paginated.
    :type df: pd.DataFrame
    :param order: Sorting order ('asc' or 'desc')
    :type order: str
    :param page: Page number for pagination, defaults to None (no pagination).
    :type page: int | None, optional
    :param limit: Number of items per page, defaults to None (no pagination).
    :type limit: int | None, optional
    :return: Sorted and optionally paginated DataFrame with JSON compatible values.
    :rtype: pd.DataFrame
    """
    # Validate pagination parameters
    if (page is None) != (limit is None):
        raise ValueError(
            "Both 'page' and 'limit' must be provided together or both omitted."
        )

    # Replace match_score and match_category NaN for sorting and ensure match_category remains integer
    # The option_context is used to avoid FutureWarning in pandas 3, where silent downcasting is deprecated.
    with pd.option_context("future.no_silent_downcasting", True):
        df["match_score"] = df["match_score"].fillna(-1)
        df["match_category"] = df["match_category"].fillna(-1).astype(int)

    # Sorting data
    sort_ascending = [(order != "desc"), (order != "desc"), (order != "desc")]
    df = df.sort_values(
        by=["target_collection_id", "match_category", "match_score"],
        ascending=sort_ascending,
    )

    # Pagination logic (conditional)
    if page is not None and limit is not None:
        df = df.iloc[page * limit : (page + 1) * limit]

    # Replace -1 back to None for match_category and match_score if it was originally NaN
    df["match_score"] = df["match_score"].replace(-1, None)
    df["match_category"] = df["match_category"].replace(-1, None)

    # Replace all other NaN and NaT with None for JSON compatibility
    df = df.replace([np.nan, pd.NaT], None)

    return df


def deduplicate_match_df(df: pd.DataFrame, id_keys: tuple) -> pd.DataFrame:
    """
    Deduplicate match items in a DataFrame based on target_collection_type priority.
    Priority: TARGETS > DIAGNOSTICS > CALIBRANTS.

    :param df: DataFrame of match items to deduplicate.
    :type df: pd.DataFrame
    :param id_keys: Keys to identify unique items (e.g., 'target_compound_id', 'sample_item_id').
    :type id_keys: tuple
    :return: Deduplicated DataFrame with highest priority items kept.
    :rtype: pd.DataFrame
    """
    # Check if DataFrame is empty
    if df.empty:
        return df

    collection_priority = {"TARGETS": 1, "DIAGNOSTICS": 2, "CALIBRANTS": 3}

    def prioritize_group(group):
        # Sort the group by target_collection_type priority
        return group.sort_values(
            by="target_collection_type", key=lambda col: col.map(collection_priority)
        ).head(1)

    # Apply deduplication
    deduplicated_df = df.groupby(list(id_keys), as_index=False)[df.columns].apply(
        prioritize_group
    )
    return deduplicated_df.reset_index(drop=True)


def similarity_factor(
    cos_sim: float, threshold: float = 0.75, sharpness: int = 26
) -> float:
    """
    Calculate a similarity factor based on cosine similarity.
    This function applies a sigmoid-like transformation to the cosine similarity value,
    where values below the threshold are penalized more heavily.

    The default values are set so to reach a similarity factor of ~0.98 at a cosine similarity of 0.9,
    and a similarity factor of ~0 at a cosine similarity of 0.5.

    :param cos_sim: Cosine similarity value (between 0 and 1)
    :param threshold: Threshold below which the similarity factor drops sharply
    :param sharpness: Controls how steep the drop is
    :return: Similarity factor (between 0 and 1)
    :rtype: float
    """
    return 1 / (1 + np.exp(sharpness * (threshold - cos_sim)))
