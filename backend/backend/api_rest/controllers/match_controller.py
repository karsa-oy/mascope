import asyncio
import numpy as np
import pandas as pd
from typing import List
from sqlalchemy import select, and_, delete
from sqlalchemy.orm import joinedload
from backend.db_api_rest import async_session
from backend.server import sio
from backend.lib.chemistry import match_mz
from backend.lib.file import load_file
from backend.lib.peak import detect_peaks, get_peaks, read_instrument_functions
from backend.db.id import gen_id
from backend.api_rest.models.models import (
    SampleBatch,
    Sample,
    SampleItem,
    MatchInterference,
    Match,
    TargetCollection,
    TargetCompoundInTargetCollection,
    TargetIon,
    TargetIsotope,
)
from ..models.pydantic_models.sample_batch_pydantic_model import (
    SampleBatchComputeMatch,
    ProgressProperties,
)
from .sample_items_controller import get_sample_items


async def compute_matches(
    filename,
    target_collection_ids,
    ionization_mechanism_ids,
    min_isotope_abundance=0.15,
):
    # Note:
    #   Matching is done on isotope-level. Ion, compound
    #   and collection level matches are aggregated from
    #   isotope-level matches on read; see the frontend
    #   sample store module for this aggregation.

    async with async_session() as session:
        stmt = (
            select(
                TargetIsotope.target_isotope_id,
                TargetIon.target_ion_id,
                TargetIsotope.mz,
                TargetIsotope.relative_abundance,
            )
            .distinct()
            .select_from(TargetCollection)
            .join(
                TargetCompoundInTargetCollection,
                TargetCompoundInTargetCollection.target_collection_id
                == TargetCollection.target_collection_id,
            )
            .join(
                TargetIon,
                TargetIon.target_compound_id
                == TargetCompoundInTargetCollection.target_compound_id,
            )
            .join(TargetIsotope, TargetIsotope.target_ion_id == TargetIon.target_ion_id)
            .where(
                TargetCollection.target_collection_id.in_(target_collection_ids),
                TargetIon.ionization_mechanism_id.in_(ionization_mechanism_ids),
                TargetIsotope.relative_abundance >= min_isotope_abundance,
            )
        )

        result = await session.execute(stmt)
        target_isotope_df = pd.DataFrame(result.fetchall())

    #########################
    # STEP 1 - Load or detect peaks #
    #########################

    # Find peaks and write to file
    u_list = list(np.unique(np.round(target_isotope_df.mz)))
    sample_file = await detect_peaks(filename, u_list, if_exists="append")
    peaks = get_peaks(sample_file, "area")

    #########################
    # STEP 2 - Prepare data #
    #########################

    # init match df from target isotopes
    match_isotope_df = target_isotope_df.copy().assign(
        match_id=np.nan,
        sample_peak_id=np.nan,
        sample_peak_mz=np.nan,
        sample_peak_area=np.nan,
        sample_peak_area_relative=np.nan,
        match_abundance_error=np.nan,
        match_isotope_correlation=np.nan,
        match_mz_error=np.nan,
        match_score=np.nan,
    )

    # parse peak data
    peak_mzs = peaks.mz.values
    peak_areas = peaks.sum(dim="time").values
    peak_tofs = peaks.tof.values
    peak_sorting = np.argsort(peak_mzs)

    #############################
    # STEP 3 - Perform matching #
    #############################

    def match(row):
        # Get all peaks within unit mass window
        mz_tolerance = 0.5
        target_mz = row.mz
        match_indeces, match_mzs = match_mz(
            target_mz, peak_mzs[peak_sorting], tolerance=mz_tolerance
        )
        # Find closest match
        for match_index in match_indeces:
            # get match peak
            peak_index = peak_sorting[match_index]
            peak_mz = peak_mzs[peak_index]
            peak_area = peak_areas[peak_index]
            # check current best match
            best_match = row.sample_peak_id
            if not np.isnan(best_match):
                prev_mz_err = np.abs(row.sample_peak_mz - target_mz)
                new_mz_err = np.abs(peak_mz - target_mz)
                if new_mz_err > prev_mz_err:
                    continue
            # save match
            row["match_id"] = gen_id(length=32)
            row["sample_peak_id"] = peak_index
            row["sample_peak_mz"] = peak_mz
            row["sample_peak_tof"] = peak_tofs[int(peak_index)]
            row["sample_peak_area"] = peak_area
        return row

    match_isotope_df = (
        match_isotope_df.apply(match, axis=1)
        .dropna(subset=["sample_peak_mz"])
        .reset_index()
    )

    ##################################
    # STEP 4 - Calculate match stats #
    ##################################

    # calculate isotope ratios

    # sum matched sample peak heights for each ion
    ion_level_peak_sums = match_isotope_df.groupby(["target_ion_id"], as_index=False)[
        "sample_peak_area"
    ].sum()
    # join sums back to the isotope level
    isotope_level_peak_sums = pd.merge(
        match_isotope_df,
        ion_level_peak_sums.rename(
            columns={"sample_peak_area": "sample_peak_area_sum"}
        ),
        on=["target_ion_id"],
        how="left",
    )

    # compute relative peak heights
    match_isotope_df.loc[:, "sample_peak_area_relative"] = (
        match_isotope_df["sample_peak_area"]
        / isotope_level_peak_sums["sample_peak_area_sum"]
    )
    # calculate isotope ratio errors
    match_isotope_df.loc[:, "match_abundance_error"] = match_isotope_df[
        "relative_abundance"
    ] * (
        match_isotope_df["sample_peak_area_relative"]
        - match_isotope_df["relative_abundance"]
    )
    # calculate isotope correlations
    match_isotope_df = match_isotope_df.groupby(
        ["target_ion_id"], group_keys=False
    ).apply(
        lambda ion_group: (
            ion_group.assign(
                match_isotope_correlation=np.corrcoef(
                    np.array(
                        [
                            peaks.sel(mz=peak_mz, method="nearest")
                            for peak_mz in ion_group["sample_peak_mz"]
                        ]
                    )
                )[0, 1]
                if len(ion_group) > 1
                else 1
            )
        )
    )
    # calculate mz errors
    match_isotope_df.loc[:, "match_mz_error"] = (
        1e6
        * (match_isotope_df["sample_peak_mz"] - match_isotope_df["mz"])
        / match_isotope_df["sample_peak_mz"]
    )

    def score(row):
        row["match_score"] = (1 - abs(row.match_abundance_error)) * max(
            0, (1 - 1e-2 * abs(row.match_mz_error))
        )
        return row

    match_isotope_df = match_isotope_df.apply(score, axis=1, result_type="broadcast")
    return match_isotope_df


async def compute_raw_intensities(
    filename,
    target_collection_ids,
    ionization_mechanism_ids,
):
    # 1. Establish connection and fetch data
    async with async_session() as session:
        stmt = (
            select(
                TargetIsotope.target_isotope_id,
                TargetIon.target_ion_id,
                TargetIsotope.mz,
                TargetIsotope.relative_abundance,
            )
            .distinct()
            .select_from(TargetCollection)
            .join(
                TargetCompoundInTargetCollection,
                TargetCompoundInTargetCollection.target_collection_id
                == TargetCollection.target_collection_id,
            )
            .join(
                TargetIon,
                TargetIon.target_compound_id
                == TargetCompoundInTargetCollection.target_compound_id,
            )
            .join(TargetIsotope, TargetIsotope.target_ion_id == TargetIon.target_ion_id)
            .where(
                and_(
                    TargetCollection.target_collection_id.in_(target_collection_ids),
                    TargetIon.ionization_mechanism_id.in_(ionization_mechanism_ids),
                )
            )
        )

        result = await session.execute(stmt)
        target_isotope_df = pd.DataFrame(result.fetchall())

    # 2. Compute Sum Spectrum from Sample File Data
    sample_file_data = load_file(filename, vars=["signal"])
    sum_spectrum = sample_file_data.signal.sum(dim="time").compute()

    _, R = read_instrument_functions(filename)

    # 3. Compute raw intensities for each target mz
    # init interference df from target isotopes
    isotope_interference_df = target_isotope_df.copy().assign(
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

    isotope_interference_df = isotope_interference_df.apply(calc_raw_intensity, axis=1)

    return isotope_interference_df


async def emit_progress_update(
    progress_properties: ProgressProperties, increment: float
):
    if not progress_properties:
        return

    item_weight = progress_properties.item_weight
    item_index = progress_properties.item_index
    batch_index = progress_properties.batch_index
    total_batches = progress_properties.total_batches
    workspace_id = progress_properties.workspace_id

    # Calculate the progress contribution of completed batches
    batch_progress = ((batch_index - 1) / total_batches) * 100

    # Calculate the progress within the current batch
    item_progress = ((item_index + increment) * item_weight) * 100

    # Calculate the proportional progress of the current batch in terms of the overall progress
    proportional_batch_progress = item_progress * (1 / total_batches)

    # Combine both progresses
    progress_percentage_all = batch_progress + proportional_batch_progress

    await sio.emit(
        "match_batch_compute_progress_percentage",
        {
            "progress_percentage": progress_percentage_all,
            "progress_percentage_batch": proportional_batch_progress * total_batches,
        },
        room=workspace_id,
        namespace="/",
    )


async def item_compute(sample_item, progress_properties: ProgressProperties = None):
    sample_item_id = sample_item.sample_item_id
    filename = sample_item.filename
    sample_batch_id = sample_item.sample_batch_id

    # Step 1: Fetch sample batch and related ion mechanisms and target collection ids
    async with async_session() as session:
        # Get the sample batch and associated target collections
        result = await session.execute(
            select(SampleBatch)
            .options(joinedload(SampleBatch.target_collection))
            .where(SampleBatch.sample_batch_id == sample_batch_id)
        )
        sample_batch = result.unique().scalar_one()

        # Extract ion mechanisms directly
        ionization_mechanism_ids = sample_batch.build_params["ion_mechanisms"]

        # Since we have eager loaded the target_collection, we can fetch them directly from sample_batch
        target_collection_ids = [
            tc.target_collection_id for tc in sample_batch.target_collection
        ]

    await emit_progress_update(progress_properties=progress_properties, increment=0.25)

    # Step 2: Compute Interferences and Matches
    print("Computing interferences for file: %s" % filename)
    match_interference_df = await compute_raw_intensities(
        filename, target_collection_ids, ionization_mechanism_ids
    )
    await emit_progress_update(progress_properties=progress_properties, increment=0.5)

    print("Computing matches for file: %s" % filename)
    match_isotope_df = await compute_matches(
        filename, target_collection_ids, ionization_mechanism_ids
    )
    await emit_progress_update(progress_properties=progress_properties, increment=0.75)

    # Step 3: Check for existing interferences and save them to database
    async with async_session() as session:
        # Extract the required target_isotope_id values
        target_isotope_refs = match_interference_df["target_isotope_id"].tolist()

        # Select interferences that match the criteria
        stmt = select(MatchInterference.match_interference_id).where(
            and_(
                MatchInterference.sample_item_id == sample_item_id,
                MatchInterference.target_isotope_id.in_(target_isotope_refs),
            )
        )

        result = await session.execute(stmt)

        match_interferences = result.all()

        if match_interferences:
            raise RuntimeError("Match interferences exist! Not going to overwrite")

        # Prepare the data for insertion
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

        # Insert the data
        session.add_all(match_interference_for_insertion)

        # Commit the transaction to save the data
        await session.commit()

    # Step 4: Check for existing matches and save them
    if len(match_isotope_df) == 0:
        print("No matches found")
        return sample_item

    async with async_session() as session:
        # Extract the required target_isotope_id values
        target_isotope_refs = match_isotope_df["target_isotope_id"].tolist()

        # Select matches that match the criteria
        stmt = select(Match.match_id).where(
            and_(
                Match.sample_item_id == sample_item_id,
                Match.target_isotope_id.in_(target_isotope_refs),
            )
        )

        result = await session.execute(stmt)

        matches = result.all()

        if matches:
            raise RuntimeError("Matches exist! Not going to overwrite")

        # Prepare the data for insertion
        match_isotope_for_insertion = [
            Match(
                **{
                    key: value
                    for key, value in record.items()
                    if key in Match.__table__.columns
                },
                sample_item_id=sample_item_id,
            )
            for record in match_isotope_df.to_dict(orient="records")
        ]

        # Insert the data
        session.add_all(match_isotope_for_insertion)

        # Commit the transaction to save the data
        await session.commit()

    await emit_progress_update(progress_properties=progress_properties, increment=1)

    return sample_item


async def match_batch_remove(sample_batch_id):
    async with async_session() as session:
        # Get sample items related to the given sample batch
        sample_items = await session.execute(
            select(SampleItem.sample_item_id).where(
                SampleItem.sample_batch_id == sample_batch_id
            )
        )
        sample_item_ids = [sample_item.sample_item_id for sample_item in sample_items]

        # Delete records from match table
        await session.execute(
            delete(Match).where(Match.sample_item_id.in_(sample_item_ids))
        )

        # Delete records from match_interference table
        await session.execute(
            delete(MatchInterference).where(
                MatchInterference.sample_item_id.in_(sample_item_ids)
            )
        )

        await session.commit()


async def match_batch_compute(
    sample_batch_id, progress_properties: ProgressProperties = None
):
    print(f"...Computing matches of batch: {sample_batch_id} ...")

    # clear previous matches
    await match_batch_remove(sample_batch_id)

    async with async_session() as session:
        # Fetch item ids
        result = await session.execute(
            select(SampleItem).where(SampleItem.sample_batch_id == sample_batch_id)
        )

        sample_items = result.scalars().all()

    for item_index, sample_item in enumerate(sample_items):
        try:
            print(
                f"...Computing matches of sample item: {sample_item.sample_item_id} ..."
            )
            progress_properties = ProgressProperties(
                item_weight=progress_properties.item_weight,
                item_index=item_index,
                batch_index=progress_properties.batch_index,
                workspace_id=progress_properties.workspace_id,
                total_batches=progress_properties.total_batches,
            )

            await item_compute(sample_item, progress_properties=progress_properties)
        except Exception as e:
            print(f"Processing sample {sample_item} failed: {e}")

    # reload batch
    await sio.emit("sample_batch_reload", room=sample_batch_id, namespace="/")


async def match_batches_compute(sample_batches: List[SampleBatchComputeMatch]):
    total_batches = len(sample_batches)
    total_number_of_items = 0
    items_per_batch = []
    workspace_ids = set()

    # Step 1: Gather data for each batch and set workspace_ids
    async with async_session() as session:
        for sample_batch in sample_batches:
            sample_items_info = await get_sample_items(
                sample_batch_id=sample_batch.sample_batch_id
            )
            total_number_of_items += sample_items_info["results"]
            items_per_batch.append(sample_items_info["results"])

            # If workspace_id is not provided, fetch it from the database
            if not sample_batch.workspace_id:
                result = await session.execute(
                    select(SampleBatch.workspace_id).filter(
                        SampleBatch.sample_batch_id == sample_batch.sample_batch_id
                    )
                )
                sample_batch.workspace_id = result.scalar_one_or_none()

            workspace_ids.add(sample_batch.workspace_id)

    # Calculate weight for each batch based on the number of items
    item_weights_per_batch = [1.0 / items if items else 0 for items in items_per_batch]

    # Step 2: Notify workspace clients that batch processing has started
    for workspace_id in workspace_ids:
        await sio.emit(
            "match_batch_compute_started",
            {"total_batches": total_batches},
            room=workspace_id,
            namespace="/",
        )

    # Step 3: Process each batch
    for batch_index, sample_batch in enumerate(sample_batches, start=1):
        # Notify workspace clients of the progres
        await sio.emit(
            "match_batch_compute_progress",
            {"current_batch": batch_index},
            room=sample_batch.workspace_id,
            namespace="/",
        )
        # Notify sample batch clients of the selected batch processing
        await sio.emit(
            "match_batch_compute_progress",
            {"current_batch_message": "Selected batch is processing now"},
            room=sample_batch.sample_batch_id,
            namespace="/",
        )

        # Compute progress properties for the current batch
        progress_properties = ProgressProperties(
            item_weight=item_weights_per_batch[batch_index - 1],
            batch_index=batch_index,
            workspace_id=sample_batch.workspace_id,
            total_batches=total_batches,
        )

        # Create computing matches task for the batch
        task = asyncio.create_task(
            match_batch_compute(
                sample_batch.sample_batch_id, progress_properties=progress_properties
            )
        )
        await task

    # Step 4: Notify workspace clients that batch processing has finished
    for workspace_id in workspace_ids:
        await sio.emit(
            "match_batch_compute_finished",
            {"total_batches": total_batches},
            room=workspace_id,
            namespace="/",
        )

    return {"status": f"Match computation for {total_batches} batches"}
