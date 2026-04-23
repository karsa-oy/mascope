# pylint: disable=no-member
"""Rename workspace table and columns to dataset.

The entity previously called "workspace" is now called "dataset".
This migration renames the table and all workspace_* columns to dataset_*.
Also updates existing workspace_description text to replace "workspace" with "dataset"
(case-insensitive).

Revision ID: 8a57effe5414
Revises: be6a2a093ade
Create Date: 2026-04-23 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "8a57effe5414"
down_revision: Union[str, Sequence[str]] = "be6a2a093ade"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rename workspace table/columns to dataset."""

    # Drop FK from sample_batch -> workspace first
    op.drop_constraint(
        "fk_sample_batch_workspace_id_workspace", "sample_batch", type_="foreignkey"
    )

    # Rename the table
    op.rename_table("workspace", "dataset")

    # Rename columns: workspace_* -> dataset_*
    op.alter_column("dataset", "workspace_id", new_column_name="dataset_id")
    op.alter_column("dataset", "workspace_name", new_column_name="dataset_name")
    op.alter_column(
        "dataset", "workspace_description", new_column_name="dataset_description"
    )
    op.alter_column("dataset", "workspace_type", new_column_name="dataset_type")
    op.alter_column(
        "dataset", "workspace_utc_created", new_column_name="dataset_utc_created"
    )
    op.alter_column(
        "dataset", "workspace_utc_modified", new_column_name="dataset_utc_modified"
    )

    # Rename the PK constraint
    op.execute(
        sa.text('ALTER TABLE dataset RENAME CONSTRAINT "pk_workspace" TO "pk_dataset"')
    )

    # Rename sample_batch column and re-create FK to dataset
    op.alter_column("sample_batch", "workspace_id", new_column_name="dataset_id")
    op.create_foreign_key(
        op.f("fk_sample_batch_dataset_id_dataset"),
        "sample_batch",
        "dataset",
        ["dataset_id"],
        ["dataset_id"],
        ondelete="CASCADE",
    )

    # Update description text: replace "workspace" → "dataset" (preserving case)
    op.execute(
        sa.text(
            "UPDATE dataset "
            "SET dataset_description = REPLACE("
            "    REPLACE(dataset_description, 'Workspace', 'Dataset'),"
            "    'workspace', 'dataset'"
            ") "
            "WHERE dataset_description LIKE '%workspace%'"
            "   OR dataset_description LIKE '%Workspace%'"
        )
    )


def downgrade() -> None:
    """Revert dataset back to workspace."""

    # Revert description text: replace "dataset" → "workspace" (preserving case)
    op.execute(
        sa.text(
            "UPDATE dataset "
            "SET dataset_description = REPLACE("
            "    REPLACE(dataset_description, 'Dataset', 'Workspace'),"
            "    'dataset', 'workspace'"
            ") "
            "WHERE dataset_description LIKE '%dataset%'"
            "   OR dataset_description LIKE '%Dataset%'"
        )
    )

    # Drop FK from sample_batch -> dataset
    op.drop_constraint(
        op.f("fk_sample_batch_dataset_id_dataset"), "sample_batch", type_="foreignkey"
    )
    op.alter_column("sample_batch", "dataset_id", new_column_name="workspace_id")

    # Rename PK constraint back
    op.execute(
        sa.text('ALTER TABLE dataset RENAME CONSTRAINT "pk_dataset" TO "pk_workspace"')
    )

    # Rename columns back: dataset_* -> workspace_*
    op.alter_column(
        "dataset", "dataset_utc_modified", new_column_name="workspace_utc_modified"
    )
    op.alter_column(
        "dataset", "dataset_utc_created", new_column_name="workspace_utc_created"
    )
    op.alter_column("dataset", "dataset_type", new_column_name="workspace_type")
    op.alter_column(
        "dataset", "dataset_description", new_column_name="workspace_description"
    )
    op.alter_column("dataset", "dataset_name", new_column_name="workspace_name")
    op.alter_column("dataset", "dataset_id", new_column_name="workspace_id")

    # Rename table back
    op.rename_table("dataset", "workspace")

    # Re-create FK from sample_batch -> workspace
    op.create_foreign_key(
        "fk_sample_batch_workspace_id_workspace",
        "sample_batch",
        "workspace",
        ["workspace_id"],
        ["workspace_id"],
        ondelete="CASCADE",
    )
