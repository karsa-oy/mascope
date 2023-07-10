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
)

from backend.db_api_rest import async_session

from ..models.models import (
    Sample,
    SampleBatch,
    SampleItem,
    SampleFile,
    Match,
    TargetCompound,
    TargetIon,
    IonizationMechanism,
    TargetIsotope,
    MatchInterference,
)

from ..models.pydantic_models.sample_pydantic_model import FilterParams


async def get_sample_by_id(sample_id: str):
    async with async_session() as session:
        stmt = select(Sample).filter(Sample.sample_id == sample_id)
        result = await session.execute(stmt)
        sample = result.scalars().first()

        if not sample:
            raise HTTPException(
                status_code=404,
                detail=f"Sample with ID {sample_id} not found",
            )

        return sample.to_dict()


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
    sort: str = None,
    order: str = None,
    filter_params: FilterParams = None,
    page: int = 0,
    limit: int = 10000,
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

        # Calculate and add fields match_score, sample_peak_area_sum, sample_peak_interference_sum, matched

        # Convert samples into dataframe
        samples_df = pd.DataFrame([sample.to_dict() for sample in samples])

        if sample_batch_id and filter_params:
            # call to init_match_filter
            batch_match_filter_dict = await init_match_filter(
                sample_batch_id, filter_params
            )

            # Convert the result to a dataframe
            batch_match_filter_df = pd.DataFrame(batch_match_filter_dict)

            # Group by sample_item_id, target_compound_id, target_ion_id and summing the product of match_score and relative_abundance,
            # sum of sample_peak_area and sum of sample_peak_interference
            batch_match_filter_df = (
                batch_match_filter_df.groupby(
                    ["sample_item_id", "target_compound_id", "target_ion_id"]
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
                        "match_score": "match_score",
                        "sample_peak_area": "sample_peak_area_sum",
                        "sample_peak_interference": "sample_peak_interference_sum",
                    }
                )
            )

            # print("\nDataFrame after first groupby:\n", batch_match_filter_df)

            # Preserving the sample_peak_interference_sum of isotope lvl sum of the row with max match_score
            max_match_score_idx = batch_match_filter_df.groupby(["sample_item_id"])[
                "match_score"
            ].idxmax()

            batch_match_filter_df[
                "sample_peak_interference_sum_max_match_score"
            ] = batch_match_filter_df.loc[
                max_match_score_idx, "sample_peak_interference_sum"
            ]

            # Group by sample_item_id and calculating the max of match_score, sum of sample_peak_area and sum of sample_peak_interference
            batch_match_filter_df = (
                batch_match_filter_df.groupby(["sample_item_id"])
                .agg(
                    {
                        "match_score": "max",
                        "sample_peak_area_sum": "sum",
                        "sample_peak_interference_sum_max_match_score": "first",
                    }
                )
                .reset_index()
                .rename(
                    columns={
                        "sample_peak_interference_sum_max_match_score": "sample_peak_interference_sum"
                    }
                )
            )

            # print("\nDataFrame after second groupby:\n", batch_match_filter_df)

            # Merge with samples dataframe
            samples_df = pd.merge(
                samples_df, batch_match_filter_df, how="left", on="sample_item_id"
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

            # Add matched column
            samples_df["matched"] = samples_df["match_score"].apply(
                lambda x: 0 if x == 0 or x is None else 1
            )

        #  Add 'selection' field
        if sample_item_id_active is not None:
            samples_df["selection"] = samples_df["sample_item_id"].apply(
                lambda x: 3 if x == sample_item_id_active else 0
            )
        else:
            samples_df["selection"] = 0

        return {"results": total, "data": samples_df.to_dict("records")}


async def init_match_filter(batch_id: str, filter_params: FilterParams):
    mz_tolerance = filter_params.mz_tolerance
    isotope_ratio_tolerance = filter_params.isotope_ratio_tolerance
    peak_min_intensity = filter_params.peak_min_intensity
    min_isotope_abundance = filter_params.min_isotope_abundance
    min_isotope_correlation = filter_params.min_isotope_correlation
    # TODO use default value if not provided in filter_params, can be added in js or pydantic_model FilterParams
    print("Batch match filter successfully initialized")
    async with async_session() as session:
        stmt = (
            select(
                SampleItem.filename,
                TargetIsotope.relative_abundance,
                SampleItem.sample_item_id,
                SampleItem.sample_item_name,
                SampleItem.sample_item_type,
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
            .select_from(SampleItem)
            .join(
                SampleBatch, SampleItem.sample_batch_id == SampleBatch.sample_batch_id
            )
            .join(SampleFile, SampleFile.filename == SampleItem.filename)
            .join(Match, SampleItem.sample_item_id == Match.sample_item_id)
            .join(
                MatchInterference,
                and_(
                    SampleItem.sample_item_id == MatchInterference.sample_item_id,
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
            .where(SampleBatch.sample_batch_id == batch_id)
        )

        # return stmt
        result = await session.execute(stmt)
        batch_match_filter = result.fetchall()

        # Convert each Row object in the result into a dictionary
        batch_match_filter_dict = [row._asdict() for row in batch_match_filter]

        return batch_match_filter_dict
