import os
import sqlite3
import shutil


from mascope_server.runtime import runtime


def run():
    # STEP 1 - setup new database
    old_db_path = os.path.join(runtime.config.database, "mascope.v11.db")
    new_db_path = os.path.join(runtime.config.database, "mascope.v12.db")
    shutil.copyfile(old_db_path, new_db_path)
    new_conn = sqlite3.connect(database=new_db_path)
    with new_conn:
        # Step 2 - Add "polarity" column to "sample_file" table
        new_conn.cursor().execute(
            """--sql
            ALTER TABLE sample_file
            ADD polarity VARCHAR(1)
            """
        )

        # Step 3 - Populate "polarity" column based on ionization mechanisms of
        # sample items derived from sample files. The ionization mechanisms are deferred
        # from matches related to the sample item.
        # NOTE: In case there are no matches, polarity will not be populated and left NULL
        for polarity in ["+", "-"]:
            new_conn.cursor().execute(
                f"""--sql
                UPDATE sample_file
                SET polarity = "{polarity}"
                WHERE filename IN
                (
                SELECT filename
                FROM sample_item
                WHERE sample_item_id IN
                (
                    -- Get sample_item_ids from specific polarity matches
                    SELECT DISTINCT sample_item_id
                    FROM match
                    WHERE target_isotope_id IN
                        (
                        -- Get specific polarity target isotopes
                        SELECT target_isotope_id
                        FROM target_isotope
                        WHERE target_ion_id IN
                            -- Get specific polarity target ions
                            (
                            SELECT target_ion_id
                            FROM target_ion
                            WHERE ionization_mechanism_id IN
                                -- Get specific polarity ionization mechanisms
                                (
                                SELECT ionization_mechanism_id
                                FROM ionization_mechanism
                                WHERE ionization_mechanism_polarity = "{polarity}"
                                )
                            )
                        )
                )
                )
                """
            )

        # Step 4 - Drop old sample_view
        new_conn.cursor().execute(
            """--sql
            DROP VIEW IF EXISTS sample_view;
            """
        )

        # Step 5 - Create new sample_view including polarity
        new_conn.cursor().execute(
            """--sql
            CREATE VIEW sample_view AS
            SELECT
                sample_item.sample_item_id,
                sample_file.sample_file_id,
                sample_item.sample_batch_id,
                sample_item.sample_item_name,
                sample_file.instrument,
                sample_item.filename,
                sample_item.sample_item_type,
                sample_item.sample_item_attributes,
                sample_item.filter_id,
                sample_file.length,
                sample_file.tic,
                sample_file.range,
                sample_file.mz_calibration,
                sample_file.datetime,
                sample_file.datetime_utc,
                sample_item.sample_item_utc_created,
                sample_item.sample_item_utc_modified,
                sample_file.polarity
            FROM
                sample_item
            JOIN
                sample_file ON sample_item.filename = sample_file.filename
            """
        )
