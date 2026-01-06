from typing import NamedTuple

from sqlalchemy import (
    select,
)

from mascope_backend.db import (
    MatchCollection,
    MatchCompound,
    MatchIon,
    MatchIsotope,
    MatchSample,
    async_session,
)
from mascope_backend.db.id import gen_id
from mascope_backend.socket.notifications import (
    UserNotification,
    send_progress_user_notification,
)


class CopyMatches(NamedTuple):
    original_sample_item_id: str
    new_sample_item_id: str


async def copy_sample_items_match_data(
    copy_commands: list[CopyMatches],
    notification: UserNotification = None,
):
    """
    Copies all match-related records (MatchIsotope, MatchIon, MatchCompound, MatchCollection, MatchSample)
    from the original sample item to the new sample item

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

    async def copy_match_records(command, model, progress_increment):
        async with async_session() as session:
            query = select(model).where(
                model.sample_item_id == command.original_sample_item_id
            )
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
                        "sample_item_id": command.new_sample_item_id,
                    }
                )
                new_record = model(**new_record_data)
                session.add(new_record)
            await session.commit()

        if notification:
            await send_progress_user_notification(notification, progress_increment)

    # calculate progress from step index and within-step progress
    total = len(copy_commands)

    def progress(step_index, step_prog):
        return (step_index - 1) / total + step_prog / total

    # execute through copy commands, reporting progress
    for i, command in enumerate(copy_commands):
        await send_progress_user_notification(notification, progress(i, 0))
        await copy_match_records(command, MatchIsotope, progress(i, 0.25))
        await copy_match_records(command, MatchIon, progress(i, 0.50))
        await copy_match_records(command, MatchCompound, progress(i, 0.75))
        await copy_match_records(command, MatchCollection, progress(i, 0.90))
        await copy_match_records(command, MatchSample, progress(i, 0.95))
