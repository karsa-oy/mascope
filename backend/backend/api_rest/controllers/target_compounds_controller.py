from fastapi import HTTPException
from sqlalchemy import asc, desc, func, select, or_, and_
from typing import List, Optional

from backend.server import sio
from backend.db.id import gen_id
from lib.molmass import Formula
from backend.db_api_rest import async_session

from .ionization_mechanisms_controller import get_ionization_mechanisms
from .helpers_controller import get_affected_batches_and_collections
from ..models.models import (
    TargetCompound,
    TargetIon,
    TargetIsotope,
    TargetCompoundInTargetCollection,
    TargetCollectionInSampleBatch,
)
from ..models.pydantic_models.target_compound_pydantic_model import (
    TargetCompoundBase,
    TargetCompoundUpdate,
)


async def get_target_compounds(
    target_compound_name: Optional[str] = None,
    target_compound_formula: Optional[str] = None,
    sample_batch_id: Optional[str] = None,
    sort: str = None,
    order: str = None,
    page: int = 0,
    limit: int = 1000000,
):
    async with async_session() as session:
        stmt = select(TargetCompound)

        if target_compound_name:
            stmt = stmt.filter(
                TargetCompound.target_compound_name == target_compound_name
            )

        if target_compound_formula:
            stmt = stmt.filter(
                TargetCompound.target_compound_formula == target_compound_formula
            )
        if sample_batch_id:
            stmt = (
                stmt.join(
                    TargetCompoundInTargetCollection,
                    TargetCompoundInTargetCollection.target_compound_id
                    == TargetCompound.target_compound_id,
                )
                .join(
                    TargetCollectionInSampleBatch,
                    TargetCollectionInSampleBatch.target_collection_id
                    == TargetCompoundInTargetCollection.target_collection_id,
                )
                .filter(
                    TargetCollectionInSampleBatch.sample_batch_id == sample_batch_id
                )
                .distinct()
            )

        if sort:
            if order == "desc":
                stmt = stmt.order_by(desc(getattr(TargetCompound, sort)))
            else:
                stmt = stmt.order_by(asc(getattr(TargetCompound, sort)))

        # Get total count
        count_stmt = select(func.count()).select_from(stmt)
        total = await session.scalar(count_stmt)

        # Get paginated results
        stmt = stmt.offset(page * limit).limit(limit)
        result = await session.execute(stmt)
        target_compounds = result.scalars().all()

        return {
            "results": total,
            "data": [target_compound.to_dict() for target_compound in target_compounds],
        }


async def get_target_compound_by_id(target_compound_id: str):
    async with async_session() as session:
        stmt = select(TargetCompound).filter(
            TargetCompound.target_compound_id == target_compound_id
        )
        result = await session.execute(stmt)
        target_compound = result.scalars().first()

        if not target_compound:
            raise HTTPException(
                status_code=404,
                detail=f"TargetCompound with ID {target_compound_id} not found",
            )

        return target_compound.to_dict()


async def delete_target_compound(target_compound_id: str, session=None):
    independent_transaction = False
    sample_batches_to_reload = set()

    if session is None:
        independent_transaction = True
        session = async_session()

    # Check if target compound exists
    result = await session.execute(
        select(TargetCompound).filter(
            TargetCompound.target_compound_id == target_compound_id
        )
    )
    target_compound = result.scalar_one_or_none()
    if not target_compound:
        raise HTTPException(status_code=404, detail="Target compound not found")

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
    else:
        await session.flush()


async def create_target_compound(
    target_compounds: List[TargetCompoundBase], session=None
):
    independent_transaction = False

    if session is None:
        independent_transaction = True
        session = async_session()

    # helper functions
    def norm(name, lower=False):
        if lower:
            name = name.lower()
        return " ".join(name.strip().split())

    def charge_string(raw_ion):
        if raw_ion.charge == -1:
            charge_string = "-"
        elif raw_ion.charge == +1:
            charge_string = "+"
        else:
            charge_string = ""
        return charge_string

    def generate_target_ions_from_composition():
        # generate and create ion records
        for ionization_mechanism in ionization_mechanisms:
            mechanism = ionization_mechanism["ionization_mechanism"]
            try:
                # get and save ions
                raw_ion = Formula(
                    "("
                    + target_compound.target_compound_formula.rstrip()
                    + mechanism[:-1]
                    + ")"
                    + mechanism[-1]
                )
            except ValueError as e:
                print("Failed to parse ion formula: %s" % e)
            else:
                # construct and save ion row
                ion = TargetIon(
                    target_ion_id=gen_id(),
                    target_compound_id=target_compound.target_compound_id,
                    ionization_mechanism_id=ionization_mechanism[
                        "ionization_mechanism_id"
                    ],
                    target_ion_formula=raw_ion.formula + charge_string(raw_ion),
                    filter_params={},
                )

                nonlocal target_ions
                target_ions.append(ion)

                # construct and save isotope rows
                raw_isotopes = raw_ion.mz_spectrum().values()
                nonlocal target_isotopes
                target_isotopes += [
                    TargetIsotope(
                        target_isotope_id=gen_id(),
                        target_ion_id=ion.target_ion_id,
                        mz=mz,
                        relative_abundance=rel_abu,
                    )
                    for [mz, rel_abu] in raw_isotopes
                ]

    def generate_target_ions_from_mass(target_compound_mass):
        # generate and create ion records
        for ionization_mechanism in ionization_mechanisms:
            mechanism = ionization_mechanism["ionization_mechanism"]
            # construct and save ion row
            ion = TargetIon(
                target_ion_id=gen_id(),
                target_compound_id=target_compound.target_compound_id,
                ionization_mechanism_id=ionization_mechanism["ionization_mechanism_id"],
                target_ion_formula=(f"{target_compound_mass:.4f}" + mechanism),
                filter_params={},
            )

            nonlocal target_ions
            target_ions.append(ion)
            # construct and save isotope rows
            raw_ion = Formula("(" + mechanism[1:-1] + ")" + mechanism[-1])
            is_adduct = mechanism[0] == "+"
            if is_adduct:
                raw_isotopes = raw_ion.mz_spectrum().values()
            else:
                raw_isotopes = [(-raw_ion.mz, 1.0)]
            nonlocal target_isotopes
            target_isotopes += [
                TargetIsotope(
                    target_isotope_id=gen_id(),
                    target_ion_id=ion.target_ion_id,
                    mz=(target_compound_mass + reagent_mz),
                    relative_abundance=reagent_rel_abu,
                )
                for [reagent_mz, reagent_rel_abu] in raw_isotopes
            ]

    # Fetch ionization mechanisms
    ionization_mechanisms_data = await get_ionization_mechanisms()
    ionization_mechanisms = ionization_mechanisms_data["data"]

    # initialize list of targets to return
    target_compound_ids = []
    existing_target_compounds = []
    # initalized lists of targets to create
    target_compounds_to_create = []
    target_ions = []
    target_isotopes = []
    # Initialize message log
    message_log = {}

    for i, target_compound in enumerate(target_compounds):
        # Initialize messages list
        message_log[i + 1] = {
            "status_code": 0,
            "messages": [],
        }
        # check if the compound record is already in the database
        existing_compounds = await session.execute(
            select(TargetCompound).filter(
                or_(
                    func.lower(TargetCompound.target_compound_formula)
                    == norm(target_compound.target_compound_formula, lower=True),
                    TargetCompound.target_compound_formula
                    == norm(target_compound.target_compound_formula, lower=True),
                )
            )
        )
        existing_compounds = existing_compounds.scalars().all()

        if len(existing_compounds) == 0:
            # save the new compound for creation if it doesn't exist
            target_compound = TargetCompound(
                target_compound_id=gen_id(),
                target_compound_name=target_compound.target_compound_name,
                target_compound_formula=norm(target_compound.target_compound_formula),
                cas_number=target_compound.cas_number,
            )

            target_compounds_to_create.append(target_compound)
            target_compound_ids.append(target_compound.target_compound_id)

            message_log[i + 1]["status_code"] = 201
            message_log[i + 1]["messages"].append(
                "New target compound with target_compound_id: {} created".format(
                    target_compound.target_compound_id
                )
            )
        elif len(existing_compounds) == 1:
            # use the existing compound record if it does exist
            target_compound = existing_compounds[0]
            existing_target_compounds.append(target_compound)
            target_compound_ids.append(target_compound.target_compound_id)

            message_log[i + 1]["status_code"] = 200
            message_log[i + 1]["messages"].append(
                "Existing target compound {} with target_compound_id: {} used".format(
                    target_compound.target_compound_name,
                    target_compound.target_compound_id,
                )
            )
            continue  # as ions & isotopes are already there in this case
        else:
            # the database is inconsistent
            raise RuntimeError("Duplicate target compound in database")

        try:
            # Target compound given by mass
            target_compound_mass = float(target_compound.target_compound_formula)
            generate_target_ions_from_mass(target_compound_mass)
        except ValueError:
            # Target compound given by composition
            generate_target_ions_from_composition()

    # Add the targets to the database and commit
    for target_compound in target_compounds_to_create:
        session.add(target_compound)
    for target_ion in target_ions:
        session.add(target_ion)
    for target_isotope in target_isotopes:
        session.add(target_isotope)

    if independent_transaction:
        await session.commit()
    else:
        await session.flush()

    return {
        "target_compound_ids": target_compound_ids,
        "created_compounds": target_compounds_to_create,
        "existing_compounds": existing_target_compounds,
        "message_logs": message_log,
    }


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
                # Check if the new formula already exists in other TargetCompound records
                existing_formula_compound = await session.execute(
                    select(TargetCompound).where(
                        TargetCompound.target_compound_formula
                        == target_compound.target_compound_formula
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
                        f"The compound with formula ({target_compound.target_compound_formula}) is already exists as {existing_formula_compound.target_compound_name} (target_compound_id: {existing_formula_compound.target_compound_id}). Use this compound instead of {target_compound.target_compound_name}"
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
                    target_compound.target_compound_id, session
                )

                # Create new compound with updated formula
                new_compound_result = await create_target_compound(
                    [target_compound], session
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
