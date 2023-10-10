import pandas as pd
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy import (
    asc,
    desc,
    and_,
    select,
    func,
    case,
    cast,
    Float,
    literal,
)
from typing import List

from backend.db_api_rest import async_session

from ..models.models import (
    Sample,
    Match,
    TargetCompound,
    TargetIon,
    IonizationMechanism,
    TargetIsotope,
    MatchInterference,
    TargetCompoundInTargetCollection,
    TargetCollection,
    TargetCollectionInSampleBatch,
)

from ..models.pydantic_models.sample_pydantic_model import FilterParams


async def get_samples(
    sample_item_id: str = None,
    sample_item_id_active: str = None,
    sample_file_id: str = None,
    sample_batch_id: str = None,
    filename: str = None,
    instrument: str = None,
    sample_item_type: str = None,
    minDatetime: datetime = None,
    maxDatetime: datetime = None,
    sort: str = "datetime_utc",
    order: str = None,
    filter_params: FilterParams = None,
    page: int = 0,
    limit: int = 10000,
    batch_matches_info: bool = False,
):
    async with async_session() as session:
        stmt = select(Sample)

        # filters
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

        if minDatetime and maxDatetime:
            stmt = stmt.where(
                and_(
                    cast(func.julianday(Sample.datetime_utc), Float)
                    >= func.julianday(minDatetime),
                    cast(func.julianday(Sample.datetime_utc), Float)
                    <= func.julianday(maxDatetime),
                )
            )

        if sort:
            if order == "desc":
                stmt = stmt.order_by(desc(getattr(Sample, sort)))
            else:
                stmt = stmt.order_by(asc(getattr(Sample, sort)))

        # Get total count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await session.scalar(count_stmt)

        # Get paginated results
        stmt = stmt.offset(page * limit).limit(limit)

        result = await session.execute(stmt)
        samples = result.scalars().all()

        # Convert samples into dataframe
        samples_df = pd.DataFrame([sample.to_dict() for sample in samples])

        #  Add 'selection' field
        if sample_item_id_active is not None:
            samples_df["selection"] = samples_df["sample_item_id"].apply(
                lambda x: 3 if x == sample_item_id_active else 0
            )
        else:
            samples_df["selection"] = 0

        if sample_batch_id and filter_params:
            # Calculate and add fields match_score, sample_peak_area_sum, sample_peak_interference_sum, matched
            batch_match_filter_result = await init_batch_match_filter(
                sample_batch_id, filter_params
            )

            # Convert the result to a dataframe
            batch_match_filter_dict = batch_match_filter_result["data"]
            message = batch_match_filter_result["message"]
            batch_match_filter_df = pd.DataFrame(batch_match_filter_dict)

            # Calculate matchIsotopes, matchIons, matchCompounds, matchCollections

            # If batch_match_filter_df is empty, assign None to relevant fields and continue
            if batch_match_filter_df.empty:
                samples_df[
                    [
                        "match_score",
                        "sample_peak_area_sum",
                        "sample_peak_interference_sum",
                        "matched",
                    ]
                ] = (
                    None,
                    None,
                    None,
                    0,
                )
                result_dict = {
                    "results": total,
                    "data": samples_df.to_dict("records"),
                    "message": message,
                }
                return result_dict

            # 1) Aggregate fields for matchIons
            match_ions_df = (
                batch_match_filter_df.groupby(
                    [
                        "filename",
                        "sample_item_id",
                        "sample_item_name",
                        "sample_item_type",
                        "target_compound_formula",
                        "target_compound_id",
                        "target_compound_name",
                        "target_ion_formula",
                        "target_ion_id",
                        "target_ion_mechanism",
                    ]
                )
                .agg(
                    {
                        "match_score": lambda x: (
                            x * batch_match_filter_df.loc[x.index, "relative_abundance"]
                        ).sum(),
                        "sample_peak_area": "sum",
                        "sample_peak_interference": "sum",
                    }
                )
                .reset_index()
                .rename(
                    columns={
                        "sample_peak_area": "sample_peak_area_sum",
                        "sample_peak_interference": "sample_peak_interference_sum",
                    }
                )
            )

            # 2) Aggregate fields for matchCompounds
            match_compounds_df = (
                match_ions_df.groupby(
                    [
                        "filename",
                        "sample_item_id",
                        "sample_item_name",
                        "sample_item_type",
                        "target_compound_formula",
                        "target_compound_id",
                        "target_compound_name",
                    ]
                )
                .agg(
                    {
                        "match_score": "max",
                        "sample_peak_area_sum": "sum",
                        "sample_peak_interference_sum": "max",
                    }
                )
                .reset_index()
                .rename(
                    columns={
                        "sample_peak_interference_sum": "sample_peak_interference_max",
                    }
                )
            )

            # Create a copy of match_compounds_df
            match_compounds_df_copy = match_compounds_df.copy()

            # Preserving the sample_peak_interference_sum of ion lvl sum of the row with max match_score
            max_match_score_idx = match_compounds_df_copy.groupby(["sample_item_id"])[
                "match_score"
            ].idxmax()

            match_compounds_df_copy[
                "sample_peak_interference_max_in_max_match_score"
            ] = match_compounds_df_copy.loc[
                max_match_score_idx, "sample_peak_interference_max"
            ]

            # 3)  Aggregate fields for matchSamples
            match_samples_df = (
                match_compounds_df_copy.groupby(
                    [
                        "filename",
                        "sample_item_id",
                        "sample_item_name",
                    ]
                )
                .agg(
                    {
                        "match_score": "max",
                        "sample_peak_area_sum": "sum",
                        "sample_peak_interference_max_in_max_match_score": "first",
                    }
                )
                .reset_index()
                .rename(
                    columns={
                        "sample_peak_interference_max_in_max_match_score": "sample_peak_interference_sum"
                    }
                )
            )

            # Select relevant columns from match_samples_df
            match_samples_df_short = match_samples_df[
                [
                    "sample_item_id",
                    "match_score",
                    "sample_peak_area_sum",
                    "sample_peak_interference_sum",
                ]
            ]

            # Merge with samples_df
            samples_df = pd.merge(
                samples_df, match_samples_df_short, how="left", on="sample_item_id"
            )

            # Add matched column
            samples_df["matched"] = samples_df["match_score"].apply(
                lambda x: 0 if pd.isna(x) else 1
            )

            # Replace NaNs with 0
            samples_df[
                [
                    "match_score",
                    "sample_peak_area_sum",
                    "sample_peak_interference_sum",
                ]
            ] = samples_df[
                [
                    "match_score",
                    "sample_peak_area_sum",
                    "sample_peak_interference_sum",
                ]
            ].fillna(
                0
            )

        result_dict = {
            "results": total,
            "data": samples_df.to_dict("records"),
            "message": message,
        }
        # If batch_matches_info is true, calculate matches and add match dataframes to the result
        if batch_matches_info and sample_batch_id and filter_params:
            result_dict["batch_matches_info"] = {
                "matches": {
                    # "match_isotopes": len(match_isotopes_df),
                    "match_ions": len(match_ions_df),
                    "match_compounds": len(match_compounds_df),
                    "match_samples": len(match_samples_df),
                },
                "match_samples": match_samples_df.sort_values(
                    by="match_score", ascending=False
                ).to_dict("records"),
                "match_compounds": match_compounds_df.sort_values(
                    by="match_score", ascending=False
                ).to_dict("records"),
                "match_ions": match_ions_df.sort_values(
                    by="match_score", ascending=False
                ).to_dict("records"),
            }

        return result_dict


async def get_sample_by_id(sample_item_id: str, filter_params: FilterParams):
    async with async_session() as session:
        stmt = select(Sample).filter(Sample.sample_item_id == sample_item_id)
        result = await session.execute(stmt)
        sample = result.scalars().first()

        if not sample:
            raise HTTPException(
                status_code=404,
                detail=f"Sample with ID {sample_item_id} not found",
            )

        # Calculate matchIsotopes, matchIons, matchCompounds, matchCollections

        sample_match_filter_result = await init_sample_match_filter(
            sample.sample_batch_id, sample.sample_item_id, filter_params
        )

        # Convert the result to a dataframe
        sample_match_filter_dict = sample_match_filter_result["data"]
        message = sample_match_filter_result["message"]
        sample_match_filter_df = pd.DataFrame(sample_match_filter_dict)

        # If sample_match_filter_df is empty, return the sample dictionary with empty fields
        if sample_match_filter_df.empty:
            sample_dict = sample.to_dict()
            sample_dict.update(
                {
                    "match_score": 0,
                    "sample_peak_area_sum": 0,
                    "sample_peak_interference_sum": 0,
                    "matched": 0,
                    "selection": 3,
                    "matchCollections": [],
                    "matchCompounds": [],
                    "matchIons": [],
                    "matchIsotopes": [],
                }
            )
            return {
                "data": sample_dict,
                "message": message,
            }

        # Aggregate fields for matchIsotopes
        match_isotopes_df = sample_match_filter_df.loc[
            :,
            [
                "match_score",
                "match_mz_error",
                "match_abundance_error",
                "match_isotope_correlation",
                "mz",
                "relative_abundance",
                "sample_item_id",
                "sample_peak_area",
                "sample_peak_area_relative",
                "sample_peak_mz",
                "sample_peak_tof",
                "sample_peak_interference",
                "target_isotope_id",
                "target_ion_id",
                "target_ion_formula",
                "target_compound_id",
                "target_collection_id",
                "target_collection_name",
                "target_collection_description",
                "target_compound_name",
                "target_compound_formula",
            ],
        ]

        # Drop duplicates for matchIsotopes based on target_isotope_id
        match_isotopes_unique_df = match_isotopes_df.drop_duplicates(
            subset="target_isotope_id"
        )

        # Aggregate fields for matchIons
        match_ions_df = (
            match_isotopes_df.groupby(
                [
                    "sample_item_id",
                    "target_ion_formula",
                    "target_compound_formula",
                    "target_compound_name",
                    "target_ion_id",
                    "target_compound_id",
                    "target_collection_id",
                    "target_collection_name",
                    "target_collection_description",
                ]
            )
            .agg(
                {
                    "match_score": lambda x: (
                        x * match_isotopes_df.loc[x.index, "relative_abundance"]
                    ).sum(),
                    "sample_peak_area": "sum",
                    "sample_peak_interference": "sum",
                }
            )
            .reset_index()
            .rename(
                columns={
                    "sample_peak_area": "sample_peak_area_sum",
                    "sample_peak_interference": "sample_peak_interference_sum",
                }
            )
        )

        # Drop duplicates for matchIons based on target_ion_id
        match_ions_unique_df = match_ions_df.drop_duplicates(subset="target_ion_id")
        # Aggregate fields for matchCompounds
        match_compounds_df = (
            match_ions_df.groupby(
                [
                    "sample_item_id",
                    "target_compound_id",
                    "target_compound_formula",
                    "target_compound_name",
                    "target_collection_id",
                    "target_collection_name",
                    "target_collection_description",
                ]
            )
            .agg(
                {
                    "match_score": "max",
                    "sample_peak_area_sum": "sum",
                    "sample_peak_interference_sum": "max",
                }
            )
            .reset_index()
            .rename(
                columns={
                    "sample_peak_interference_sum": "sample_peak_interference_max",
                }
            )
        )

        # Aggregate fields for matchCollections
        match_collections_df = (
            match_compounds_df.groupby(
                [
                    "sample_item_id",
                    "target_collection_id",
                    "target_collection_name",
                    "target_collection_description",
                ]
            )
            .agg(
                {
                    "match_score": "max",
                    "sample_peak_area_sum": "sum",
                    "sample_peak_interference_max": "max",
                }
            )
            .reset_index()
        )

        # Calculate and add fields match_score, sample_peak_area_sum, sample_peak_interference_sum, matched, selection

        # Convert sample into dataframe
        sample_df = pd.DataFrame([sample.to_dict()])

        # Get the index of the row with the maximum match_score
        max_score_index = match_compounds_df["match_score"].idxmax()

        # Add the calculated fields to the sample dataframe
        sample_df["match_score"] = match_compounds_df.loc[
            max_score_index, "match_score"
        ]
        sample_df["sample_peak_area_sum"] = match_compounds_df.loc[
            max_score_index, "sample_peak_area_sum"
        ]
        sample_df["sample_peak_interference_sum"] = match_compounds_df.loc[
            max_score_index, "sample_peak_interference_max"
        ]

        # Calculate the matched field
        sample_df["matched"] = int(
            sample_match_filter_df["sample_item_id"].eq(sample_item_id).any()
        )

        # Add the selection field
        sample_df["selection"] = 3

        sample_dict = sample_df.to_dict(orient="records")[0]

        # Add the matches field as a dictionary
        matches = {
            "matches": {
                "match_isotopes": len(match_isotopes_unique_df),
                "match_ions": len(match_ions_unique_df),
                "match_compounds": len(match_compounds_df),
                "match_collections": len(match_collections_df),
            }
        }

        sample_dict.update(matches)

        # Add the aggregated dataframes to the sample dictionary
        sample_dict["match_collections"] = match_collections_df.sort_values(
            by="match_score", ascending=False
        ).to_dict("records")
        sample_dict["match_compounds"] = match_compounds_df.sort_values(
            by="match_score", ascending=False
        ).to_dict("records")
        sample_dict["match_ions"] = match_ions_unique_df.sort_values(
            by="match_score", ascending=False
        ).to_dict("records")
        sample_dict["match_isotopes"] = match_isotopes_unique_df.sort_values(
            by="match_score", ascending=False
        ).to_dict("records")

        return {
            "data": sample_dict,
            "message": message,
        }


async def init_batch_match_filter(batch_id: str, filter_params: FilterParams):
    mz_tolerance = filter_params.mz_tolerance
    isotope_ratio_tolerance = filter_params.isotope_ratio_tolerance
    peak_min_intensity = filter_params.peak_min_intensity
    min_isotope_abundance = filter_params.min_isotope_abundance
    min_isotope_correlation = filter_params.min_isotope_correlation

    async with async_session() as session:
        stmt = (
            select(
                Sample.filename,
                TargetIsotope.relative_abundance,
                Sample.sample_item_id,
                Sample.sample_item_name,
                Sample.sample_item_type,
                TargetCompound.target_compound_formula,
                TargetCompound.target_compound_id,
                TargetCompound.target_compound_name,
                TargetIon.target_ion_formula,
                TargetIon.target_ion_id,
                IonizationMechanism.ionization_mechanism.label("target_ion_mechanism"),
                TargetIsotope.target_isotope_id,
                MatchInterference.sample_peak_interference,
                case(
                    (
                        and_(
                            func.abs(Match.match_mz_error) <= mz_tolerance,
                            func.abs(Match.match_abundance_error)
                            <= isotope_ratio_tolerance,
                            func.max(Match.match_isotope_correlation, 0)
                            >= min_isotope_correlation,
                            TargetIsotope.relative_abundance >= min_isotope_abundance,
                        ),
                        Match.sample_peak_area,
                    ),
                    else_=0,
                ).label("sample_peak_area"),
                case(
                    (
                        and_(
                            func.abs(Match.match_mz_error) <= mz_tolerance,
                            func.abs(Match.match_abundance_error)
                            <= isotope_ratio_tolerance,
                            func.max(Match.match_isotope_correlation, 0)
                            >= min_isotope_correlation,
                            Match.sample_peak_area >= peak_min_intensity,
                            TargetIsotope.relative_abundance >= min_isotope_abundance,
                        ),
                        Match.match_score,
                    ),
                    else_=0,
                ).label("match_score"),
            )
            .select_from(Sample)
            .where(Sample.sample_batch_id == batch_id)
            .join(Match, Sample.sample_item_id == Match.sample_item_id)
            .join(
                MatchInterference,
                and_(
                    Sample.sample_item_id == MatchInterference.sample_item_id,
                    Match.target_isotope_id == MatchInterference.target_isotope_id,
                ),
            )
            .join(
                TargetIsotope,
                Match.target_isotope_id == TargetIsotope.target_isotope_id,
            )
            .join(TargetIon, TargetIsotope.target_ion_id == TargetIon.target_ion_id)
            .join(
                IonizationMechanism,
                TargetIon.ionization_mechanism_id
                == IonizationMechanism.ionization_mechanism_id,
            )
            .join(
                TargetCompound,
                TargetIon.target_compound_id == TargetCompound.target_compound_id,
            )
        )

        result = await session.execute(stmt)
        batch_match_filter = result.fetchall()

        # Convert each Row object in the result into a dictionary
        batch_match_filter_dict = [row._asdict() for row in batch_match_filter]

        message = (
            "Batch match filter successfully initialized"
            if len(batch_match_filter_dict) > 0
            else "No matches found for the batch"
        )
        return {
            "message": message,
            "data": batch_match_filter_dict,
        }


async def init_sample_match_filter(
    sample_batch_id: str, sample_item_id: str, filter_params: FilterParams
):
    mz_tolerance = filter_params.mz_tolerance
    isotope_ratio_tolerance = filter_params.isotope_ratio_tolerance
    peak_min_intensity = filter_params.peak_min_intensity
    min_isotope_abundance = filter_params.min_isotope_abundance
    min_isotope_correlation = filter_params.min_isotope_correlation

    async with async_session() as session:
        stmt = (
            select(
                case(
                    (
                        and_(
                            func.abs(Match.match_mz_error) <= mz_tolerance,
                            func.abs(Match.match_abundance_error)
                            <= isotope_ratio_tolerance,
                            func.max(Match.match_isotope_correlation, 0)
                            >= min_isotope_correlation,
                            Match.sample_peak_area >= peak_min_intensity,
                        ),
                        Match.match_score,
                    ),
                    else_=0,
                ).label("match_score"),
                Match.match_mz_error,
                Match.match_abundance_error,
                Match.match_isotope_correlation,
                Match.sample_item_id,
                case(
                    (
                        and_(
                            func.abs(Match.match_mz_error) <= mz_tolerance,
                            func.abs(Match.match_abundance_error)
                            <= isotope_ratio_tolerance,
                            func.max(Match.match_isotope_correlation, 0)
                            >= min_isotope_correlation,
                        ),
                        Match.sample_peak_area,
                    ),
                    else_=0,
                ).label("sample_peak_area"),
                Match.sample_peak_area_relative,
                Match.sample_peak_mz,
                Match.sample_peak_tof,
                MatchInterference.sample_peak_interference,
                TargetIsotope.mz,
                TargetIsotope.relative_abundance,
                TargetCollection.target_collection_id,
                TargetCollection.target_collection_name,
                TargetCollection.target_collection_description,
                TargetCompound.target_compound_formula,
                TargetCompound.target_compound_id,
                TargetCompound.target_compound_name,
                TargetIon.target_ion_formula,
                TargetIon.target_ion_id,
                TargetIsotope.target_isotope_id,
                literal(2).label("selection"),
            )
            .select_from(Sample)
            .where(
                Sample.sample_item_id == sample_item_id,
            )
            .join(Match, Sample.sample_item_id == Match.sample_item_id)
            .join(
                MatchInterference,
                and_(
                    Sample.sample_item_id == MatchInterference.sample_item_id,
                    Match.target_isotope_id == MatchInterference.target_isotope_id,
                ),
            )
            .join(
                TargetIsotope,
                Match.target_isotope_id == TargetIsotope.target_isotope_id,
            )
            .join(TargetIon, TargetIsotope.target_ion_id == TargetIon.target_ion_id)
            .join(
                TargetCompound,
                TargetIon.target_compound_id == TargetCompound.target_compound_id,
            )
            .join(
                TargetCompoundInTargetCollection,
                TargetCompound.target_compound_id
                == TargetCompoundInTargetCollection.target_compound_id,
            )
            .join(
                TargetCollection,
                TargetCompoundInTargetCollection.target_collection_id
                == TargetCollection.target_collection_id,
            )
            .join(
                TargetCollectionInSampleBatch,
                TargetCollection.target_collection_id
                == TargetCollectionInSampleBatch.target_collection_id,
            )
            .where(
                and_(
                    TargetCollectionInSampleBatch.sample_batch_id == sample_batch_id,
                    Match.sample_item_id == sample_item_id,
                    TargetIsotope.relative_abundance >= min_isotope_abundance,
                    Sample.sample_batch_id == sample_batch_id,
                )
            )
        )

        result = await session.execute(stmt)
        sample_match_filter = result.fetchall()

        # Convert each Row object in the result into a dictionary
        sample_match_filter_dict = [row._asdict() for row in sample_match_filter]

        message = (
            "Sample match filter successfully initialized"
            if len(sample_match_filter_dict) > 0
            else "No matches found for the sample"
        )
        return {
            "message": message,
            "data": sample_match_filter_dict,
        }


async def get_targets(sample_batch_id: str, ion_mechanisms: List[str]):
    async with async_session() as session:
        #   TargetCollections
        # Fetch TargetCollections associated with the sample_batch_id
        target_collections = await session.execute(
            select(
                TargetCollection,
                literal(0).label("selection"),
            )
            .join(
                TargetCollectionInSampleBatch,
                TargetCollectionInSampleBatch.target_collection_id
                == TargetCollection.target_collection_id,
            )
            .filter(TargetCollectionInSampleBatch.sample_batch_id == sample_batch_id)
        )
        target_collections = target_collections.scalars().all()

        # Fetch the required target_collection_ids
        target_collection_ids = [tc.target_collection_id for tc in target_collections]

        #   TargetCompounds
        # Fetch TargetCompounds associated with the fetched TargetCollections and add the associated target_collection_id
        target_compounds_query = await session.execute(
            select(TargetCompound)
            .join(
                TargetCompoundInTargetCollection,
                TargetCompoundInTargetCollection.target_compound_id
                == TargetCompound.target_compound_id,
            )
            .filter(
                TargetCompoundInTargetCollection.target_collection_id.in_(
                    [tc.target_collection_id for tc in target_collections]
                )
            )
        )
        target_compounds = target_compounds_query.scalars().all()

        associations_list = []

        associations = await session.execute(
            select(
                TargetCompoundInTargetCollection.target_compound_id,
                TargetCompoundInTargetCollection.target_collection_id,
            ).filter(
                TargetCompoundInTargetCollection.target_collection_id.in_(
                    target_collection_ids
                )
            )
        )

        for association in associations:
            compound_id = association.target_compound_id
            collection_id = association.target_collection_id
            associations_list.append((compound_id, collection_id))

        # Convert target_compounds to a dictionary for faster lookup
        target_compounds_dict_lookup = {
            tc.target_compound_id: tc for tc in target_compounds
        }

        target_compounds_dict = []
        for compound_id, collection_id in associations_list:
            tc = target_compounds_dict_lookup.get(compound_id)
            if tc:
                target_compounds_dict.append(
                    {
                        **tc.to_dict(),
                        "target_collection_id": collection_id,
                        "selection": 0,
                    }
                )

        #   TargetIons
        # Fetch TargetIons associated with the fetched TargetCompounds, ion_mechanisms, and relevant TargetCollections
        target_ions_query = await session.execute(
            select(TargetIon)
            .distinct(TargetIon.target_ion_id)
            .join(
                TargetCompoundInTargetCollection,
                TargetIon.target_compound_id
                == TargetCompoundInTargetCollection.target_compound_id,
            )
            .join(
                IonizationMechanism,
                TargetIon.ionization_mechanism_id
                == IonizationMechanism.ionization_mechanism_id,
            )
            .filter(
                TargetCompoundInTargetCollection.target_collection_id.in_(
                    target_collection_ids
                ),
                TargetIon.target_compound_id.in_(
                    [tc.target_compound_id for tc in target_compounds]
                ),
                IonizationMechanism.ionization_mechanism_id.in_(ion_mechanisms),
            )
        )
        target_ions = target_ions_query.scalars().all()

        # Create a lookup dictionary for target_compound_id -> target_collection_id
        target_compound_to_collection = {
            tc["target_compound_id"]: tc["target_collection_id"]
            for tc in target_compounds_dict
        }

        # Fetch all ionization mechanisms and create a lookup dictionary for them
        ion_mechanisms_query = await session.execute(
            select(
                IonizationMechanism.ionization_mechanism_id,
                IonizationMechanism.ionization_mechanism,
            )
        )
        ion_mechanisms_associations = {
            im.ionization_mechanism_id: im.ionization_mechanism
            for im in ion_mechanisms_query
        }

        # Create TargetIons dictionary including the new fields
        target_ions_dict = [
            {
                **ti.to_dict(),
                "target_collection_id": target_compound_to_collection.get(
                    ti.target_compound_id
                ),
                "ionization_mechanism": ion_mechanisms_associations.get(
                    ti.ionization_mechanism_id
                ),
                "selection": 0,
            }
            for ti in target_ions
        ]
        #   TargetIsotopes
        # Fetch TargetIsotopes associated with the fetched TargetIons
        target_isotopes = await session.execute(
            select(
                TargetIsotope,
                literal(0).label("selection"),
            ).filter(
                TargetIsotope.target_ion_id.in_(
                    [ti.target_ion_id for ti in target_ions]
                )
            )
        )
        target_isotopes = target_isotopes.scalars().all()

        return {
            "target_collections_count": len(target_collections),
            "target_compounds_count": len(target_compounds),
            "target_ions_count": len(target_ions),
            "target_isotopes_count": len(target_isotopes),
            "target_collections": [
                tc.to_dict(include_selection=True) for tc in target_collections
            ],
            "target_compounds": target_compounds_dict,
            "target_ions": target_ions_dict,
            "target_isotopes": [
                ti.to_dict(include_selection=True) for ti in target_isotopes
            ],
        }
