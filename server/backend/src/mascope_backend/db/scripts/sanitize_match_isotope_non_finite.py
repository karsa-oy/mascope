"""
Maintenance script to sanitize non-finite values in match_isotope.

Rules:
- sample_peak_intensity_relative: non-finite -> 0.0
- match_abundance_error: +Infinity -> 1.0, -Infinity -> -1.0
- match_abundance_error NaN values remain unchanged

Usage:
    mascope dev db script run sanitize_match_isotope_non_finite
    mascope prod db script run sanitize_match_isotope_non_finite --yes

Date: 2026-03-19
"""

import asyncio

from mascope_backend.db import configure_database_engine
from mascope_backend.db.admin.match.sanitize_match_isotope_non_finite import (
    sanitize_match_isotope_non_finite,
)
from mascope_backend.runtime import runtime


async def run_sanitize() -> None:
    """
    Initialize database and run match_isotope non-finite sanitation
    and log detailed summary.
    """
    await configure_database_engine()

    result = await sanitize_match_isotope_non_finite()

    runtime.logger.info("=" * 80)
    runtime.logger.info("MATCH_ISOTOPE SANITATION COMPLETE")
    runtime.logger.info(
        "Before: "
        f"relative_non_finite={result['before_non_finite_relative']}, "
        f"abundance_pos_inf={result['before_pos_inf_abundance_error']}, "
        f"abundance_neg_inf={result['before_neg_inf_abundance_error']}"
    )
    runtime.logger.info(
        "Updated: "
        f"relative={result['updated_relative']}, "
        f"abundance_pos_inf={result['updated_pos_inf_abundance_error']}, "
        f"abundance_neg_inf={result['updated_neg_inf_abundance_error']}"
    )
    runtime.logger.info(
        "After: "
        f"relative_non_finite={result['after_non_finite_relative']}, "
        f"abundance_pos_inf={result['after_pos_inf_abundance_error']}, "
        f"abundance_neg_inf={result['after_neg_inf_abundance_error']}"
    )
    runtime.logger.info("=" * 80)


def main() -> None:
    """Entry point for the sanitation script."""
    try:
        asyncio.run(run_sanitize())
    except KeyboardInterrupt:
        runtime.logger.info("Sanitation cancelled by user (Ctrl+C)")
    except Exception:
        runtime.logger.exception("Sanitation script failed")
        raise


if __name__ == "__main__":
    main()
