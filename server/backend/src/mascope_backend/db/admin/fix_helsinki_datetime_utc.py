"""
Database administration operation for fixing datetime_utc values corrupted
by the Europe/Helsinki Docker timezone misconfiguration.

The backend Dockerfile was configured with MASCOPE_TIMEZONE=Europe/Helsinki
instead of Etc/UTC.  Processors that fall back to the container's local
timezone (RawProcessor always, TofProcessor when the HDF5 file lacks the
LocalTimeOffsetToUTC attribute) computed a non-zero utc_offset (7 200 s for
EET / 10 800 s for EEST) which was then subtracted from the correct local
datetime to produce datetime_utc.  Because the client PCs are in UTC, the
correct utc_offset is 0 and datetime_utc should equal datetime.

The offset was applied twice:
  1. Python: datetime_utc = timestamp - utc_offset  (produces naive ISO string)
  2. PostgreSQL: naive timestamp inserted into TIMESTAMP WITH TIME ZONE column
     is interpreted in the session timezone (also Helsinki), subtracting the
     offset a second time.

Possible offsets per row:
  - 2 h (EET applied once)   or  4 h (EET applied twice)
  - 3 h (EEST applied once)  or  6 h (EEST applied twice)

Detection: affected rows satisfy
    (datetime AT TIME ZONE 'UTC') - datetime_utc  IN  {2h, 3h, 4h, 6h}

Fix: set datetime_utc = datetime AT TIME ZONE 'UTC' for those rows.

Entry Points:
- Async: `fix_helsinki_datetime_utc()` for async callers
- CLI: `mascope dev db script run fix_helsinki_datetime_utc`
"""

from datetime import datetime

from sqlalchemy import text

from mascope_backend.db import async_session
from mascope_backend.runtime import runtime


# Helsinki UTC offsets applied once or twice:
#   EET  = +02:00 -> 2h (single) or 4h (double)
#   EEST = +03:00 -> 3h (single) or 6h (double)
_HELSINKI_OFFSETS_SECONDS = [7200, 10800, 14400, 21600]


async def fix_helsinki_datetime_utc(
    min_datetime: datetime | None = None,
) -> dict:
    """Correct datetime_utc for sample_file rows affected by the Helsinki
    timezone bug.

    Identifies rows where the gap between datetime (correct local/UTC value)
    and datetime_utc equals 2, 3, 4, or 6 hours (Helsinki offsets applied
    once or twice), then sets datetime_utc = datetime interpreted as UTC.

    :param min_datetime: If set, only rows with ``datetime >= min_datetime``
        are considered.  Use this to skip legacy data where the Helsinki
        offset was intentional.
    :return: Summary ``{"affected": int, "updated": int, "previewed": list}``
    :rtype: dict
    """
    # Build optional WHERE clause for the cutoff
    cutoff_clause = "AND datetime >= :min_dt" if min_datetime else ""
    params: dict = {"offsets": _HELSINKI_OFFSETS_SECONDS}
    if min_datetime:
        params["min_dt"] = min_datetime
        runtime.logger.info(
            f"Applying cutoff: only rows with datetime >= {min_datetime.isoformat()}"
        )

    async with async_session() as session:
        # --- Preview affected rows ---
        preview_result = await session.execute(
            text(f"""
                SELECT sample_file_id,
                       filename,
                       datetime,
                       datetime_utc,
                       datetime AT TIME ZONE 'UTC' AS corrected_utc,
                       EXTRACT(EPOCH FROM (
                           (datetime AT TIME ZONE 'UTC') - datetime_utc
                       ))::int AS offset_seconds
                FROM sample_file
                WHERE EXTRACT(EPOCH FROM (
                          (datetime AT TIME ZONE 'UTC') - datetime_utc
                      ))::int = ANY(:offsets)
                {cutoff_clause}
                ORDER BY datetime
                LIMIT 20
            """),
            params,
        )
        previewed = [dict(row._mapping) for row in preview_result]

        # --- Count ---
        count_result = await session.execute(
            text(f"""
                SELECT COUNT(*) FROM sample_file
                WHERE EXTRACT(EPOCH FROM (
                          (datetime AT TIME ZONE 'UTC') - datetime_utc
                      ))::int = ANY(:offsets)
                {cutoff_clause}
            """),
            params,
        )
        affected = count_result.scalar()

        for row in previewed:
            runtime.logger.info(
                f"  {row['filename']}: "
                f"datetime={row['datetime']}  "
                f"datetime_utc={row['datetime_utc']}  ->  "
                f"corrected={row['corrected_utc']}  "
                f"(offset was {row['offset_seconds']}s)"
            )

        if affected == 0:
            runtime.logger.info("No rows affected by Helsinki timezone bug.")
            return {"affected": 0, "updated": 0, "previewed": []}

        runtime.logger.info(f"Total affected rows: {affected}")

        # --- Fix ---
        update_result = await session.execute(
            text(f"""
                UPDATE sample_file
                SET datetime_utc = datetime AT TIME ZONE 'UTC'
                WHERE EXTRACT(EPOCH FROM (
                          (datetime AT TIME ZONE 'UTC') - datetime_utc
                      ))::int = ANY(:offsets)
                {cutoff_clause}
            """),
            params,
        )

        await session.commit()

        return {
            "affected": affected,
            "updated": update_result.rowcount,
            "previewed": previewed,
        }
