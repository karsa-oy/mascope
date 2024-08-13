import pandas as pd
from mascope_server.api.controllers.match.isotopes.match_isotopes_controller import (
    get_match_isotopes,
)
from mascope_server.api.controllers.match.interferences.match_interferences_controller import (
    get_match_interferences,
)
from mascope_server.api.models.match.match_pydantic_model import (
    FilterParams,
)

import mascope_runtime as runtime

logger = runtime.logger.service("backend")


async def filter_existing_sample_match_isotope_data(target_isotopes_df, sample_item_id):
    """
    Filters out target isotopes for a given sample item that already have matches or match interferences,
    ensuring that only isotopes without existing matches are considered for new match computation.

    This function checks existing matches and match interferences for the given sample item and
    excludes those target isotopes from the provided DataFrame that already have matches or interferences.
    This helps in optimizing the match computation process by avoiding redundant calculations for isotopes
    that already have matches.

    Steps:
    1. Retrieve existing matches and match interferences for the specified sample item.
    2. Identify target isotope IDs from existing matches and interferences.
    3. Filter out these isotopes from the provided DataFrame to exclude already matched isotopes.
    4. Return the filtered DataFrame, ready for further match computation processes.

    :param target_isotopes_df: DataFrame containing target isotopes to be considered for match computation.
    :type target_isotopes_df: pandas.DataFrame
    :param sample_item_id: Unique identifier of the sample item for which existing matches and interferences are to be checked.
    :type sample_item_id: str
    :raises RuntimeError: Raises an error if the process of fetching existing matches or interferences, or filtering fails.
    :return: A filtered DataFrame excluding isotopes that already have matches or interferences.
    :rtype: pandas.DataFrame
    """
    try:
        # Step 1: Fetch existing matches and interferences for the given sample item.
        existing_match_isotopes = await get_match_isotopes(
            sample_item_id=sample_item_id
        )
        existing_interferences = await get_match_interferences(
            sample_item_id=sample_item_id
        )

        # Step 2: Compile sets of target isotope IDs from existing matches and interferences.
        existing_match_isotopes_ids = {
            match["target_isotope_id"] for match in existing_match_isotopes["data"]
        }
        existing_interference_ids = {
            interference["target_isotope_id"]
            for interference in existing_interferences["data"]
        }

        # Step 3: Filter out isotopes from the DataFrame that already have matches or interferences.
        target_isotopes_df = target_isotopes_df[
            ~target_isotopes_df["target_isotope_id"].isin(
                existing_match_isotopes_ids | existing_interference_ids
            )
        ]

        # Step 4: Return the filtered DataFrame, which now only contains isotopes without existing matches or interferences.
        return target_isotopes_df
    except Exception as e:
        error_message = f"Filtering existing matches and interferences failed: {e}"
        raise RuntimeError(error_message)


def apply_filter_params(
    match_isotope_df, filter_params: FilterParams = None
) -> pd.DataFrame:
    """
    Apply filtering logic to a isotope-lvl matches DataFrame.

    :param match_isotope_df: DataFrame containing match isotope data.
    :type match_isotope_df: pd.DataFrame
    :param filter_params: Optional; Pydantic model of filtering parameters.
    :type filter_params: FilterParams
    :return: DataFrame with applied filters.
    :rtype: pd.DataFrame
    """
    # Convert filter_params Pydantic model to dictionary if provided
    provided_params = filter_params.model_dump() if filter_params else None

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
        default_params = FilterParams().model_dump()
        # Fallback to default parameters
        return default_params

    def filter_row(row):
        """
        Apply filtering logic to the given row based on the determined parameters.
        """
        # Determine which filter parameters to use for the current row
        params = get_params(row)

        # Check for None/NaN in necessary for filtering fields to ensure they can be processed
        valid_data = True
        for field in [
            "match_mz_error",
            "match_abundance_error",
            "match_isotope_correlation",
            "sample_peak_area",
            "relative_abundance",
        ]:
            if pd.isna(row[field]) or row.get(field) is None:
                # Assign match_category to NaN value by assigning None
                row["match_category"] = None
                valid_data = False
                break
        if not valid_data:
            return row

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
    filtered_df = match_isotope_df.apply(filter_row, axis=1)

    return filtered_df
