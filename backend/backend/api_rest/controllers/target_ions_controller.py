from fastapi import HTTPException
from sqlalchemy import asc, desc, func, select

from backend.db_api_rest import async_session
from backend.server import sio
from ..models.models import (
    TargetIon,
    TargetCompound,
    TargetCollection,
    TargetCompoundInTargetCollection,
    TargetCollectionInSampleBatch,
    SampleBatch,
    Sample,
)
from ..models.pydantic_models.target_ion_pydantic_model import TargetIonUpdate


async def get_target_ions(
    target_compound_id: str,
    ionization_mechanism_id: str,
    target_ion_formula: str,
    sort: str,
    order: str,
    page: int,
    limit: int,
):
    async with async_session() as session:
        stmt = select(TargetIon)

        if target_compound_id:
            stmt = stmt.filter(TargetIon.target_compound_id == target_compound_id)

        if ionization_mechanism_id:
            stmt = stmt.filter(
                TargetIon.ionization_mechanism_id == ionization_mechanism_id
            )

        if target_ion_formula:
            stmt = stmt.filter(TargetIon.target_ion_formula == target_ion_formula)

        if sort:
            if order == "desc":
                stmt = stmt.order_by(desc(getattr(TargetIon, sort)))
            else:
                stmt = stmt.order_by(asc(getattr(TargetIon, sort)))

        # Get total count
        count_stmt = select(func.count()).select_from(stmt)
        total = await session.scalar(count_stmt)

        # Get paginated results
        stmt = stmt.offset(page * limit).limit(limit)
        result = await session.execute(stmt)
        target_ions = result.scalars().all()

        return {
            "results": total,
            "data": [target_ion.to_dict() for target_ion in target_ions],
        }


async def get_target_ion(target_ion_id: str):
    async with async_session() as session:
        stmt = select(TargetIon)

        if target_ion_id:
            stmt = stmt.filter(TargetIon.target_ion_id == target_ion_id)

        result = await session.execute(stmt)
        target_ion = result.scalars().first()

        if not target_ion:
            raise HTTPException(status_code=404, detail=f"Target ion not found")

        return target_ion.to_dict()


async def update_target_ion(target_ion_id: str, target_ion_update: TargetIonUpdate):
    async with async_session() as session:
        target_ion = await session.get(TargetIon, target_ion_id)
        if not target_ion:
            raise HTTPException(
                status_code=404,
                detail=f"Target ion with ID {target_ion_id} not found",
            )

        existing_filter_params = target_ion.filter_params or {}

        # Create a new dictionary for updated filter_params
        new_filter_params = existing_filter_params.copy()
        affected_instruments = set()

        # Handle deletion of filter parameters for a specific instrument
        if target_ion_update.delete_instrument_filters:
            instrument_to_delete = target_ion_update.delete_instrument_filters
            if instrument_to_delete in new_filter_params:
                del new_filter_params[instrument_to_delete]
                target_ion.filter_params = new_filter_params
                affected_instruments.add(instrument_to_delete)

        # Handle updating filter parameters
        else:
            updated_filter_params = target_ion_update.filter_params
            for instrument, update_params in updated_filter_params.items():
                update_params_dict = update_params.dict()
                # Check for changes in filter_params
                if (
                    instrument not in existing_filter_params
                    or existing_filter_params[instrument] != update_params_dict
                ):
                    new_filter_params[instrument] = update_params_dict
                    affected_instruments.add(instrument)

                    # Assign the new dictionary to target_ion.filter_params
                    target_ion.filter_params = new_filter_params

        # Commit and refresh if there are any changes
        if affected_instruments:
            await session.commit()
            await session.refresh(target_ion)

            # Find and notify affected sample batches
            for instrument in affected_instruments:
                stmt = (
                    select(SampleBatch.sample_batch_id)
                    .join(Sample)
                    .join(TargetCollectionInSampleBatch)
                    .join(TargetCollection)
                    .join(TargetCompoundInTargetCollection)
                    .join(TargetCompound)
                    .join(TargetIon)
                    .where(TargetIon.target_ion_id == target_ion_id)
                    # Filter sample batches by instrument
                    .where(Sample.instrument == instrument)
                    .distinct()
                )
                result = await session.execute(stmt)
                affected_batches = result.fetchall()
                affected_batch_ids = [
                    batch.sample_batch_id for batch in affected_batches
                ]

                # Emit signal for affected sample batches
                for sample_batch_id in affected_batch_ids:
                    await sio.emit(
                        "sample_batch_reload",
                        room=sample_batch_id,
                        namespace="/",
                    )

        return target_ion.to_dict()
