import pandas as pd
import numpy as np
from sqlalchemy import asc, desc, func, select, delete, and_
from typing import List, Optional
from lib.file_func import load_file
from backend.db.id import gen_id
from backend.db import async_session
from ..utils.api_features import api_controller
from .instrument_functions_controller import (
    read_instrument_functions,
)
from ..exceptions import NotFoundException
from ..models.models import MatchInterference

# -------------------------------------------------------------------
# Main Logic Functions
# -------------------------------------------------------------------


async def compute_match_interferences(
    filename,
    target_isotopes_df,
) -> pd.DataFrame:
    """
    Computes match interferences for a given sample file based on specified target isotopes.

    This function calculates the raw intensities for each target isotope within the specified mass-to-charge (m/z) range,
    which are used to identify potential interferences in the sample's spectrum. It involves loading the sample file data,
    summing up the spectrum, and then computing the raw intensities for the target isotopes.

    Steps:
    1. Load the sample file and compute the summed spectrum across all time points.
    2. For each target isotope, calculate the raw intensity within a defined m/z range around the target m/z value.

    :param filename: Path to the sample file from which to compute interferences.
    :type filename: str
    :param target_isotopes_df: DataFrame containing the target isotopes and their m/z values.
    :type target_isotopes_df: pd.DataFrame
    :return: DataFrame with computed interferences for each target isotope.
    :rtype: pd.DataFrame
    :raises RuntimeError: If an error occurs during the computation process.
    """
    try:
        # Step 1: Load the sample file and compute the summed spectrum
        sample_file_data = load_file(filename, vars=["signal"])
        sum_spectrum = sample_file_data.signal.sum(dim="time").compute()

        # Read instrument resolution function
        _, R = await read_instrument_functions(filename)

        # Step 2: Initialize DataFrame for interferences and compute raw intensities for each target mz
        isotope_interference_df = target_isotopes_df.copy().assign(
            sample_peak_interference=np.nan,
        )

        def calc_raw_intensity(row):
            target_mz = row.mz
            dmz = (target_mz / R(target_mz)) / 2  # hwhm
            target_raw_intensity = sum_spectrum.sel(
                mz=slice(target_mz - dmz, target_mz + dmz)
            ).sum(dim="mz")
            row["match_interference_id"] = gen_id(length=32)
            row["sample_peak_interference"] = target_raw_intensity.compute().item()
            return row

        isotope_interference_df = isotope_interference_df.apply(
            calc_raw_intensity, axis=1
        )

        return isotope_interference_df
    except Exception as e:
        error_message = f"Computing match interferences failed: {e}"
        raise RuntimeError(error_message)


# -------------------------------------------------------------------
# Controller or Route Handlers
# -------------------------------------------------------------------


@api_controller()
async def get_match_interferences(
    target_isotope_id: Optional[str] = None,
    sample_item_id: Optional[str] = None,
    min_sample_peak_interference: Optional[float] = None,
    max_sample_peak_interference: Optional[float] = None,
    sort: Optional[str] = None,
    order: Optional[str] = None,
    page: int = 0,
    limit: int = 1000000,
) -> dict:
    """
    Retrieves a paginated list of match interferences, optionally filtered by various criteria, and sorted by a specified column.

    Steps:
    1. Construct a SQLAlchemy query to select all match interferences.
    2. Apply filtering based on provided parameters (target isotope ID, sample item ID, and sample peak interference range).
    3. Apply sorting based on the provided sort and order parameters.
    4. Apply pagination based on the provided page and limit parameters.
    5. Execute the query and fetch the results.
    6. Convert the results into a list of dictionaries for JSON serialization.

    :param target_isotope_id: Filter by target isotope ID, defaults to None.
    :type target_isotope_id: Optional[str], optional
    :param sample_item_id: Filter by sample item ID, defaults to None.
    :type sample_item_id: Optional[str], optional
    :param min_sample_peak_interference: Minimum sample peak interference value for filtering, defaults to None.
    :type min_sample_peak_interference: Optional[float], optional
    :param max_sample_peak_interference: Maximum sample peak interference value for filtering, defaults to None.
    :type max_sample_peak_interference: Optional[float], optional
    :param sort: Column to sort by, defaults to None.
    :type sort: Optional[str], optional
    :param order: Sorting order, 'asc' for ascending or 'desc' for descending, defaults to None.
    :type order: Optional[str], optional
    :param page: Page number for pagination, defaults to 0.
    :type page: int, optional
    :param limit: Number of items per page, defaults to 100.
    :type limit: int, optional
    :return: A dictionary containing the total count and a list of match interferences.
    :rtype: dict
    """
    async with async_session() as session:
        # Step 1: Construct a SQLAlchemy query to select all match interferences.
        stmt = select(MatchInterference)

        # Step 2: Apply filters based on parameters
        if target_isotope_id:
            stmt = stmt.filter(MatchInterference.target_isotope_id == target_isotope_id)
        if sample_item_id:
            stmt = stmt.filter(MatchInterference.sample_item_id == sample_item_id)
        if min_sample_peak_interference is not None:
            stmt = stmt.filter(
                MatchInterference.sample_peak_interference
                >= min_sample_peak_interference
            )
        if max_sample_peak_interference is not None:
            stmt = stmt.filter(
                MatchInterference.sample_peak_interference
                <= max_sample_peak_interference
            )

        # Step 3: Apply sorting
        if sort:
            sort_expression = (
                desc(getattr(MatchInterference, sort))
                if order == "desc"
                else asc(getattr(MatchInterference, sort))
            )
            stmt = stmt.order_by(sort_expression)

        # Step 4: Apply pagination
        total = await session.scalar(
            select(func.count()).select_from(stmt)  # pylint: disable=not-callable
        )
        stmt = stmt.offset(page * limit).limit(limit)

        # Step 5: Execute the query and return results
        result = await session.execute(stmt)
        match_interferences = result.scalars().all()

        # Step 6: Return results
        return {
            "results": total,
            "data": [
                match_interference.to_dict()
                for match_interference in match_interferences
            ],
        }


@api_controller()
async def get_match_interference(match_interference_id: str) -> dict:
    """
    Retrieves a single match interference by its unique ID.

    Steps:
    1. Execute a query to fetch the match interference with the specified ID.
    2. Check if the match interference exists. If not, raise a NotFoundException.
    3. Return the match interference's details as a dictionary.

    :param match_interference_id: Unique identifier of the match interference to retrieve.
    :type match_interference_id: str
    :raises NotFoundException: If the match interference with the given ID is not found.
    :return: The requested match interference's details.
    :rtype: dict
    """
    async with async_session() as session:
        match_interference = await session.get(MatchInterference, match_interference_id)
        if not match_interference:
            raise NotFoundException(
                f"Match interference with ID '{match_interference_id}' not found"
            )
        return match_interference.to_dict()


@api_controller()
async def delete_match_interferences(
    sample_item_ids: List[str], target_isotope_ids: Optional[List[str]] = None
):
    """
    This function deletes match interferences for a list of sample item IDs. If target isotope IDs are specified,
    only interferences corresponding to these isotopes are deleted.

    Steps:
    1. Start a new database session and construct a delete query for match interferences based on sample item IDs.
    2. If target isotope IDs are provided, apply an additional filter to restrict the deletion to those isotopes.
    3. Execute the delete query and commit the transaction to finalize the deletion.

    :param sample_item_ids: List of sample item IDs for which match interferences are to be deleted.
    :type sample_item_ids: List[str]
    :param target_isotope_ids: Optional list of target isotope IDs to filter match interferences, defaults to None
    :type target_isotope_ids: Optional[List[str]], optional
    """
    async with async_session() as session:
        query = delete(MatchInterference).where(
            MatchInterference.sample_item_id.in_(sample_item_ids)
        )
        if target_isotope_ids:
            query = query.where(
                MatchInterference.target_isotope_id.in_(target_isotope_ids)
            )
        await session.execute(query)
        await session.commit()


@api_controller()
async def create_match_interferences(
    match_interference_df: pd.DataFrame, sample_item_id: str
):
    """
    Creates match interferences for a given sample item based on the provided DataFrame of interference data.

    Steps:
    1. Check for existing match interferences to avoid duplication.
    2. Prepare the data for insertion based on the provided DataFrame.
    3. Insert the new match interferences into the database and commit the transaction.

    :param match_interference_df: DataFrame containing interference data for creating match interferences.
    :type match_interference_df: pd.DataFrame
    :param sample_item_id: ID of the sample item for which match interferences are being created.
    :type sample_item_id: str
    :raises RuntimeError: If match interferences already exist for the given sample item and isotopes.
    """
    print("Saving match interferences to database")
    # Step 1: Check for existing match interferences to avoid duplication.
    async with async_session() as session:
        target_isotope_refs = match_interference_df["target_isotope_id"].tolist()
        stmt = select(MatchInterference.match_interference_id).where(
            and_(
                MatchInterference.sample_item_id == sample_item_id,
                MatchInterference.target_isotope_id.in_(target_isotope_refs),
            )
        )
        result = await session.execute(stmt)
        match_interferences = result.all()
        # Step 2: If existing match interference are found, raise a RuntimeError to prevent overwriting.
        if match_interferences:
            raise RuntimeError(
                "Match interferences already exist for the given sample item and isotopes."
            )

        # Step 3: Prepare the data for insertion based on the provided DataFrame.
        match_interference_for_insertion = [
            MatchInterference(
                **{
                    key: value
                    for key, value in record.items()
                    if key in MatchInterference.__table__.columns
                },
                sample_item_id=sample_item_id,
            )
            for record in match_interference_df.to_dict(orient="records")
        ]

        # Step 4: Insert the new match interference into the database and commit the transaction.
        session.add_all(match_interference_for_insertion)
        await session.commit()
