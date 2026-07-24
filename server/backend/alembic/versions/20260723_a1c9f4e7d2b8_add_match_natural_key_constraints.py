"""Add natural-key unique constraints to the match aggregate tables

The match create funnels are read-then-write upserts that historically ran
concurrently with no constraint on their natural keys, so races could insert
duplicate logical rows - reads collapse duplicates into dicts keyed by the
target-side id, silently masking the corruption. Dedupe existing rows first
(keep the newest per key: utc_modified, else utc_created, ties broken by the
larger primary key) and then constrain the keys so a race fails loudly
instead of corrupting data.

Note: building the unique indexes takes a table lock; on very large
match_isotope tables the upgrade can take a while (the db_init flow dumps the
database before migrating).

Revision ID: a1c9f4e7d2b8
Revises: c7a1e5d9b2f4
Create Date: 2026-07-23 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = "a1c9f4e7d2b8"
down_revision: Union[str, Sequence[str], None] = "c7a1e5d9b2f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (table, primary key column, natural key columns, unique constraint name)
MATCH_NATURAL_KEYS: list[tuple[str, str, list[str], str]] = [
    (
        "match_isotope",
        "match_isotope_id",
        ["sample_item_id", "target_isotope_id"],
        "uq_match_isotope_sample_item_target_isotope",
    ),
    (
        "match_ion",
        "match_ion_id",
        ["sample_item_id", "target_ion_id"],
        "uq_match_ion_sample_item_target_ion",
    ),
    (
        "match_compound",
        "match_compound_id",
        ["sample_item_id", "target_compound_id"],
        "uq_match_compound_sample_item_target_compound",
    ),
    (
        "match_collection",
        "match_collection_id",
        ["sample_item_id", "target_collection_id"],
        "uq_match_collection_sample_item_target_collection",
    ),
    (
        "match_sample",
        "match_sample_id",
        ["sample_item_id"],
        "uq_match_sample_sample_item",
    ),
]


def _dedupe_sql(table: str, pk: str, key_cols: list[str]) -> str:
    """
    DELETE that keeps, per natural key, the newest row: greatest
    COALESCE(utc_modified, utc_created), ties broken by the larger primary key.
    A row is deleted when some duplicate of it sorts strictly newer.
    """
    key_match = " AND ".join(f"a.{col} = b.{col}" for col in key_cols)
    ts_a = (
        f"COALESCE(a.{table}_utc_modified, a.{table}_utc_created, "
        "'-infinity'::timestamptz)"
    )
    ts_b = (
        f"COALESCE(b.{table}_utc_modified, b.{table}_utc_created, "
        "'-infinity'::timestamptz)"
    )
    return (
        f"DELETE FROM {table} a "
        f"USING {table} b "
        f"WHERE {key_match} "
        f"AND a.{pk} <> b.{pk} "
        f"AND ({ts_a} < {ts_b} OR ({ts_a} = {ts_b} AND a.{pk} < b.{pk}))"
    )


def upgrade() -> None:
    connection = op.get_bind()
    for table, pk, key_cols, constraint_name in MATCH_NATURAL_KEYS:
        result = connection.execute(text(_dedupe_sql(table, pk, key_cols)))
        if result.rowcount:
            print(f"Deduplicated {result.rowcount} duplicate rows from {table}")
        op.create_unique_constraint(constraint_name, table, key_cols)


def downgrade() -> None:
    for table, _pk, _key_cols, constraint_name in reversed(MATCH_NATURAL_KEYS):
        op.drop_constraint(constraint_name, table, type_="unique")
