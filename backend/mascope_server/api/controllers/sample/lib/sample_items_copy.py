from mascope_server.db.models import (
    MatchIsotope,
    MatchInterference,
    MatchIon,
    MatchCompound,
    MatchCollection,
    MatchSample,
)
from mascope_server.db.id import gen_id


async def copy_sample_item_match_data(
    original_sample_item, new_sample_item_id, session
):
    """
    Copies all match-related records (MatchIsotope, MatchInterference, MatchIon, MatchCompound, MatchCollection, MatchSample)
    from the original sample item to the new sample item within the provided session.

    This function performs the copying operation in the context of the given session, but it does not commit the changes.
    The calling function is responsible for committing the session if needed.

    :param original_sample_item: The original sample item from which match data will be copied.
    :type original_sample_item: SampleItem
    :param new_sample_item_id: The ID of the new sample item to which match data will be copied.
    :type new_sample_item_id: str
    :param session: The SQLAlchemy session to use for database operations.
    :type session: sqlalchemy.ext.asyncio.AsyncSession
    """

    # Copy related MatchIsotope records
    for match_isotope in original_sample_item.match_isotope:
        new_match_isotope_data = {
            c.name: getattr(match_isotope, c.name)
            for c in MatchIsotope.__table__.columns
            if c.name != "match_isotope_id"
        }
        new_match_isotope_data.update(
            {
                "match_isotope_id": gen_id(32),
                "sample_item_id": new_sample_item_id,
            }
        )
        new_match_isotope = MatchIsotope(**new_match_isotope_data)
        session.add(new_match_isotope)

    # Copy related MatchInterference records
    for match_interference in original_sample_item.match_interference:
        new_match_interference_data = {
            c.name: getattr(match_interference, c.name)
            for c in MatchInterference.__table__.columns
            if c.name != "match_interference_id"
        }
        new_match_interference_data.update(
            {
                "match_interference_id": gen_id(32),
                "sample_item_id": new_sample_item_id,
            }
        )
        new_match_interference = MatchInterference(**new_match_interference_data)
        session.add(new_match_interference)

    # Copy related MatchIon records
    for match_ion in original_sample_item.match_ion:
        new_match_ion_data = {
            c.name: getattr(match_ion, c.name)
            for c in MatchIon.__table__.columns
            if c.name != "match_ion_id"
        }
        new_match_ion_data.update(
            {
                "match_ion_id": gen_id(32),
                "sample_item_id": new_sample_item_id,
            }
        )
        new_match_ion = MatchIon(**new_match_ion_data)
        session.add(new_match_ion)

    # Copy related MatchCompound records
    for match_compound in original_sample_item.match_compound:
        new_match_compound_data = {
            c.name: getattr(match_compound, c.name)
            for c in MatchCompound.__table__.columns
            if c.name != "match_compound_id"
        }
        new_match_compound_data.update(
            {
                "match_compound_id": gen_id(32),
                "sample_item_id": new_sample_item_id,
            }
        )
        new_match_compound = MatchCompound(**new_match_compound_data)
        session.add(new_match_compound)

    # Copy related MatchCollection records
    for match_collection in original_sample_item.match_collection:
        new_match_collection_data = {
            c.name: getattr(match_collection, c.name)
            for c in MatchCollection.__table__.columns
            if c.name != "match_collection_id"
        }
        new_match_collection_data.update(
            {
                "match_collection_id": gen_id(32),
                "sample_item_id": new_sample_item_id,
            }
        )
        new_match_collection = MatchCollection(**new_match_collection_data)
        session.add(new_match_collection)

    # Copy related MatchSample records
    for match_sample in original_sample_item.match_sample:
        new_match_sample_data = {
            c.name: getattr(match_sample, c.name)
            for c in MatchSample.__table__.columns
            if c.name != "match_sample_id"
        }
        new_match_sample_data.update(
            {
                "match_sample_id": gen_id(32),
                "sample_item_id": new_sample_item_id,
            }
        )
        new_match_sample = MatchSample(**new_match_sample_data)
        session.add(new_match_sample)
