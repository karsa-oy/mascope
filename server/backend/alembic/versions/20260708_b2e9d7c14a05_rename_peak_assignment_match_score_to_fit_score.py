"""Rename peak_assignment.match_score to fit_score

The peak-centric assignment score is the *fit score* (mascope_tools
score_pattern_v2): a measurement of how well the observed data fit an
assignment's predicted pattern, not an identification probability. Rename the
column to say so plainly, and rename its range check constraint to match.

Scope: the new peak_assignment table only. The legacy match_ion / match_isotope
match_score columns are a separate surface and are left untouched.

Reversible: the downgrade renames fit_score back to match_score and restores the
original constraint name.

Revision ID: b2e9d7c14a05
Revises: a1f8c25d9e47
Create Date: 2026-07-08 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b2e9d7c14a05"
down_revision: Union[str, Sequence[str], None] = "a1f8c25d9e47"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # The check constraint references the column, so drop it first, rename the
    # column, then recreate the constraint under its new (fit_score) name.
    op.drop_constraint(
        op.f("ck_peak_assignment_match_score_range"),
        "peak_assignment",
        type_="check",
    )
    op.alter_column(
        "peak_assignment",
        "match_score",
        new_column_name="fit_score",
    )
    op.create_check_constraint(
        op.f("ck_peak_assignment_fit_score_range"),
        "peak_assignment",
        "fit_score IS NULL OR fit_score BETWEEN 0 AND 1",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck_peak_assignment_fit_score_range"),
        "peak_assignment",
        type_="check",
    )
    op.alter_column(
        "peak_assignment",
        "fit_score",
        new_column_name="match_score",
    )
    op.create_check_constraint(
        op.f("ck_peak_assignment_match_score_range"),
        "peak_assignment",
        "match_score IS NULL OR match_score BETWEEN 0 AND 1",
    )
