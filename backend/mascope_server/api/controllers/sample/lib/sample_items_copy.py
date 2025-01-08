from sqlalchemy import (
    select,
)
from mascope_server.db.models import (
    MatchIsotope,
    MatchInterference,
    MatchIon,
    MatchCompound,
    MatchCollection,
    MatchSample,
)
from mascope_server.db.id import gen_id
from mascope_server.socket.notifications import (
    UserNotification,
    send_progress_user_notification,
)


async def copy_sample_item_match_data(
    original_sample_item_id: str,
    new_sample_item_id: str,
    session,
    notification: UserNotification = None,
):
    """
    Copies all match-related records (MatchIsotope, MatchInterference, MatchIon, MatchCompound, MatchCollection, MatchSample)
    from the original sample item to the new sample item within the provided session.

    This function performs the copying operation in the context of the given session, but it does not commit the changes.
    The calling function is responsible for committing the session if needed.

    :param original_sample_item_id: The ID of the original sample item from which match data will be copied.
    :type original_sample_item_id: str
    :param new_sample_item_id: The ID of the new sample item to which match data will be copied.
    :type new_sample_item_id: str
    :param session: The SQLAlchemy session to use for database operations.
    :type session: sqlalchemy.ext.asyncio.AsyncSession
    :param notification: Optional notification for sending progress user notifications of match copying.
    :type notification: UserNotification, optional
    """

    async def copy_match_records(model, progress_increment):
        query = select(model).filter(model.sample_item_id == original_sample_item_id)
        result = await session.execute(query)
        match_records = result.scalars().all()

        for match_record in match_records:
            new_record_data = {
                c.name: getattr(match_record, c.name)
                for c in model.__table__.columns
                if c.name != f"{model.__tablename__}_id"
            }
            new_record_data.update(
                {
                    f"{model.__tablename__}_id": gen_id(32),
                    "sample_item_id": new_sample_item_id,
                }
            )
            new_record = model(**new_record_data)
            session.add(new_record)

        if notification:
            await send_progress_user_notification(notification, progress_increment)

    # Copy each type of match record with progress tracking
    await copy_match_records(MatchIsotope, 0.25)
    await copy_match_records(MatchInterference, 0.5)
    await copy_match_records(MatchIon, 0.75)
    await copy_match_records(MatchCompound, 0.85)
    await copy_match_records(MatchCollection, 0.9)
    await copy_match_records(MatchSample, 0.95)
