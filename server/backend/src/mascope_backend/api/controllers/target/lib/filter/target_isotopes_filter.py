from mascope_backend.api.controllers.match.isotopes.match_isotopes_controller import (
    get_match_isotopes,
)
from mascope_backend.runtime import runtime


async def filter_existing_sample_match_isotope_data(target_isotopes_df, sample_item_id):
    """
    Filters out target isotopes for a given sample item that already have matches,
    ensuring that only isotopes without existing matches are considered for new match computation.

    This function checks existing matches for the given sample item and
    excludes those target isotopes from the provided DataFrame that already have matches.
    This helps in optimizing the match computation process by avoiding redundant calculations for isotopes
    that already have matches.

    Steps:
    1. Retrieve existing matches for the specified sample item.
    2. Identify target isotope IDs from existing matches.
    3. Filter out these isotopes from the provided DataFrame to exclude already matched isotopes.
    4. Return the filtered DataFrame, ready for further match computation processes.

    :param target_isotopes_df: DataFrame containing target isotopes to be considered for match computation.
    :type target_isotopes_df: pandas.DataFrame
    :param sample_item_id: Unique identifier of the sample item for which existing matches are to be checked.
    :type sample_item_id: str
    :raises RuntimeError: Raises an error if the process of fetching existing matches fails.
    :return: A filtered DataFrame excluding isotopes that already have matches.
    :rtype: pandas.DataFrame
    """
    try:
        # Step 1: Fetch existing matches for the given sample item.
        existing_match_isotopes = await get_match_isotopes(
            sample_item_id=sample_item_id
        )

        # Step 2: Compile sets of target isotope IDs from existing matches.
        existing_match_isotopes_ids = {
            match["target_isotope_id"] for match in existing_match_isotopes["data"]
        }
        # Step 3: Filter out isotopes from the DataFrame that already have matches.
        target_isotopes_df = target_isotopes_df[
            ~target_isotopes_df["target_isotope_id"].isin(existing_match_isotopes_ids)
        ]

        # Step 4: Return the filtered DataFrame, which now only contains isotopes without existing matches.
        return target_isotopes_df
    except Exception as e:
        error_message = f"Filtering existing matches failed: {e}"
        raise RuntimeError(error_message)
