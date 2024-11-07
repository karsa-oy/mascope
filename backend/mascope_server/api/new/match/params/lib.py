import pandas as pd

from mascope_server.db import async_session
from mascope_server.db.models import Sample

from mascope_lib.instrument import instrument_type

from .schema import BaseMatchParams, TofMatchParams, OrbiMatchParams


def instrument_default_match_params(instrument_name: str):
    type = instrument_type(instrument_name)
    if type == "orbi":
        return OrbiMatchParams()
    elif type == "tof":
        return TofMatchParams()


async def default_match_params(sample_item_id: str):
    async with async_session() as session:
        sample = await session.get(Sample, sample_item_id)
    return instrument_default_match_params(sample.instrument)


def apply_match_params(
    match_isotope_df, match_params: BaseMatchParams = None
) -> pd.DataFrame:
    """
    Apply filtering logic to a isotope-lvl matches DataFrame.

    :param match_isotope_df: DataFrame containing match isotope data.
    :type match_isotope_df: pd.DataFrame
    :param match_params: Optional; Pydantic model of filtering parameters.
    :type match_params: MatchParams
    :return: DataFrame with applied filters.
    :rtype: pd.DataFrame
    """
    # Convert match_params Pydantic model to dictionary if provided
    provided_params = match_params.model_dump() if match_params else None

    def get_params(row):
        """
        Determine the match parameters to use based on the priority:
        1. Provided match parameters
        2. Ion-specific match parameters for the sample instrument
        3. Default match parameters
        """
        # If provided_params are available, use them for all rows
        if provided_params:
            return provided_params

        # If row-specific match_params are available for the instrument, use them
        if "filter_params" in row and row["instrument"] in row["filter_params"]:
            return row["filter_params"][row["instrument"]]

        # Fallback to default parameters
        return instrument_default_match_params(row["instrument"]).model_dump()

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
