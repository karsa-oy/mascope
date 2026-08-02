"""Add a natural-key unique index for ACQUISITION datasets

``get_acquisition_dataset`` is a read-then-write get-or-create with no
constraint on its natural key (workspace_id, instrument, dataset_name), so
concurrent ingest could insert duplicate year-datasets - after which every
lookup fails with MultipleResultsFound and auto-processing dies for all
subsequent files of that instrument/year.

Duplicate datasets own sample batches, so they are merged rather than
deleted: per natural key the oldest dataset (dataset_utc_created, ties broken
by the smaller primary key) is kept, sample batches of the newer duplicates
are repointed to it, and the emptied duplicates are removed. Then the key is
constrained with a partial unique index (user-created dataset types have no
naming invariant) so the race fails loudly and is recovered in code.

Revision ID: e4b7a2c8d1f6
Revises: f2d8b5c3a9e1
Create Date: 2026-08-02 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = "e4b7a2c8d1f6"
down_revision: Union[str, Sequence[str], None] = "f2d8b5c3a9e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


INDEX_NAME = "uq_dataset_acquisition_natural_key"

# Oldest dataset per ACQUISITION natural key. `instrument` is nullable, so
# group NULLs together explicitly (DISTINCT ON treats NULLs as equal, matching
# the IS NOT DISTINCT FROM joins below).
_KEEPERS_CTE = """
    SELECT DISTINCT ON (workspace_id, instrument, dataset_name)
           dataset_id AS keep_id, workspace_id, instrument, dataset_name
    FROM dataset
    WHERE dataset_type = 'ACQUISITION'
    ORDER BY workspace_id, instrument, dataset_name,
             COALESCE(dataset_utc_created, '-infinity'::timestamptz),
             dataset_id
"""

_REPOINT_BATCHES_SQL = f"""
    WITH keepers AS ({_KEEPERS_CTE})
    UPDATE sample_batch sb
    SET dataset_id = k.keep_id
    FROM dataset d
    JOIN keepers k
      ON d.workspace_id = k.workspace_id
     AND d.instrument IS NOT DISTINCT FROM k.instrument
     AND d.dataset_name = k.dataset_name
    WHERE sb.dataset_id = d.dataset_id
      AND d.dataset_type = 'ACQUISITION'
      AND d.dataset_id <> k.keep_id
"""

_DELETE_DUPLICATES_SQL = f"""
    WITH keepers AS ({_KEEPERS_CTE})
    DELETE FROM dataset d
    USING keepers k
    WHERE d.dataset_type = 'ACQUISITION'
      AND d.workspace_id = k.workspace_id
      AND d.instrument IS NOT DISTINCT FROM k.instrument
      AND d.dataset_name = k.dataset_name
      AND d.dataset_id <> k.keep_id
"""


def upgrade() -> None:
    connection = op.get_bind()
    repointed = connection.execute(text(_REPOINT_BATCHES_SQL))
    deleted = connection.execute(text(_DELETE_DUPLICATES_SQL))
    if deleted.rowcount:
        print(
            f"Merged {deleted.rowcount} duplicate ACQUISITION dataset(s) "
            f"({repointed.rowcount} sample batch(es) repointed to the oldest)"
        )
    op.create_index(
        INDEX_NAME,
        "dataset",
        ["workspace_id", "instrument", "dataset_name"],
        unique=True,
        postgresql_where=text("dataset_type = 'ACQUISITION'"),
    )


def downgrade() -> None:
    op.drop_index(INDEX_NAME, table_name="dataset")
