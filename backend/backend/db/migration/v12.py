import os
import sqlite3
import shutil


def run():
    data_path = os.environ.get("MASCOPE_PRIVATE_DATABASE_DIR")

    # STEP 1 - setup new database
    old_db_path = os.path.join(data_path, "mascope.v11.db")
    new_db_path = os.path.join(data_path, "mascope.v12.db")
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
