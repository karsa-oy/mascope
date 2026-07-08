"""Add assignment_verification (verification-calibration loop V1)

Adds the assignment_verification table: a user's confirm/reject/unsure verdict on a
peak-centric assignment, with the evidence level and a score snapshot, as the labelled
source for refitting the confidence calibration later. Append-only; keyed to the stable
identity (sample + observed peak + formula/adduct) so labels survive re-runs, with the
run-scoped assignment row as SET NULL provenance. Schema only - no data seeded, no
calibration wired (that is V2).

Revision ID: e4f2a7c9d3b1
Revises: d1a2c3b4e5f6
Create Date: 2026-07-09 15:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "e4f2a7c9d3b1"
down_revision: Union[str, Sequence[str], None] = "d1a2c3b4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "assignment_verification",
        sa.Column("assignment_verification_id", sa.String(length=32), nullable=False),
        sa.Column("sample_item_id", sa.String(length=16), nullable=False),
        sa.Column("peak_assignment_id", sa.String(length=32), nullable=True),
        sa.Column("peak_assignment_run_id", sa.String(length=16), nullable=True),
        sa.Column("sample_peak_id", sa.String(length=20), nullable=False),
        sa.Column("assigned_formula", sa.String(length=256), nullable=True),
        sa.Column("ionization_mechanism_id", sa.String(length=16), nullable=True),
        sa.Column("verdict", sa.String(length=16), nullable=False),
        sa.Column("evidence_level", sa.String(length=24), nullable=True),
        sa.Column("fit_score", sa.Float(), nullable=True),
        sa.Column("evidence", sa.Float(), nullable=True),
        sa.Column("p_correct", sa.Float(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("context", sa.JSON(), nullable=True),
        sa.Column("verified_by", sa.Integer(), nullable=True),
        sa.Column("verified_utc", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.CheckConstraint(
            "verdict IN ('confirmed', 'rejected', 'unsure')",
            name=op.f("ck_assignment_verification_verdict_valid"),
        ),
        sa.CheckConstraint(
            "evidence_level IS NULL OR evidence_level IN "
            "('reference_standard', 'msms', 'orthogonal', 'pattern', 'visual')",
            name=op.f("ck_assignment_verification_evidence_level_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["sample_item_id"],
            ["sample_item.sample_item_id"],
            name=op.f("fk_assignment_verification_sample_item_id_sample_item"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["peak_assignment_id"],
            ["peak_assignment.peak_assignment_id"],
            name=op.f(
                "fk_assignment_verification_peak_assignment_id_peak_assignment"
            ),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["verified_by"],
            ["user.id"],
            name=op.f("fk_assignment_verification_verified_by_user"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint(
            "assignment_verification_id",
            name=op.f("pk_assignment_verification"),
        ),
    )
    op.create_index(
        op.f("ix_assignment_verification_sample_item_id"),
        "assignment_verification",
        ["sample_item_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_assignment_verification_peak_assignment_id"),
        "assignment_verification",
        ["peak_assignment_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_assignment_verification_sample_peak_id"),
        "assignment_verification",
        ["sample_peak_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_assignment_verification_verified_by"),
        "assignment_verification",
        ["verified_by"],
        unique=False,
    )
    op.create_index(
        "ix_assignment_verification_identity",
        "assignment_verification",
        ["sample_item_id", "sample_peak_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_assignment_verification_identity",
        table_name="assignment_verification",
    )
    op.drop_index(
        op.f("ix_assignment_verification_verified_by"),
        table_name="assignment_verification",
    )
    op.drop_index(
        op.f("ix_assignment_verification_sample_peak_id"),
        table_name="assignment_verification",
    )
    op.drop_index(
        op.f("ix_assignment_verification_peak_assignment_id"),
        table_name="assignment_verification",
    )
    op.drop_index(
        op.f("ix_assignment_verification_sample_item_id"),
        table_name="assignment_verification",
    )
    op.drop_table("assignment_verification")
