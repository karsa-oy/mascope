"""Add description column to access_token

Device pairing stamps the paired machine's hostname on the token it
creates, so multiple tokens per (user, service) stay distinguishable.

Revision ID: f2d8b5c3a9e1
Revises: a1c9f4e7d2b8
Create Date: 2026-07-25 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "f2d8b5c3a9e1"
down_revision: Union[str, Sequence[str], None] = "a1c9f4e7d2b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "access_token",
        sa.Column("description", sa.String(length=100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("access_token", "description")
