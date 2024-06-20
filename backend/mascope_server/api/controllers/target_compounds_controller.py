from fastapi import HTTPException
from sqlalchemy import asc, desc, func, select, or_, and_
from sqlalchemy.orm import aliased
from typing import List, Optional
from mascope_server.api_sio import sio
from mascope_server.db.id import gen_id
from mascope_server.db import async_session
from mascope_lib.util import norm
from ..utils.api_features import api_controller
from ..exceptions import NotFoundException
from .ionization_mechanisms_controller import get_ionization_mechanisms
from .target_ions_controller import create_target_ions
from ..models.models import (
    IonizationMechanism,
    TargetCompound,
    TargetCompoundInTargetCollection,
    TargetCollectionInSampleBatch,
)
from ..models.pydantic_models.target_compound_pydantic_model import (
    TargetCompoundBase,
    TargetCompoundUpdate,
)

# TODO_target_compound_management refactor to use same strucutre as other controllers


# -------------------------------------------------------------------
# Utility Functions
# -------------------------------------------------------------------


async def get_affected_batches_and_collections(target_compound_id: str):
    async with async_session() as session:
        # Get the target collections for this compound
        target_collections = await session.execute(
            select(TargetCompoundInTargetCollection.target_collection_id).where(
                TargetCompoundInTargetCollection.target_compound_id
                == target_compound_id
            )
        )
        target_collections_ids = {tc[0] for tc in target_collections}

        # Get all affected sample batches
        sample_batches = await session.execute(
            select(TargetCollectionInSampleBatch.sample_batch_id).where(
                TargetCollectionInSampleBatch.target_collection_id.in_(
                    target_collections_ids
                )
            )
        )
        sample_batches_ids = {sb[0] for sb in sample_batches}

        return sample_batches_ids, target_collections_ids


# -------------------------------------------------------------------
# Controller or Route Handlers
# -------------------------------------------------------------------


@api_controller()
async def get_target_compounds(
    target_compound_name: Optional[str] = None,
    target_compound_formula: Optional[str] = None,
    sample_batch_id: Optional[str] = None,
    show_duplicates: bool = False,
    sort: str = None,
    order: str = None,
    page: int = 0,
    limit: int = 10000,
) -> dict:
    async with async_session() as session:
        # Define the main query for target compounds
        stmt = select(TargetCompound)

        # Apply filters if any
        if target_compound_name:
            stmt = stmt.filter(
                TargetCompound.target_compound_name == target_compound_name
            )
        if target_compound_formula:
            stmt = stmt.filter(
                TargetCompound.target_compound_formula == target_compound_formula
            )

        # Adjust the query based on sample_batch_id filter
        if sample_batch_id or show_duplicates:
            # Alias for TargetCompoundInTargetCollection to be able to add to SELECT the target_collection_id
            tcitc_alias = aliased(TargetCompoundInTargetCollection)

            stmt = stmt.join(
                tcitc_alias,
                tcitc_alias.target_compound_id == TargetCompound.target_compound_id,
            ).join(
                TargetCollectionInSampleBatch,
                TargetCollectionInSampleBatch.target_collection_id
                == tcitc_alias.target_collection_id,
            )

            if sample_batch_id:
                stmt = stmt.filter(
                    TargetCollectionInSampleBatch.sample_batch_id == sample_batch_id
                )

            if show_duplicates:
                # Select the target_collection_id if duplicates are to be shown
                stmt = stmt.add_columns(tcitc_alias.target_collection_id).distinct()

            if not show_duplicates:
                # Apply distinct only if duplicates should not be shown
                stmt = stmt.distinct()

        # Apply sorting if specified
        if sort:
            if order == "desc":
                stmt = stmt.order_by(desc(getattr(TargetCompound, sort)))
            else:
                stmt = stmt.order_by(asc(getattr(TargetCompound, sort)))

        # Pagination logic
        count_stmt = select(func.count()).select_from(  # pylint: disable=not-callable
            stmt.subquery()
        )
        total = await session.scalar(count_stmt)

        stmt = stmt.offset(page * limit).limit(limit)
        result = await session.execute(stmt)

        # Construct the response data
        data = []
        for row in result.all():
            # When duplicates are shown, include target_collection_id
            compound_data = row.TargetCompound.to_dict()
            if show_duplicates:
                compound_data["target_collection_id"] = row.target_collection_id
            data.append(compound_data)

        return {
            "results": total,
            "data": data,
        }


@api_controller()
async def get_target_compound(target_compound_id: str) -> dict:
    """
    Retrieves a single target compound by its unique ID.

    Steps:
    1. Execute a query to fetch the target compound with the specified ID.
    2. Check if the target compound exists. If not, raise a NotFoundException.
    3. Return the target compound's details as a dictionary.

    :param sample_batch_id: Unique identifier of the target compound to retrieve.
    :type sample_batch_id: str
    :raises NotFoundException: If the target compound with the given ID is not found.
    :return: The requested target compound's details.
    :rtype: dict
    """
    async with async_session() as session:
        # Step 1: Fetch target compound by ID
        target_compound = await session.get(TargetCompound, target_compound_id)

        if not target_compound:
            # Step 2: If target compound not found, raise exception
            raise NotFoundException(
                f"Target compound with ID '{target_compound_id}' not found"
            )
    # Step 3: Return target compound details
    return target_compound.to_dict()


@api_controller()
async def create_target_compound(
    target_compounds: List[TargetCompoundBase],
    independent_transaction=False,
    session=None,
) -> dict:
    """Function to create a target compound record(s) and derived target ions and isotopes

    For each target compound to create:
    1. Check for existing records in the database with either similar name+formula or CAS number
        - If no matching records, move to step 2
        - If one matching record exists
            - If match is based on name+formula
              AND existing record is missing CAS number
              AND new record has CAS number
              THEN update the record with CAS number
            - No need to create new record, continue to next compound
        - If > 1 matching records exist
            - Check for actual duplicates in the database (similar name+formula+CAS number)
              - If duplicates, raise RuntimeError
              - Else, no need to create new record, continue to next compound
    2. Create new target compound record and derived target ions and isotopes
    3. Notify clients about new target compounds

    TODO: Different kinds of inconsistencies between new and existing records could be handled better. E.g. if the new record has similar
    name+formula but different CAS number than an existing record, the existing record will be used and the inconsistency between CAS
    numbers is silently ignored.

    :param target_compounds: List of target compounds to create
    :type target_compounds: List[TargetCompoundBase]
    :param independent_transaction: Flag indicating whether the create target compound is an independent transaction, defaults to False
    :type independent_transaction: bool, optional
    :param session: Database session, smust be gicen if not an independent transaction, defaults to None
    :type session: SQLAlchemy.AsyncSession, optional
    :raises RuntimeError: Database is malformed
    :return: Return created target compounds, skipped compounds (already existing) and message log
    :rtype: dict
    """
    if independent_transaction:
        session = async_session()

    # initialize list of targets to return
    target_compound_ids = []
    existing_target_compounds = []
    # initalized lists of targets to create
    target_compounds_to_create = []
    # Initialize message log
    message_log = {}

    for i, target_compound in enumerate(target_compounds):
        # Initialize messages list
        message_log[i + 1] = {
            "status_code": 0,
            "messages": [],
        }
        # STEP 1: check if the compound record is already in the database (similar name and formula or CAS number)
        existing_compounds = await session.execute(
            select(TargetCompound).filter(
                or_(
                    # Similar CAS number
                    and_(
                        TargetCompound.cas_number is not None,
                        (
                            TargetCompound.cas_number
                            == norm(target_compound.cas_number)
                            if target_compound.cas_number
                            else None
                        ),
                    ),
                    # Similar name and formula
                    and_(
                        func.lower(TargetCompound.target_compound_formula)
                        == norm(target_compound.target_compound_formula, lower=True),
                        func.lower(TargetCompound.target_compound_name)
                        == norm(target_compound.target_compound_name, lower=True),
                    ),
                )
            )
        )
        existing_compounds = existing_compounds.scalars().all()
        existing_target_compounds += existing_compounds
        if len(existing_compounds) == 0:
            # save the new compound for creation if it doesn't exist
            target_compound = TargetCompound(
                target_compound_id=gen_id(),
                target_compound_name=norm(target_compound.target_compound_name),
                target_compound_formula=norm(target_compound.target_compound_formula),
                cas_number=(
                    norm(target_compound.cas_number)
                    if target_compound.cas_number
                    else None
                ),
            )

            target_compounds_to_create.append(target_compound)
            target_compound_ids.append(target_compound.target_compound_id)

            message_log[i + 1]["status_code"] = 201
            message_log[i + 1]["messages"].append(
                f"New target compound with target_compound_id: {target_compound.target_compound_id} created"
            )
        elif len(existing_compounds) == 1:
            # use the existing compound record if it does exist
            target_compound_old = existing_compounds[0]
            # Check if CAS number update needed
            if (
                target_compound_old.cas_number is None
                and target_compound.cas_number is not None
            ):
                target_compound_old.cas_number = target_compound.cas_number
                await update_target_compound(
                    [TargetCompoundUpdate(**target_compound_old.to_dict())]
                )
            target_compound = target_compound_old
            target_compound_ids.append(target_compound.target_compound_id)

            message_log[i + 1]["status_code"] = 200
            message_log[i + 1]["messages"].append(
                f"Existing target compound {target_compound.target_compound_name} with target_compound_id: {target_compound.target_compound_id} used"
            )
            continue  # as ions & isotopes are already there in this case
        else:
            # More than one matching compound in the database
            # It is possible to arrive here if there are compound(s) that:
            #   1) Have the same CAS number as the one to be created; AND
            #   2) Another compound that has the same name and formula but not CAS number as the one to be created
            # Let's check to be sure there are no actual duplicates in the database
            target_compound = existing_compounds[0]
            # Convert to dicts
            existing_compounds = [
                existing_compound.to_dict() for existing_compound in existing_compounds
            ]
            # Pop target compound ids for dict comparison afterwards
            _ = [
                existing_compound.pop("target_compound_id")
                for existing_compound in existing_compounds
            ]
            # Check for identical target compounds
            for i, existing_compound in enumerate(existing_compounds[:-1]):
                if any(
                    existing_compound == another_existing_compound
                    for another_existing_compound in existing_compounds[i + 1 :]
                ):
                    # the database is inconsistent with two identical target compounds
                    raise RuntimeError("Duplicate target compound in database")
            # No duplicates, let's proceed
            target_compound_ids.append(target_compound.target_compound_id)
            message_log[i + 1]["status_code"] = 200
            message_log[i + 1]["messages"].append(
                f"Existing target compound {target_compound.target_compound_name} with target_compound_id: {target_compound.target_compound_id} used"
            )
            continue  # as ions & isotopes are already there in this case

        # STEP2: Proceed to creating new target compound record and generating target ions and isotopes for the compound
        try:
            # Try if target compound is given by mass (try to parse composition into float)
            target_compound_mass = float(target_compound.target_compound_formula)
        except ValueError:
            target_compound_mass = None

        # Create target ions for the compound
        # Fetch ionization mechanisms
        ionization_mechanisms_data = await get_ionization_mechanisms()
        ionization_mechanisms = [
            IonizationMechanism(**ionization_mechanism_dict)
            for ionization_mechanism_dict in ionization_mechanisms_data["data"]
        ]

        await create_target_ions(
            target_compound=target_compound,
            ionization_mechanisms=ionization_mechanisms,
            target_compound_mass=target_compound_mass,
            independent_transaction=False,
            session=session,
        )
        # Add the compound to be committed to the db
        session.add(target_compound)

    if independent_transaction:
        await session.commit()
        # STEP 3: Emit global target reload event to inform all clients.
        await sio.emit("targets_all_reload", namespace="/")
    else:
        await session.flush()

    return {
        "target_compound_ids": target_compound_ids,
        "created_compounds": target_compounds_to_create,
        "existing_compounds": existing_target_compounds,
        "message_logs": message_log,
    }


@api_controller()
async def update_target_compound(target_compounds: List[TargetCompoundUpdate]):
    async with async_session() as session:
        not_changed_target_compounds = []
        not_updated_target_compounds = []
        existing_target_compounds = []
        updated_target_compounds = []
        sample_batches_affected_reload = set()
        sample_batches_affected_rematch = set()
        message_log = {}

        # for target_compound in target_compounds:
        for i, target_compound in enumerate(target_compounds):
            # Initialize messages list for this compound
            message_log[i + 1] = {"status_code": 0, "messages": []}

            # Check if target compound exists
            existing_compound = await session.execute(
                select(TargetCompound).where(
                    TargetCompound.target_compound_id
                    == target_compound.target_compound_id
                )
            )
            existing_compound = existing_compound.scalar_one_or_none()

            if not existing_compound:
                message_log[i + 1]["status_code"] = 404
                message_log[i + 1]["messages"].append(
                    f"Target compound not found. ID: {target_compound.target_compound_id}, Name: {target_compound.target_compound_name}"
                )
                continue

            # Check if target compound was edited
            update_data = target_compound.dict(exclude_unset=True)

            if all(
                getattr(existing_compound, key, None) == value
                for key, value in update_data.items()
            ):
                not_changed_target_compounds.append(existing_compound)  # no change
                message_log[i + 1]["status_code"] = 304
                message_log[i + 1]["messages"].append(
                    f"No changes in compound {existing_compound.target_compound_name} detected."
                )
                continue  # Skip this compound update, proceed to the next

            # Check if the compound formula is updated
            if (
                target_compound.target_compound_formula
                and existing_compound.target_compound_formula
                != target_compound.target_compound_formula
            ):
                # Check if the new formula already exists in other TargetCompound records with the same name
                existing_formula_compound = await session.execute(
                    select(TargetCompound).where(
                        and_(
                            func.lower(TargetCompound.target_compound_formula)
                            == norm(
                                target_compound.target_compound_formula, lower=True
                            ),
                            func.lower(TargetCompound.target_compound_name)
                            == norm(target_compound.target_compound_name, lower=True),
                        )
                    )
                )
                existing_formula_compound = (
                    existing_formula_compound.scalar_one_or_none()
                )

                if existing_formula_compound:
                    not_updated_target_compounds.append(target_compound)
                    existing_target_compounds.append(existing_formula_compound)
                    message_log[i + 1]["status_code"] = 409
                    message_log[i + 1]["messages"].append(
                        f"The compound with name {target_compound.target_compound_name} and formula {target_compound.target_compound_formula} is already exists as {existing_formula_compound.target_compound_name} (target_compound_id: {existing_formula_compound.target_compound_id}). Use this compound instead of {target_compound.target_compound_name}"
                    )
                    continue  # Skip this compound update, proceed to the next

                # Get the sample batches affected by the formula changed compond
                (
                    sample_batches_ids,
                    target_collections_ids,
                ) = await get_affected_batches_and_collections(
                    target_compound.target_compound_id
                )

                # If compound formula has changed, delete the compound and recreate it with new formula
                await delete_target_compound(
                    target_compound_id=target_compound.target_compound_id,
                    independent_transaction=False,
                    session=session,
                )

                # Create new compound with updated formula
                new_compound_result = await create_target_compound(
                    target_compounds=[target_compound],
                    independent_transaction=False,
                    session=session,
                )
                if (
                    "created_compounds" in new_compound_result
                    and len(new_compound_result["created_compounds"]) == 1
                ):
                    new_compound = new_compound_result["created_compounds"][0]
                    # Add batches to remath set
                    sample_batches_affected_rematch.update(sample_batches_ids)

                    message_log[i + 1]["status_code"] = 201
                    message_log[i + 1]["messages"].append(
                        "New target compound {} (target_compound_id: {} ) created".format(
                            new_compound.target_compound_name,
                            new_compound.target_compound_id,
                        )
                    )
                elif (
                    "existing_compounds" in new_compound_result
                    and len(new_compound_result["existing_compounds"]) == 1
                ):
                    new_compound = new_compound_result["existing_compounds"][0]
                    # Add batches to remath set
                    sample_batches_affected_rematch.update(sample_batches_ids)

                    message_log[i + 1]["status_code"] = 200
                    message_log[i + 1]["messages"].append(
                        "Existing target compound {} with target_compound_id: {} used".format(
                            new_compound.target_compound_name,
                            new_compound.target_compound_id,
                        )
                    )

                else:
                    raise HTTPException(
                        status_code=500,
                        detail="Error in creating target compound",
                    )

                # Check if the compound already exists in target collections
                existing_target_compound_in_target_collection = await session.execute(
                    select(TargetCompoundInTargetCollection).where(
                        and_(
                            TargetCompoundInTargetCollection.target_compound_id
                            == new_compound.target_compound_id,
                            TargetCompoundInTargetCollection.target_collection_id.in_(
                                target_collections_ids
                            ),
                        )
                    )
                )
                existing_target_compound_in_target_collection = (
                    existing_target_compound_in_target_collection.scalar_one_or_none()
                )

                # Re-add the new compound to target collections if the new compound is not already associated with the target collections
                if not existing_target_compound_in_target_collection:
                    for target_collection_id in target_collections_ids:
                        new_target_compound_in_target_collection = (
                            TargetCompoundInTargetCollection(
                                target_compound_id=new_compound.target_compound_id,
                                target_collection_id=target_collection_id,
                            )
                        )
                        session.add(new_target_compound_in_target_collection)
                updated_target_compounds.append(new_compound)

            else:
                # If compound formula has not changed, just update the fields
                update_data = target_compound.dict(exclude_unset=True)
                for key, value in update_data.items():
                    setattr(existing_compound, key, value)
                updated_target_compounds.append(existing_compound)

                # Get all affected collection and sample batches to reload
                sample_batches_ids, _ = await get_affected_batches_and_collections(
                    target_compound.target_compound_id
                )
                sample_batches_affected_reload.update(sample_batches_ids)

                message_log[i + 1]["status_code"] = 200
                message_log[i + 1]["messages"].append(
                    f"Compound {existing_compound.target_compound_name} updated."
                )

        await session.commit()

        # Rematch the affected sample batches where compound formula was updated
        # for sample_batch_id in sample_batches_affected_rematch:
        #     # FIX replace with request
        #     # TODO_background Use the fastApi background tasks
        #     task = asyncio.create_task(match_batch_compute(None, sample_batch_id))
        #     await task

        # Exclude rematched ids since they've been reloaded
        sample_batches_affected_reload = (
            sample_batches_affected_reload - sample_batches_affected_rematch
        )

        # Reload other affected sample batches
        for sample_batch_id in sample_batches_affected_reload:
            await sio.emit(
                "sample_batch_reload",
                room=sample_batch_id,
                namespace="/",
            )

        return {
            "not_changed_compounds": not_changed_target_compounds,
            "updated_compounds": updated_target_compounds,
            "not_updated_compounds": not_updated_target_compounds,
            "existing_compounds": existing_target_compounds,
            "message_logs": message_log,
        }


@api_controller()
# TODO_error_handling any exceptions would not be returned whdn called from the delete_target_collection, may use the api_controller_background_task
async def delete_target_compound(
    target_compound_id: str, independent_transaction=False, session=None
):
    sample_batches_to_reload = set()

    if independent_transaction:
        session = async_session()

    # Step 1: Fetch the target compound
    target_compound = await session.get(TargetCompound, target_compound_id)
    if not target_compound:
        raise NotFoundException(
            f"Target compound with ID '{target_compound_id}' not found"
        )

    # Fetch the target collections where the deleting compound was present
    result = await session.execute(
        select(TargetCompoundInTargetCollection.target_collection_id).filter(
            TargetCompoundInTargetCollection.target_compound_id == target_compound_id
        )
    )
    target_collections_with_compound = result.scalars().all()

    # Fetch the sample batch ids from TargetCollectionInSampleBatch for these collections
    result = await session.execute(
        select(TargetCollectionInSampleBatch.sample_batch_id).filter(
            TargetCollectionInSampleBatch.target_collection_id.in_(
                target_collections_with_compound
            )
        )
    )
    affected_sample_batches = result.scalars().all()
    sample_batches_to_reload.update(affected_sample_batches)

    # Delete TargetCompound record
    await session.delete(target_compound)

    if independent_transaction:
        await session.commit()
        # Reload affected sample batches
        for sample_batch_id in sample_batches_to_reload:
            await sio.emit(
                "sample_batch_reload",
                room=sample_batch_id,
                namespace="/",
            )
        await sio.emit("targets_all_reload", namespace="/")
    else:
        await session.flush()
