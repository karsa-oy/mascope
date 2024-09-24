import pandas as pd
import numpy as np

from mascope_server.runtime import runtime


def sort_and_paginate_match_sample_df(
    df: pd.DataFrame, order: str, page: int, limit: int
) -> pd.DataFrame:
    """
    Sorts and paginates the DataFrame for match sample data. Used in endpoints match_sample_targets_controller
    Handles NaN values by treating them as -1 for sorting purposes and ensures JSON compatibility.

    Steps:
    1. Replace NaN values in 'match_score' and 'match_category' with -1 for sorting purposes.
    2. Convert 'match_category' to integer type.
    3. Sort the DataFrame by 'target_collection_id', 'match_category', and 'match_score'.
    4. Paginate the sorted DataFrame based on the 'page' and 'limit' parameters.
    5. Replace -1 back to None for 'match_score' and 'match_category'.
    6. Replace all other NaN and NaT values with None for JSON compatibility.

    :param df: DataFrame containing the match sample data to be sorted and paginated.
    :type df: pd.DataFrame
    :param order: Sorting order ('asc' or 'desc').
    :type order: str
    :param page: Page number for pagination.
    :type page: int
    :param limit: Number of items per page.
    :type limit: int
    :return: Sorted and paginated DataFrame with JSON compatible values.
    :rtype: pd.DataFrame
    """
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

    # Pagination logic
    df = df.iloc[page * limit : (page + 1) * limit]

    # Replace -1 back to None for match_category and match_score if it was originally NaN
    df["match_score"] = df["match_score"].replace(-1, None)
    df["match_category"] = df["match_category"].replace(-1, None)

    # Replace all other NaN and NaT with None for JSON compatibility
    df = df.replace([np.nan, pd.NaT], None)

    return df
