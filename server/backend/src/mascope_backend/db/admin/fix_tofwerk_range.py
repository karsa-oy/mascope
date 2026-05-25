"""
Database and filestore administration operation for fixing the sample_file
range values corrupted by a bug in the TofWerk H5Processor.

The ``range`` property of ``H5Processor`` returned the entire MassAxis array
(potentially thousands of floats) instead of ``[first, last]``.  This caused
the full mass axis to be stored in:

1. PostgreSQL ``sample_file.range`` JSON column
2. Filestore ``.props`` JSON files

Detection: affected rows have ``json_array_length(range) > 2``.

Fix: replace the array with ``[range[0], range[-1]]`` — the first and last
elements of the stored mass axis, which are the correct min/max m/z values.

Entry Points:
- Async: ``fix_tofwerk_range()`` for async callers
- CLI: ``mascope dev db script run fix_tofwerk_range``
"""

import json
import os

from sqlalchemy import text

from mascope_backend.db import async_session
from mascope_backend.runtime import runtime


async def fix_tofwerk_range() -> dict:
    """Correct the ``range`` column for sample_file rows where the full
    mass axis was stored instead of ``[first, last]``, and patch the
    corresponding ``.props`` files in the filestore.

    :return: Summary with counts and lists of affected/fixed items.
    :rtype: dict
    """
    db_result = await _fix_database()
    filestore_result = _fix_filestore(db_result["filenames"])

    return {
        "database": db_result,
        "filestore": filestore_result,
    }


async def _fix_database() -> dict:
    """Find and fix rows in ``sample_file`` where ``range`` has > 2 elements.

    :return: ``{"affected": int, "updated": int, "filenames": list[str]}``
    :rtype: dict
    """
    async with async_session() as session:
        # --- Preview affected rows ---
        preview_result = await session.execute(
            text("""
                SELECT sample_file_id,
                       filename,
                       json_array_length(range) AS range_len
                FROM sample_file
                WHERE json_array_length(range) > 2
                ORDER BY datetime
            """)
        )
        affected_rows = [dict(row._mapping) for row in preview_result]
        affected = len(affected_rows)

        for row in affected_rows:
            runtime.logger.info(
                f"  {row['filename']}: range has {row['range_len']} elements"
            )

        filenames = [row["filename"] for row in affected_rows]

        if affected == 0:
            runtime.logger.info("No rows with corrupted range found.")
            return {"affected": 0, "updated": 0, "filenames": []}

        runtime.logger.info(f"Total affected rows: {affected}")

        # --- Fix: keep only first and last element ---
        update_result = await session.execute(
            text("""
                UPDATE sample_file
                SET range = (
                    SELECT json_build_array(range->0, range->(json_array_length(range) - 1))
                )
                WHERE json_array_length(range) > 2
            """)
        )

        await session.commit()
        runtime.logger.info(f"Updated {update_result.rowcount} database rows.")

        return {
            "affected": affected,
            "updated": update_result.rowcount,
            "filenames": filenames,
        }


def _fix_filestore(filenames: list[str]) -> dict:
    """Patch ``.props`` files for the given sample filenames.

    :param filenames: List of sample filenames whose ``.props`` may need fixing.
    :return: ``{"checked": int, "updated": int, "missing": int, "errors": list}``
    :rtype: dict
    """
    import mascope_file.name as m_name

    checked = 0
    updated = 0
    missing = 0
    errors = []

    for filename in filenames:
        checked += 1
        try:
            sample_path = m_name.parse_path_from_item_filename(filename)
        except Exception as exc:
            runtime.logger.warning(f"  Cannot resolve path for {filename}: {exc}")
            errors.append(filename)
            continue

        props_path = os.path.join(sample_path, ".props")

        if not os.path.isfile(props_path):
            runtime.logger.warning(f"  .props not found: {props_path}")
            missing += 1
            continue

        try:
            with open(props_path, "r") as f:
                props = json.load(f)
        except Exception as exc:
            runtime.logger.warning(f"  Cannot read {props_path}: {exc}")
            errors.append(filename)
            continue

        mz_range = props.get("range")
        if not isinstance(mz_range, list) or len(mz_range) <= 2:
            continue  # Already correct

        corrected = [mz_range[0], mz_range[-1]]
        props["range"] = corrected

        try:
            with open(props_path, "w") as f:
                json.dump(props, f, indent=4)
            updated += 1
            runtime.logger.info(f"  Fixed {filename}: {len(mz_range)} -> 2 elements")
        except Exception as exc:
            runtime.logger.warning(f"  Cannot write {props_path}: {exc}")
            errors.append(filename)

    runtime.logger.info(
        f"Filestore: checked={checked}, updated={updated}, "
        f"missing={missing}, errors={len(errors)}"
    )

    return {
        "checked": checked,
        "updated": updated,
        "missing": missing,
        "errors": errors,
    }
