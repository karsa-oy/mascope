import pandas as pd

from fastapi import HTTPException
from sqlalchemy import (
    asc,
    desc,
    and_,
    select,
    func,
    case,
    or_,
    text,
    literal,
    literal_column,
)
from sqlalchemy.orm import aliased

from backend.db_api_rest import async_session

from ..models.models import (
    SampleBatch,
    SampleItem,
    SampleFile,
    Match,
    TargetCollectionInSampleBatch,
    TargetCollection,
    TargetCompoundInTargetCollection,
    TargetCompound,
    TargetIon,
    IonizationMechanism,
    TargetIsotope,
    MatchInterference,
)

from ..models.pydantic_models.sample_pydantic_model import FilterParams


async def init_match_filter(batch_id: str, filter_params: FilterParams):
    mz_tolerance = filter_params.mz_tolerance
    isotope_ratio_tolerance = filter_params.isotope_ratio_tolerance
    peak_min_intensity = filter_params.peak_min_intensity
    min_isotope_abundance = filter_params.min_isotope_abundance
    min_isotope_correlation = filter_params.min_isotope_correlation
    # TODO use default value if not provided in filter_params

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

        result = await session.execute(stmt)
        batch_match_filter = result.fetchall()

        # Fetch column names from the result
        column_names = result.keys()

        return pd.DataFrame(batch_match_filter, columns=column_names)
        # Transform rows to dictionary using column names
        # return [
        #     {column_name: row[i] for i, column_name in enumerate(column_names)}
        #     for row in batch_match_filter
        # ]

        # # Drop the temporary table if it exists
        # session.execute(text("DROP TABLE IF EXISTS batch_match_filter"))

        # # Create the temporary table from the subquery
        # session.execute(
        #     text(
        #         f"CREATE TEMPORARY TABLE batch_match_filter AS SELECT * FROM {subquery}"
        #     )
        # )
        # session.commit()

    # return batch_match_filter


# _____________________________________WORKING VERSION______________________________________
async def load_samples(
    batch_id: str, sample_item_active_id: str = None, filter_params: FilterParams = None
):
    batch_match_filter = await init_match_filter(batch_id, filter_params)

    # Group the DataFrame by the required fields and compute aggregates
    grouped_batch_match_filter = (
        batch_match_filter.groupby(
            ["sample_item_id", "target_ion_id", "target_compound_id"]
        )
        .agg(
            match_score=("match_score", "sum"),
            sample_peak_area_sum=("sample_peak_area", "sum"),
            sample_peak_interference_sum=("sample_peak_interference", "sum"),
        )
        .reset_index()
    )

    # Convert the DataFrame to a list of dictionaries
    grouped_data = grouped_batch_match_filter.to_dict("records")

    async with async_session() as session:
        subquery = (
            select(
                SampleItem.sample_item_id,
                TargetIon.target_ion_id,
                TargetCompound.target_compound_id,
                (func.sum(Match.match_score * TargetIsotope.relative_abundance)).label(
                    "match_score"
                ),
                (func.sum(Match.sample_peak_area)).label("sample_peak_area_sum"),
                (func.sum(MatchInterference.sample_peak_interference)).label(
                    "sample_peak_interference_sum"
                ),
            )
            .select_from(SampleItem)
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
                TargetCompound,
                TargetIon.target_compound_id == TargetCompound.target_compound_id,
            )
            .where(SampleItem.sample_batch_id == batch_id)
            .group_by(
                SampleItem.sample_item_id,
                TargetCompound.target_compound_id,
                TargetIon.target_ion_id,
            )
            .subquery()
        )

        stmt = (
            select(
                SampleItem.sample_item_id,
                SampleItem.sample_item_name,
                SampleItem.sample_item_attributes,
                SampleItem.sample_item_type,
                SampleItem.sample_batch_id,
                SampleFile.sample_file_id,
                SampleItem.filter_id,
                SampleFile.datetime,
                SampleFile.datetime_utc,
                SampleFile.filename,
                SampleFile.instrument,
                SampleFile.length,
                SampleFile.range,
                SampleFile.mz_calibration,
                SampleItem.sample_item_utc_created,
                SampleItem.sample_item_utc_modified,
                case(
                    (Match.match_score.is_(None), 0),
                    else_=1,
                ).label("matched"),
                func.ifnull(func.max(subquery.c.match_score), 0).label("match_score"),
                func.ifnull(func.sum(subquery.c.sample_peak_area_sum), 0).label(
                    "sample_peak_area_sum"
                ),
                subquery.c.sample_peak_interference_sum.label(
                    "sample_peak_interference_sum"
                ),
                case(
                    (SampleItem.sample_item_id == sample_item_active_id, 3),
                    else_=0,
                ).label("selection"),
                SampleFile.tic,
            )
            .select_from(subquery)
            .join(SampleItem, SampleItem.sample_item_id == subquery.c.sample_item_id)
            .join(SampleFile, SampleItem.filename == SampleFile.filename)
            # .group_by(SampleItem.sample_item_id)
            # .order_by(SampleItem.sample_item_utc_created.asc())
            # )
            # Now, use the `grouped_data` for filtering in the where clause
            .where(
                SampleItem.sample_item_id.in_(
                    [d["sample_item_id"] for d in grouped_data]
                )
            )
            .group_by(SampleItem.sample_item_id)
            .order_by(SampleItem.sample_item_utc_created.asc())
        )

        result = await session.execute(stmt)
        load_samples = result.fetchall()

        column_names = result.keys()

        return [
            {column_name: row[i] for i, column_name in enumerate(column_names)}
            for row in load_samples
        ]
