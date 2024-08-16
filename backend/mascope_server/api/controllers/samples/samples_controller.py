# pylint: disable=line-too-long
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    asc,
    desc,
    and_,
    select,
    func,
    cast,
    Float,
)
from mascope_server.db import async_session
from mascope_server.db.models import (
    SampleItem,
    Sample,
    MatchSample,
    MatchCollection,
    TargetCollection,
)
from mascope_server.api.lib.api_features import api_controller
from mascope_server.api.lib.exceptions.api_exceptions import NotFoundException


@api_controller()
async def get_samples(
    sample_item_id: str = None,
    sample_file_id: str = None,
    sample_batch_id: str = None,
    filename: str = None,
    instrument: str = None,
    sample_item_type: str = None,
    datetime_min: datetime = None,
    datetime_max: datetime = None,
    match_category: Optional[int] = None,
    sort: str = "datetime_utc",
    order: str = "asc",
    page: int = 0,
    limit: int = 10000,
) -> dict:
    """
    Retrieves samples (combined sample item and sample file info) based on filter criteria and pagination settings.
    Additionally, it can include match information for the samples if available, along with the match unique target collection types
    associated with the sample's matches.

    Steps:
    1. Construct the base query with filters based on provided parameters.
    2. Apply sorting and pagination to the query.
    3. Execute the query and fetch results.
    4. Add unique match target collection types (`match_collection_types`) to each sample's result if there are matches.

    :param sample_item_id: Filter by sample item ID.
    :type sample_item_id: str, optional
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
    :param match_category: Filter by match category.
    :type match_category: int, optional
    :param sort: Column to sort the results by.
    :type sort: str, optional
    :param order: Sort order ('asc' or 'desc').
    :type order: str, optional
    :param page: Pagination page number.
    :type page: int, optional
    :param limit: Number of results per page.
    :type limit: int, optional
    :return: A dictionary containing the total number of results, the formatted sample data, and optionally match information.
    :rtype: dict
    """
    async with async_session() as session:
        # Step 1: Construct base query with joins to include MatchSample, MatchCollection, and TargetCollection data
        stmt = (
            select(
                Sample,
                MatchSample,
                func.group_concat(
                    func.distinct(TargetCollection.target_collection_type)
                ).label("match_collection_types"),
            )
            .outerjoin(MatchSample, Sample.sample_item_id == MatchSample.sample_item_id)
            .outerjoin(
                MatchCollection,
                MatchCollection.sample_item_id == Sample.sample_item_id,
            )
            .outerjoin(
                TargetCollection,
                TargetCollection.target_collection_id
                == MatchCollection.target_collection_id,
            )
            .group_by(Sample.sample_item_id, MatchSample.sample_item_id)
        )

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
        if match_category is not None:
            stmt = stmt.filter(MatchSample.match_category == match_category)

        # Step 2: Apply sorting and pagination
        if sort:
            order_function = desc if order == "desc" else asc
            stmt = stmt.order_by(order_function(getattr(Sample, sort)))

        # Get total count
        count_stmt = select(func.count()).select_from(  # pylint: disable=not-callable
            stmt.subquery()
        )
        total = await session.scalar(count_stmt)

        # Get paginated results
        stmt = stmt.offset(page * limit).limit(limit)

        # Step 3: Execute query and fetch results
        results = await session.execute(stmt)

    # Construct the response data
    data = []
    for sample, match, match_collection_types in results.all():
        sample_dict = {**sample.to_dict(), **(match.to_dict() if match else {})}
        if match and match_collection_types:
            sample_dict["match_collection_types"] = match_collection_types.split(",")
        data.append(sample_dict)

    return {
        "results": total,
        "data": data,
    }


@api_controller()
async def get_sample(
    sample_item_id: str,
) -> dict:
    """
    Retrieves detailed information for a specific sample, including optional match data and match collection types if available.

    This function joins the sample with match data and includes the list of unique collection types associated with the sample's matches.

    :param sample_item_id: Unique identifier for the sample.
    :type sample_item_id: str
    :return: A dictionary containing detailed sample information, match data (if available), and match collection types (if available).
    :rtype: dict
    :raises NotFoundException: If the sample with the specified item ID is not found.
    """
    # Check sample item by ID
    async with async_session() as session:
        sample_item = await session.get(SampleItem, sample_item_id)
    if not sample_item:
        raise NotFoundException(f"Sample item with ID '{sample_item_id}' not found")

    async with async_session() as session:
        # Construct query with joins to include MatchSample, MatchCollection, and TargetCollection data
        stmt = (
            select(
                Sample,
                MatchSample,
                func.group_concat(
                    func.distinct(TargetCollection.target_collection_type)
                ).label("match_collection_types"),
            )
            .outerjoin(MatchSample, Sample.sample_item_id == MatchSample.sample_item_id)
            .outerjoin(
                MatchCollection,
                MatchCollection.sample_item_id == Sample.sample_item_id,
            )
            .outerjoin(
                TargetCollection,
                TargetCollection.target_collection_id
                == MatchCollection.target_collection_id,
            )
            .where(Sample.sample_item_id == sample_item_id)
            .group_by(Sample.sample_item_id, MatchSample.sample_item_id)
        )

        # Execute query and fetch results
        result = await session.execute(stmt)
    sample, match_sample, match_collection_types = result.first()

    # Construct the response data
    sample_data = sample.to_dict() if sample else {}
    match_sample_data = match_sample.to_dict() if match_sample else {}

    # Merge data, with match_sample data overlaying sample data where available
    sample_data.update(match_sample_data)

    # Include match_collection_types if there are any matches
    if match_sample and match_collection_types:
        sample_data["match_collection_types"] = match_collection_types.split(",")

    return sample_data
