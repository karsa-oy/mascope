"""Add assignment_calibration store

Adds the assignment_calibration table (the D6 calibration store): a per-instrument
score -> P(correct) Platt curve plus per-adduct corroboration log-odds, so an
assignment-confidence calibration can be (re)fit per deployment without a code change.
Schema only - no data is seeded; the loader falls back to the in-code provisional
Orbitrap curve when the table has no active row, so this is additive and safe empty.

Revision ID: d1a2c3b4e5f6
Revises: b2e9d7c14a05
Create Date: 2026-07-09 09:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "d1a2c3b4e5f6"
down_revision: Union[str, Sequence[str], None] = "b2e9d7c14a05"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "assignment_calibration",
        sa.Column(
            "assignment_calibration_id", sa.Integer(), autoincrement=True, nullable=False
        ),
        sa.Column("instrument", sa.String(length=32), nullable=False),
        sa.Column("score_version", sa.Integer(), nullable=False),
        sa.Column("a", sa.Float(), nullable=False),
        sa.Column("b", sa.Float(), nullable=False),
        sa.Column("n_pos", sa.Integer(), nullable=False),
        sa.Column("n_neg", sa.Integer(), nullable=False),
        sa.Column("ece", sa.Float(), nullable=True),
        sa.Column("source", sa.Text(), nullable=True),
        sa.Column("provisional", sa.Boolean(), nullable=False),
        sa.Column("corroboration_weights", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("fit_utc", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_utc", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint(
            "assignment_calibration_id", name=op.f("pk_assignment_calibration")
        ),
    )
    op.create_index(
        op.f("ix_assignment_calibration_instrument"),
        "assignment_calibration",
        ["instrument"],
        unique=False,
    )
    op.create_index(
        op.f("ix_assignment_calibration_score_version"),
        "assignment_calibration",
        ["score_version"],
        unique=False,
    )
    op.create_index(
        op.f("ix_assignment_calibration_is_active"),
        "assignment_calibration",
        ["is_active"],
        unique=False,
    )
    op.create_index(
        "ix_assignment_calibration_active",
        "assignment_calibration",
        ["instrument", "score_version", "is_active"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_assignment_calibration_active", table_name="assignment_calibration"
    )
    op.drop_index(
        op.f("ix_assignment_calibration_is_active"),
        table_name="assignment_calibration",
    )
    op.drop_index(
        op.f("ix_assignment_calibration_score_version"),
        table_name="assignment_calibration",
    )
    op.drop_index(
        op.f("ix_assignment_calibration_instrument"),
        table_name="assignment_calibration",
    )
    op.drop_table("assignment_calibration")
