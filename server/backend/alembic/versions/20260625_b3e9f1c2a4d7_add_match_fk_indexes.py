"""Add missing foreign-key indexes on match tables

Indexes the previously-unindexed FK columns on match_collection,
match_compound, and match_rating so cascade deletes (and target-side lookups)
use an index instead of a sequential scan. Pairs with passive_deletes=True on
the delete-chain relationships, which lets the DB perform the cascade.

Revision ID: b3e9f1c2a4d7
Revises: d46523dd8fdd
Create Date: 2026-06-25 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b3e9f1c2a4d7"
down_revision: Union[str, Sequence[str], None] = "d46523dd8fdd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        op.f("ix_match_collection_target_collection_id"),
        "match_collection",
        ["target_collection_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_match_compound_target_compound_id"),
        "match_compound",
        ["target_compound_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_match_rating_sample_item_id"),
        "match_rating",
        ["sample_item_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_match_rating_target_ion_id"),
        "match_rating",
        ["target_ion_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_match_rating_target_ion_id"), table_name="match_rating")
    op.drop_index(op.f("ix_match_rating_sample_item_id"), table_name="match_rating")
    op.drop_index(
        op.f("ix_match_compound_target_compound_id"), table_name="match_compound"
    )
    op.drop_index(
        op.f("ix_match_collection_target_collection_id"),
        table_name="match_collection",
    )
