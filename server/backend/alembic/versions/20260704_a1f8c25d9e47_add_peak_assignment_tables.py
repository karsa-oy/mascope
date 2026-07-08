"""Add peak assignment tables

Introduces the peak-centric assignment persistence layer:

- peak_assignment_run: one row per assignment run over a sample, storing the
  engine version and full configuration for reproducibility.
- peak_assignment: one row per observed sample peak in a run, carrying the
  committed formula, adduct, evidence, confidence tier, and optional
  references back to the curated target library. Peak identity follows the
  MatchIsotope pattern (sample_item_id FK + sample_peak_id string, with
  denormalized mz/intensity/tof); raw peaks stay in files.

The unique constraint on (peak_assignment_run_id, sample_peak_id) enforces
the single-owner-per-peak invariant within a run.

Revision ID: a1f8c25d9e47
Revises: c4f7a2e9b1d8
Create Date: 2026-07-04 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "a1f8c25d9e47"
down_revision: Union[str, Sequence[str], None] = "c4f7a2e9b1d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "peak_assignment_run",
        sa.Column("peak_assignment_run_id", sa.String(length=16), nullable=False),
        sa.Column("sample_item_id", sa.String(length=16), nullable=False),
        sa.Column("engine_version", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column("config", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "peak_assignment_run_utc_created",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "peak_assignment_run_utc_completed",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["sample_item_id"],
            ["sample_item.sample_item_id"],
            name=op.f("fk_peak_assignment_run_sample_item_id_sample_item"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "peak_assignment_run_id", name=op.f("pk_peak_assignment_run")
        ),
    )
    op.create_index(
        op.f("ix_peak_assignment_run_sample_item_id"),
        "peak_assignment_run",
        ["sample_item_id"],
        unique=False,
    )
    op.create_table(
        "peak_assignment",
        sa.Column("peak_assignment_id", sa.String(length=32), nullable=False),
        sa.Column("peak_assignment_run_id", sa.String(length=16), nullable=False),
        sa.Column("sample_item_id", sa.String(length=16), nullable=False),
        sa.Column("sample_peak_id", sa.String(length=20), nullable=False),
        sa.Column("sample_peak_mz", sa.Float(), nullable=False),
        sa.Column("sample_peak_intensity", sa.Float(), nullable=False),
        sa.Column("sample_peak_tof", sa.Float(), nullable=True),
        sa.Column(
            "role",
            sa.String(length=16),
            server_default=sa.text("'unassigned'"),
            nullable=False,
        ),
        sa.Column("assigned_formula", sa.String(length=256), nullable=True),
        sa.Column("ion_formula", sa.String(length=4096), nullable=True),
        sa.Column("ionization_mechanism_id", sa.String(length=16), nullable=True),
        sa.Column("isotope_label", sa.String(length=64), nullable=True),
        sa.Column("isotope_formula", sa.String(length=256), nullable=True),
        sa.Column("source", sa.String(length=16), nullable=True),
        sa.Column("match_score", sa.Float(), nullable=True),
        sa.Column("mz_error_ppm", sa.Float(), nullable=True),
        sa.Column("abundance_error", sa.Float(), nullable=True),
        sa.Column(
            "tier",
            sa.String(length=24),
            server_default=sa.text("'unassigned'"),
            nullable=False,
        ),
        sa.Column("target_compound_id", sa.String(length=16), nullable=True),
        sa.Column("target_ion_id", sa.String(length=16), nullable=True),
        sa.Column("owner_peak_assignment_id", sa.String(length=32), nullable=True),
        sa.Column("alternatives", sa.JSON(), nullable=True),
        sa.Column("provenance", sa.JSON(), nullable=True),
        sa.CheckConstraint(
            "match_score IS NULL OR match_score BETWEEN 0 AND 1",
            name=op.f("ck_peak_assignment_match_score_range"),
        ),
        sa.ForeignKeyConstraint(
            ["ionization_mechanism_id"],
            ["ionization_mechanism.ionization_mechanism_id"],
            name=op.f(
                "fk_peak_assignment_ionization_mechanism_id_ionization_mechanism"
            ),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["owner_peak_assignment_id"],
            ["peak_assignment.peak_assignment_id"],
            name=op.f("fk_peak_assignment_owner_peak_assignment_id_peak_assignment"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["peak_assignment_run_id"],
            ["peak_assignment_run.peak_assignment_run_id"],
            name=op.f("fk_peak_assignment_peak_assignment_run_id_peak_assignment_run"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["sample_item_id"],
            ["sample_item.sample_item_id"],
            name=op.f("fk_peak_assignment_sample_item_id_sample_item"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_compound_id"],
            ["target_compound.target_compound_id"],
            name=op.f("fk_peak_assignment_target_compound_id_target_compound"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["target_ion_id"],
            ["target_ion.target_ion_id"],
            name=op.f("fk_peak_assignment_target_ion_id_target_ion"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("peak_assignment_id", name=op.f("pk_peak_assignment")),
        sa.UniqueConstraint(
            "peak_assignment_run_id",
            "sample_peak_id",
            name="uq_peak_assignment_run_id_sample_peak_id",
        ),
    )
    op.create_index(
        op.f("ix_peak_assignment_peak_assignment_run_id"),
        "peak_assignment",
        ["peak_assignment_run_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_peak_assignment_sample_item_id"),
        "peak_assignment",
        ["sample_item_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_peak_assignment_sample_peak_id"),
        "peak_assignment",
        ["sample_peak_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_peak_assignment_target_compound_id"),
        "peak_assignment",
        ["target_compound_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_peak_assignment_target_ion_id"),
        "peak_assignment",
        ["target_ion_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_peak_assignment_ionization_mechanism_id"),
        "peak_assignment",
        ["ionization_mechanism_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_peak_assignment_owner_peak_assignment_id"),
        "peak_assignment",
        ["owner_peak_assignment_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_peak_assignment_owner_peak_assignment_id"),
        table_name="peak_assignment",
    )
    op.drop_index(
        op.f("ix_peak_assignment_ionization_mechanism_id"),
        table_name="peak_assignment",
    )
    op.drop_index(
        op.f("ix_peak_assignment_target_ion_id"), table_name="peak_assignment"
    )
    op.drop_index(
        op.f("ix_peak_assignment_target_compound_id"), table_name="peak_assignment"
    )
    op.drop_index(
        op.f("ix_peak_assignment_sample_peak_id"), table_name="peak_assignment"
    )
    op.drop_index(
        op.f("ix_peak_assignment_sample_item_id"), table_name="peak_assignment"
    )
    op.drop_index(
        op.f("ix_peak_assignment_peak_assignment_run_id"),
        table_name="peak_assignment",
    )
    op.drop_table("peak_assignment")
    op.drop_index(
        op.f("ix_peak_assignment_run_sample_item_id"),
        table_name="peak_assignment_run",
    )
    op.drop_table("peak_assignment_run")
