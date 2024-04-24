import pandas as pd
import numpy as np
from sqlalchemy import asc, desc, func, select, delete, and_
from typing import List, Optional

from lib.file_func import get_instrument_type
from lib.peak import detect_peaks, get_peaks
from lib.chemistry import match_mz
from backend.db.id import gen_id
from backend.db import async_session
from ..utils.api_features import api_controller
from .instrument_functions_controller import (
    read_instrument_functions,
)
from ..exceptions import NotFoundException
from ..models.models import Match

# -------------------------------------------------------------------
# Main Logic Functions
# -------------------------------------------------------------------


async def compute_matches(
    filename, target_isotopes_df, min_isotope_abundance, instrument_functions=None
):
    """
    Computes matches for specified target isotopes within a sample file.

    This function identifies the best matching peaks within the sample spectrum for each target isotope based on
    their m/z values. It computes match statistics such as match score, m/z error, and isotope correlation.

    Steps:
    1. Load peaks from the sample file and prepare the data for matching.
    2. Match each target isotope to the closest peak within a predefined m/z tolerance window.
    3. Compute match statistics such as isotope correlations, m/z errors, and match score.
    4. Return a DataFrame containing the match details for each target isotope.

    :param filename: Path to the sample file to be analyzed for matches.
    :type filename: str
    :param target_isotopes_df: DataFrame containing target isotopes with their m/z values and other properties.
    :type target_isotopes_df: pd.DataFrame
    :param min_isotope_abundance: Minimum relative abundance threshold for isotopes to be considered in matching.
    :type min_isotope_abundance: float
    :param instrument_functions: Optional tuple containing peak shape details and a resolution function R.
    :type instrument_functions: tuple(dict, function), optional
    :return: DataFrame with details of the matches found for each target isotope.
    :rtype: pd.DataFrame
    :raises RuntimeError: If an error occurs during the matching process.

    Notes:
        - Matching is done on isotope-level. Ion, compound and collection level matches are aggregated from
        isotope-level matches on read sample operation; see the samples_controller.py for this aggregation.
    """
    try:
        # TODO min_isotope_abundance will be passed from the filter_params
        target_isotopes_df = target_isotopes_df[
            target_isotopes_df["relative_abundance"] >= min_isotope_abundance
        ].reset_index(drop=True)

        # Step 1: - Load or detect peaks
        # Find peaks and write to file
        u_list = list(np.unique(np.round(target_isotopes_df.mz)))
        # Check if instrument functions were passed
        if instrument_functions is None:
            instrument_functions = await read_instrument_functions(filename)
        instrument_type = get_instrument_type(filename)
        # Assign peak fitting threshold depending on the instrument type
        # Correct intrument type unsured by get_instrument_type
        if instrument_type == "orbi":
            threshold = 0.8
        if instrument_type == "tof":
            threshold = 0.9
        sample_file = await detect_peaks(
            filename,
            instrument_functions,
            threshold,
            u_list,
            if_exists="append",
            instrument_type=instrument_type,
        )
        peaks = get_peaks(sample_file, "area")

        # Step 2: - Prepare data
        # init match df from target isotopes
        match_isotope_df = target_isotopes_df.copy().assign(
            match_id=np.nan,
            sample_peak_id=np.nan,
            sample_peak_mz=np.nan,
            sample_peak_area=np.nan,
            sample_peak_area_relative=np.nan,
            match_abundance_error=np.nan,
            match_isotope_correlation=np.nan,
            match_mz_error=np.nan,
            match_score=np.nan,
        )

        # parse peak data
        peak_mzs = peaks.mz.values
        peak_areas = peaks.sum(dim="time").values
        peak_tofs = peaks.tof.values
        peak_sorting = np.argsort(peak_mzs)

        # Step 3: - Perform matching

        def match(row):
            # Get all peaks within unit mass window
            mz_tolerance = 0.5
            target_mz = row.mz
            match_indeces, _ = match_mz(
                target_mz, peak_mzs[peak_sorting], tolerance=mz_tolerance
            )
            # Find closest match
            for match_index in match_indeces:
                # get match peak
                peak_index = peak_sorting[match_index]
                peak_mz = peak_mzs[peak_index]
                peak_area = peak_areas[peak_index]
                # check current best match
                best_match = row.sample_peak_id
                if not np.isnan(best_match):
                    prev_mz_err = np.abs(row.sample_peak_mz - target_mz)
                    new_mz_err = np.abs(peak_mz - target_mz)
                    if new_mz_err > prev_mz_err:
                        continue
                # save match
                row["match_id"] = gen_id(length=32)
                row["sample_peak_id"] = peak_index
                row["sample_peak_mz"] = peak_mz
                row["sample_peak_tof"] = peak_tofs[int(peak_index)]
                row["sample_peak_area"] = peak_area
            return row

        match_isotope_df = (
            match_isotope_df.apply(match, axis=1)
            .dropna(subset=["sample_peak_mz"])
            .reset_index()
        )

        # Step 4: - Calculate match stats

        # calculate isotope ratios
        # sum matched sample peak heights for each ion
        ion_level_peak_sums = match_isotope_df.groupby(
            ["target_ion_id"], as_index=False
        )["sample_peak_area"].sum()
        # join sums back to the isotope level
        isotope_level_peak_sums = pd.merge(
            match_isotope_df,
            ion_level_peak_sums.rename(
                columns={"sample_peak_area": "sample_peak_area_sum"}
            ),
            on=["target_ion_id"],
            how="left",
        )

        # compute relative peak heights
        match_isotope_df.loc[:, "sample_peak_area_relative"] = (
            match_isotope_df["sample_peak_area"]
            / isotope_level_peak_sums["sample_peak_area_sum"]
        )
        # calculate isotope ratio errors
        match_isotope_df.loc[:, "match_abundance_error"] = match_isotope_df[
            "relative_abundance"
        ] * (
            match_isotope_df["sample_peak_area_relative"]
            - match_isotope_df["relative_abundance"]
        )
        # calculate isotope correlations
        match_isotope_df = match_isotope_df.groupby(
            ["target_ion_id"], group_keys=False
        ).apply(
            lambda ion_group: (
                ion_group.assign(
                    match_isotope_correlation=(
                        np.corrcoef(
                            np.array(
                                [
                                    peaks.sel(mz=peak_mz, method="nearest")
                                    for peak_mz in ion_group["sample_peak_mz"]
                                ]
                            )
                        )[0, 1]
                        if len(ion_group) > 1
                        else 1
                    )
                )
            )
        )
        match_isotope_df["match_isotope_correlation"] = match_isotope_df[
            "match_isotope_correlation"
        ].fillna(value=0)

        # calculate mz errors
        match_isotope_df.loc[:, "match_mz_error"] = (
            1e6
            * (match_isotope_df["sample_peak_mz"] - match_isotope_df["mz"])
            / match_isotope_df["mz"]
        )

        def score(row):
            row["match_score"] = (1 - abs(row.match_abundance_error)) * max(
                0, (1 - 1e-2 * abs(row.match_mz_error))
            )
            return row

        match_isotope_df = match_isotope_df.apply(
            score, axis=1, result_type="broadcast"
        )
        return match_isotope_df
    except Exception as e:
        error_message = f"Computing matches failed: {e}"
        raise RuntimeError(error_message)


# -------------------------------------------------------------------
# Controller or Route Handlers
# -------------------------------------------------------------------


@api_controller()
async def get_matches(
    sample_item_id: Optional[str] = None,
    target_isotope_id: Optional[str] = None,
    sort: str = None,
    order: str = None,
    page: int = 0,
    limit: int = 1000000,
) -> dict:
    """
    Retrieves a paginated list of matches, optionally filtered by sample item ID and target isotope ID, and sorted by a specified column.

    Steps:
    1. Construct a SQLAlchemy query to select all matches.
    2. Apply filtering based on provided parameters.
    3. Apply sorting based on the provided sort and order parameters.
    4. Apply pagination based on the provided page and limit parameters.
    5. Execute the query and fetch the results.
    6. Convert the results into a list of dictionaries for JSON serialization.

    :param sample_item_id: Filter by sample item ID, defaults to None.
    :type sample_item_id: Optional[str], optional
    :param target_isotope_id: Filter by target isotope ID, defaults to None.
    :type target_isotope_id: Optional[str], optional
    :param sort: Column to sort by, defaults to None.
    :type sort: str, optional
    :param order: Sorting order, defaults to None.
    :type order: str, optional
    :param page: Page number for pagination, defaults to 0.
    :type page: int, optional
    :param limit: Number of items per page, defaults to a large number.
    :type limit: int, optional
    :return: A dictionary with the total count and a list of matches.
    :rtype: dict
    """
    async with async_session() as session:
        # Step 1: Construct a SQLAlchemy query to select all matches.
        stmt = select(Match)

        # Step 2: Apply filters if specified
        if sample_item_id:
            stmt = stmt.filter(Match.sample_item_id == sample_item_id)
        if target_isotope_id:
            stmt = stmt.filter(Match.target_isotope_id == target_isotope_id)

        # Step 3: Apply sorting
        if sort:
            sort_expression = (
                desc(getattr(Match, sort))
                if order == "desc"
                else asc(getattr(Match, sort))
            )
            stmt = stmt.order_by(sort_expression)

        # Step 4: Apply pagination
        total = await session.scalar(
            select(func.count()).select_from(stmt)  # pylint: disable=not-callable
        )
        stmt = stmt.offset(page * limit).limit(limit)

        # Step 5: Execute query
        result = await session.execute(stmt)
        matches = result.scalars().all()

        # Step 6: Return results
        return {"results": total, "data": [match.to_dict() for match in matches]}


@api_controller()
async def get_match(match_id: str) -> dict:
    """
    Retrieves a single match by its unique ID.

    Steps:
    1. Execute a query to fetch the match with the specified ID.
    2. Check if the match exists. If not, raise a NotFoundException.
    3. Return the match's details as a dictionary.

    :param match_id: Unique identifier of the match to retrieve.
    :type match_id: str
    :return: The requested match's details.
    :rtype: dict
    :raises NotFoundException: If the match with the given ID is not found.
    """
    async with async_session() as session:
        # Step 1: Fetch match by ID
        match = await session.get(Match, match_id)

        # Step 2: Check existence
        if not match:
            raise NotFoundException(f"Match with ID '{match_id}' not found")

        # Step 3: Return match details
        return match.to_dict()


@api_controller()
async def delete_matches(
    sample_item_ids: List[str], target_isotope_ids: Optional[List[str]] = None
):
    """
    Deletes matches for specified sample items, optionally filtered by target isotope IDs.
    This operation supports batch deletion and can be restricted to specific isotopes if needed.

    Steps:
    1. Start a new database session and construct a delete query for matches based on sample item IDs.
    2. If target isotope IDs are provided, apply an additional filter to restrict the deletion to those isotopes.
    3. Execute the delete query and commit the transaction to finalize the deletion.

    :param sample_item_ids: List of sample item IDs for which matches are to be deleted.
    :type sample_item_ids: List[str]
    :param target_isotope_ids: Optional list of target isotope IDs to further filter the matches to be deleted.
    :type target_isotope_ids: Optional[List[str]]
    """
    async with async_session() as session:
        query = delete(Match).where(Match.sample_item_id.in_(sample_item_ids))
        if target_isotope_ids:
            query = query.where(Match.target_isotope_id.in_(target_isotope_ids))
        await session.execute(query)
        await session.commit()


@api_controller()
async def create_matches(match_isotope_df: pd.DataFrame, sample_item_id: str):
    """
    Creates matches for a given sample item based on the provided DataFrame of isotopes.

    This function checks for existing matches for the given sample item and isotopes to avoid duplications.
    New matches are then created and saved to the database.

    Steps:
    1. Start a new database session and construct a query to check for existing matches for the sample item and isotopes.
    2. If existing matches are found, raise a RuntimeError to prevent overwriting.
    3. Prepare the data for insertion based on the provided DataFrame.
    4. Insert the new matches into the database and commit the transaction.

    :param match_isotope_df: DataFrame containing isotope data for creating matches.
    :type match_isotope_df: pd.DataFrame
    :param sample_item_id: ID of the sample item for which matches are being created.
    :type sample_item_id: str
    :raises RuntimeError: If matches already exist for the given sample item and isotopes.
    """
    print("Saving matches to database")
    # Step 1: Check for existing matches for the sample item and isotopes
    async with async_session() as session:
        # Extract the required target_isotope_id values
        target_isotope_refs = match_isotope_df["target_isotope_id"].tolist()
        stmt = select(Match.match_id).where(
            and_(
                Match.sample_item_id == sample_item_id,
                Match.target_isotope_id.in_(target_isotope_refs),
            )
        )
        result = await session.execute(stmt)
        matches = result.all()
        # Step 2: If existing matches are found, raise a RuntimeError to prevent overwriting.
        if matches:
            raise RuntimeError(
                "Matches already exist for the given sample item and isotopes."
            )

        # Step 3: Prepare the data for insertion based on the provided DataFrame.
        match_isotope_for_insertion = [
            Match(
                **{
                    key: value
                    for key, value in record.items()
                    if key in Match.__table__.columns
                },
                sample_item_id=sample_item_id,
            )
            for record in match_isotope_df.to_dict(orient="records")
        ]
        # Step 4: Insert the new matches into the database and commit the transaction.
        session.add_all(match_isotope_for_insertion)
        await session.commit()
