from sqlalchemy import select
from sqlalchemy.orm import joinedload
from mascope_server.db import async_session
from mascope_server.db.models import (
    TargetCollection,
)
from mascope_server.api.lib.exceptions.api_exceptions import NotFoundException

from mascope_server.runtime import runtime


async def fetch_target_collection(
    target_collection_id: str, session=None
) -> TargetCollection:
    """
    Retrieves a target collection from the database by its ID, including its associated sample batches
    and target compounds. This function is used to ensure the correct retrieval of a target collection
    along with its relationships for operations like creation, update, and deletion.

    :param target_collection_id: The ID of the target collection to fetch.
    :type target_collection_id: str
    :param session: An optional existing session to use for the query.
    :type session: sqlalchemy.ext.asyncio.AsyncSession, optional
    :return: The target collection with its associated sample batches and target compounds.
    :rtype: TargetCollection
    :raises NotFoundException: If the target collection with the specified ID is not found.
    """
    close_session = False
    if session is None:
        session = async_session()
        close_session = True

    stmt = (
        select(TargetCollection)
        .options(
            joinedload(TargetCollection.sample_batch),
            joinedload(TargetCollection.target_compound),
        )
        .where(TargetCollection.target_collection_id == target_collection_id)
    )
    result = await session.execute(stmt)
    target_collection = result.unique().scalar_one_or_none()

    if close_session:
        await session.close()

    if not target_collection:
        raise NotFoundException(
            f"Target collection with ID '{target_collection_id}' not found"
        )

    return target_collection
