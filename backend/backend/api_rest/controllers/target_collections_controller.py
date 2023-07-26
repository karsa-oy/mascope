import pandas as pd

from backend.server import sio
from backend.db.id import gen_id

from fastapi import HTTPException
from sqlalchemy import asc, desc, func, select

from backend.db_api_rest import async_session
from .target_compounds_controller import delete_target_compound, create_target_compound
from ..models.models import (
    TargetCollection,
    TargetCompoundInTargetCollection,
    TargetCollectionInSampleBatch,
)
from ..models.pydantic_models.target_collection_pydantic_model import (
    TargetCollectionCreate,
)


async def get_target_collections(sort: str, order: str, page: int, limit: int):
    async with async_session() as session:
        stmt = select(TargetCollection)

        if sort:
            if order == "desc":
                stmt = stmt.order_by(desc(getattr(TargetCollection, sort)))
            else:
                stmt = stmt.order_by(asc(getattr(TargetCollection, sort)))

        # Get total count
        count_stmt = select(func.count()).select_from(stmt)
        total = await session.scalar(count_stmt)

        # Get paginated results
        stmt = stmt.offset(page * limit).limit(limit)
        result = await session.execute(stmt)
        target_collections = result.scalars().all()

        return {
            "results": total,
            "data": [
                target_collection.to_dict() for target_collection in target_collections
            ],
        }


async def get_target_collection_by_id(target_collection_id: str):
    async with async_session() as session:
        stmt = select(TargetCollection).filter(
            TargetCollection.target_collection_id == target_collection_id
        )
        result = await session.execute(stmt)
        target_collection = result.scalars().first()

        if not target_collection:
            raise HTTPException(
                status_code=404,
                detail=f"TargetCollection with ID {target_collection_id} not found",
            )

        return target_collection.to_dict()


async def create_target_collection(target_collection: TargetCollectionCreate):
    async with async_session() as session:
        new_target_collection = TargetCollection(
            target_collection_id=gen_id(16),
            target_collection_name=target_collection.target_collection_name,
            target_collection_description=target_collection.target_collection_description,
        )
        session.add(new_target_collection)

        # Create the target compounds
        target_compound_ids = await create_target_compound(
            target_collection.target_compounds
        )

        # Add the target compounds to the target collection
        for target_compound_id in target_compound_ids:
            new_target_compound_in_target_collection = TargetCompoundInTargetCollection(
                target_compound_id=target_compound_id,
                target_collection_id=new_target_collection.target_collection_id,
            )
            session.add(new_target_compound_in_target_collection)

        # Add the target collection to the sample batches
        if target_collection.sample_batches is not None:
            for sample_batch_id in target_collection.sample_batches:
                new_target_collection_in_sample_batch = TargetCollectionInSampleBatch(
                    target_collection_id=new_target_collection.target_collection_id,
                    sample_batch_id=sample_batch_id,
                )
                session.add(new_target_collection_in_sample_batch)

        # Add the new target collection to the session and commit
        await session.commit()
        await session.refresh(new_target_collection)
        await sio.emit("org_reload", namespace="/")

        return new_target_collection


async def delete_target_collection(target_collection_id: str):
    async with async_session() as session:
        # Check if the target collection exists
        result = await session.execute(
            select(TargetCollection).filter(
                TargetCollection.target_collection_id == target_collection_id
            )
        )
        target_collection = result.scalar_one_or_none()

        if not target_collection:
            raise HTTPException(status_code=404, detail="Target collection not found")

        # Check if the compound is present in other collections
        compounds_in_collection = await session.execute(
            select(TargetCompoundInTargetCollection).filter(
                TargetCompoundInTargetCollection.target_collection_id
                == target_collection_id
            )
        )

        for compound in compounds_in_collection.scalars():
            other_collections_with_compound = await session.execute(
                select(TargetCompoundInTargetCollection).filter(
                    TargetCompoundInTargetCollection.target_compound_id
                    == compound.target_compound_id,
                    TargetCompoundInTargetCollection.target_collection_id
                    != target_collection_id,
                )
            )

            # If the compound is not in other collections, delete it
            if other_collections_with_compound.first() is None:
                await delete_target_compound(compound.target_compound_id)

        # Delete the target collection
        await session.delete(target_collection)
        await session.commit()
        await sio.emit("org_reload", namespace="/")
        await sio.emit(
            "sample_batch_reload",
            # room=db_sample_item.sample_batch_id,
            namespace="/",
        )
