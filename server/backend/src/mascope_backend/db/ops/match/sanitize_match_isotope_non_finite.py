"""
Database operation to sanitize non-finite values in match_isotope.

Rules:
- sample_peak_intensity_relative: set all non-finite values to 0.0
- match_abundance_error: set +Infinity to 1.0 and -Infinity to -1.0
- match_abundance_error NaN values are left unchanged

Entry Points:
- Async: `sanitize_match_isotope_non_finite()` for async callers
- Sync: `run_sanitize_match_isotope_non_finite()` for CLI/scripts
"""

import asyncio

from sqlalchemy import text

from mascope_backend.db import async_session, configure_database_engine
from mascope_backend.db.ops.backup import create_db_backup
from mascope_backend.db.utils import get_current_db_version
from mascope_backend.runtime import runtime


POS_INF_THRESHOLD = 1e308
NEG_INF_THRESHOLD = -1e308


async def sanitize_match_isotope_non_finite() -> dict[str, int]:
    """
    Sanitize non-finite values in match_isotope.

    Assumes database engine is already configured.

    :return: Summary counts for detected and updated rows
    :rtype: dict[str, int]
    """
    async with async_session() as session:
        before_non_finite_relative = int(
            (
                await session.execute(
                    text(
                        """
                        SELECT COUNT(*)
                        FROM match_isotope
                        WHERE sample_peak_intensity_relative > :pos_inf_threshold
                           OR sample_peak_intensity_relative < :neg_inf_threshold
                           OR sample_peak_intensity_relative != sample_peak_intensity_relative
                        """
                    ),
                    {
                        "pos_inf_threshold": POS_INF_THRESHOLD,
                        "neg_inf_threshold": NEG_INF_THRESHOLD,
                    },
                )
            ).scalar_one()
        )

        before_pos_inf_abundance_error = int(
            (
                await session.execute(
                    text(
                        """
                        SELECT COUNT(*)
                        FROM match_isotope
                        WHERE match_abundance_error > :pos_inf_threshold
                        """
                    ),
                    {"pos_inf_threshold": POS_INF_THRESHOLD},
                )
            ).scalar_one()
        )

        before_neg_inf_abundance_error = int(
            (
                await session.execute(
                    text(
                        """
                        SELECT COUNT(*)
                        FROM match_isotope
                        WHERE match_abundance_error < :neg_inf_threshold
                        """
                    ),
                    {"neg_inf_threshold": NEG_INF_THRESHOLD},
                )
            ).scalar_one()
        )

        await session.execute(
            text(
                """
                UPDATE match_isotope
                SET sample_peak_intensity_relative = 0.0
                WHERE sample_peak_intensity_relative > :pos_inf_threshold
                   OR sample_peak_intensity_relative < :neg_inf_threshold
                   OR sample_peak_intensity_relative != sample_peak_intensity_relative
                """
            ),
            {
                "pos_inf_threshold": POS_INF_THRESHOLD,
                "neg_inf_threshold": NEG_INF_THRESHOLD,
            },
        )

        await session.execute(
            text(
                """
                UPDATE match_isotope
                SET match_abundance_error = 1.0
                WHERE match_abundance_error > :pos_inf_threshold
                """
            ),
            {"pos_inf_threshold": POS_INF_THRESHOLD},
        )

        await session.execute(
            text(
                """
                UPDATE match_isotope
                SET match_abundance_error = -1.0
                WHERE match_abundance_error < :neg_inf_threshold
                """
            ),
            {"neg_inf_threshold": NEG_INF_THRESHOLD},
        )

        await session.commit()

        after_non_finite_relative = int(
            (
                await session.execute(
                    text(
                        """
                        SELECT COUNT(*)
                        FROM match_isotope
                        WHERE sample_peak_intensity_relative > :pos_inf_threshold
                           OR sample_peak_intensity_relative < :neg_inf_threshold
                           OR sample_peak_intensity_relative != sample_peak_intensity_relative
                        """
                    ),
                    {
                        "pos_inf_threshold": POS_INF_THRESHOLD,
                        "neg_inf_threshold": NEG_INF_THRESHOLD,
                    },
                )
            ).scalar_one()
        )

        after_pos_inf_abundance_error = int(
            (
                await session.execute(
                    text(
                        """
                        SELECT COUNT(*)
                        FROM match_isotope
                        WHERE match_abundance_error > :pos_inf_threshold
                        """
                    ),
                    {"pos_inf_threshold": POS_INF_THRESHOLD},
                )
            ).scalar_one()
        )

        after_neg_inf_abundance_error = int(
            (
                await session.execute(
                    text(
                        """
                        SELECT COUNT(*)
                        FROM match_isotope
                        WHERE match_abundance_error < :neg_inf_threshold
                        """
                    ),
                    {"neg_inf_threshold": NEG_INF_THRESHOLD},
                )
            ).scalar_one()
        )

    return {
        "before_non_finite_relative": before_non_finite_relative,
        "before_pos_inf_abundance_error": before_pos_inf_abundance_error,
        "before_neg_inf_abundance_error": before_neg_inf_abundance_error,
        "after_non_finite_relative": after_non_finite_relative,
        "after_pos_inf_abundance_error": after_pos_inf_abundance_error,
        "after_neg_inf_abundance_error": after_neg_inf_abundance_error,
        "updated_relative": before_non_finite_relative - after_non_finite_relative,
        "updated_pos_inf_abundance_error": before_pos_inf_abundance_error
        - after_pos_inf_abundance_error,
        "updated_neg_inf_abundance_error": before_neg_inf_abundance_error
        - after_neg_inf_abundance_error,
    }


async def init_db_and_sanitize_match_isotope_non_finite() -> dict[str, int]:
    """
    Initialize DB connection and run match_isotope non-finite sanitation.

    :return: Summary counts for detected and updated rows
    :rtype: dict[str, int]
    """
    current_db_version = get_current_db_version()
    if current_db_version is None:
        raise RuntimeError("No database found. Please create a database first.")

    await configure_database_engine(current_db_version)
    runtime.logger.info(f"Connected to database v{current_db_version}")

    await create_db_backup()
    runtime.logger.info("Backup created before sanitation")

    result = await sanitize_match_isotope_non_finite()

    runtime.logger.info(
        "Sanitized match_isotope non-finite values: "
        f"relative={result['updated_relative']}, "
        f"abundance +Inf={result['updated_pos_inf_abundance_error']}, "
        f"abundance -Inf={result['updated_neg_inf_abundance_error']}"
    )

    return result


def run_sanitize_match_isotope_non_finite() -> dict[str, int]:
    """
    Synchronous entry point for match_isotope non-finite sanitation.

    :return: Summary counts for detected and updated rows
    :rtype: dict[str, int]
    """
    return asyncio.run(init_db_and_sanitize_match_isotope_non_finite())
