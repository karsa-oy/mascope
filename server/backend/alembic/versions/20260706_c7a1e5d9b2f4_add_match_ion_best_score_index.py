"""Add composite index for best-score-per-ion lookups on match_ion

Supports the batch-level match ion aggregation (top match_score per
target_ion_id) so picking the best match per target ion uses an ordered
index scan (walked backward) instead of sorting every match row.

Revision ID: c7a1e5d9b2f4
Revises: b3e9f1c2a4d7
Create Date: 2026-07-06 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "c7a1e5d9b2f4"
down_revision: Union[str, Sequence[str], None] = "b3e9f1c2a4d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_match_ion_target_ion_id_match_score",
        "match_ion",
        ["target_ion_id", "match_score"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_match_ion_target_ion_id_match_score",
        table_name="match_ion",
    )
