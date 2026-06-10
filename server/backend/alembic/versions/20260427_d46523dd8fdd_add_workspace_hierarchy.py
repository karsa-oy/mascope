# pylint: disable=no-member
"""Add workspace hierarchy: workspace, workspace_member.

Hierarchy: Workspace (ACL) -> Dataset -> Batch -> Sample

Adds:
- workspace: ACL boundary, groups datasets
- workspace_member: maps users to workspaces with roles
- dataset.workspace_id FK to workspace
- target_collection.workspace_id FK to workspace

Backfills existing data:
- Non-acquisition datasets → "Default Workspace" (system)
- Acquisition datasets → one system workspace per instrument, with year-based
  datasets replacing the former per-instrument acquisition datasets.

Revision ID: d46523dd8fdd
Revises: 8a57effe5414
Create Date: 2026-04-27 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from nanoid import generate

from mascope_backend.db.id import alphabet as NANOID_ALPHABET


# revision identifiers, used by Alembic.
revision: str = "d46523dd8fdd"
down_revision: Union[str, Sequence[str]] = "8a57effe5414"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _gen_id(length=16):
    return generate(NANOID_ALPHABET, length)


def upgrade() -> None:
    """Add workspace hierarchy tables and backfill."""

    # ===================================================================
    # 1. workspace (new ACL boundary table)
    # ===================================================================
    op.create_table(
        "workspace",
        sa.Column("workspace_id", sa.String(16), nullable=False),
        sa.Column("workspace_name", sa.String(256), nullable=False),
        sa.Column("workspace_description", sa.Text(), nullable=True),
        sa.Column(
            "workspace_status",
            sa.String(20),
            server_default=sa.text("'active'"),
            nullable=False,
        ),
        sa.Column(
            "is_system",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("workspace_utc_created", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("workspace_utc_modified", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("workspace_id", name=op.f("pk_workspace")),
    )
    op.create_index(
        "ix_workspace_name_ci",
        "workspace",
        [sa.literal_column("lower(workspace_name)")],
        unique=True,
    )

    # ===================================================================
    # 3. workspace_member
    # ===================================================================
    op.create_table(
        "workspace_member",
        sa.Column("workspace_member_id", sa.String(16), nullable=False),
        sa.Column("workspace_id", sa.String(16), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "workspace_role",
            sa.String(20),
            server_default=sa.text("'guest'"),
            nullable=False,
        ),
        sa.Column(
            "granted_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
        ),
        sa.Column("granted_by", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint(
            "workspace_member_id", name=op.f("pk_workspace_member")
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspace.workspace_id"],
            name=op.f("fk_workspace_member_workspace_id_workspace"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
            name=op.f("fk_workspace_member_user_id_user"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["granted_by"],
            ["user.id"],
            name=op.f("fk_workspace_member_granted_by_user"),
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint("workspace_id", "user_id", name="uq_workspace_member_pair"),
    )
    op.create_index(
        op.f("ix_workspace_member_workspace_id"),
        "workspace_member",
        ["workspace_id"],
    )
    op.create_index(
        op.f("ix_workspace_member_user_id"),
        "workspace_member",
        ["user_id"],
    )

    # ===================================================================
    # 4. Add workspace_id FK to dataset and backfill
    # ===================================================================

    # 4a. Add column as nullable first
    op.add_column(
        "dataset",
        sa.Column("workspace_id", sa.String(16), nullable=True),
    )

    # 4b. Create seed workspaces and assign datasets
    conn = op.get_bind()

    default_workspace_id = _gen_id()
    conn.execute(
        sa.text(
            "INSERT INTO workspace "
            "(workspace_id, workspace_name, workspace_description, "
            " workspace_status, is_system, workspace_utc_created, workspace_utc_modified) "
            "VALUES (:wid, :wname, :wdesc, 'active', true, NOW(), NOW())"
        ).bindparams(
            wid=default_workspace_id,
            wname="System Workspace",
            wdesc="Workspace for pre-existing datasets. Cannot be deleted.",
        )
    )

    # --- Per-instrument acquisition workspaces ---
    # Collect all instruments that have acquisition datasets
    acq_instruments = conn.execute(
        sa.text(
            "SELECT DISTINCT instrument FROM dataset "
            "WHERE dataset_type = 'ACQUISITION' AND instrument IS NOT NULL"
        )
    ).fetchall()

    # Global role_id mapping: 100=guest, 200=editor, 300=admin, 400=owner
    ROLE_MAP = {100: "guest", 200: "editor", 300: "admin", 400: "owner"}
    users = conn.execute(sa.text('SELECT id, role_id FROM "user"')).fetchall()

    # Track all workspace IDs for user membership seeding
    all_workspace_ids = [default_workspace_id]

    for (instrument,) in acq_instruments:
        instr_ws_id = _gen_id()
        all_workspace_ids.append(instr_ws_id)

        conn.execute(
            sa.text(
                "INSERT INTO workspace "
                "(workspace_id, workspace_name, workspace_description, "
                " workspace_status, is_system, workspace_utc_created, workspace_utc_modified) "
                "VALUES (:wid, :wname, :wdesc, 'active', true, NOW(), NOW())"
            ).bindparams(
                wid=instr_ws_id,
                wname=f"Acquisitions {instrument}",
                wdesc=f"System workspace for {instrument} acquisitions",
            )
        )

        # Restructure: split the per-instrument dataset into year-based datasets.
        # Extract years from batch names (format: "YYYY-MM-DD <mode> acquisition").
        # We use the batch name rather than sample_batch_utc_created because
        # retrospectively processed data would have a creation timestamp that
        # doesn't match the actual acquisition date.
        year_rows = conn.execute(
            sa.text(
                "SELECT DISTINCT SUBSTRING(sb.sample_batch_name FROM '^(\\d{4})')::int AS yr "
                "FROM sample_batch sb "
                "JOIN dataset d ON d.dataset_id = sb.dataset_id "
                "WHERE d.dataset_type = 'ACQUISITION' AND d.instrument = :instr "
                "  AND sb.sample_batch_name ~ '^\\d{4}-' "
                "ORDER BY yr"
            ).bindparams(instr=instrument)
        ).fetchall()

        if not year_rows:
            # Dataset exists but has no batches — just reassign it as
            # the current-year dataset under the instrument workspace.
            conn.execute(
                sa.text(
                    "UPDATE dataset SET workspace_id = :wid, "
                    "  dataset_name = :dname, "
                    "  dataset_description = :ddesc "
                    "WHERE dataset_type = 'ACQUISITION' AND instrument = :instr"
                ).bindparams(
                    wid=instr_ws_id,
                    dname="2026",
                    ddesc=f"2026 acquisitions for {instrument}",
                    instr=instrument,
                )
            )
        else:
            years = [row[0] for row in year_rows]

            # Get the original dataset ID
            orig_dataset_id = conn.execute(
                sa.text(
                    "SELECT dataset_id FROM dataset "
                    "WHERE dataset_type = 'ACQUISITION' AND instrument = :instr "
                    "LIMIT 1"
                ).bindparams(instr=instrument)
            ).scalar_one()

            # Repurpose the original dataset for the first year
            first_year = years[0]
            conn.execute(
                sa.text(
                    "UPDATE dataset SET workspace_id = :wid, "
                    "  dataset_name = :dname, "
                    "  dataset_description = :ddesc "
                    "WHERE dataset_id = :did"
                ).bindparams(
                    wid=instr_ws_id,
                    dname=str(first_year),
                    ddesc=f"{first_year} acquisitions for {instrument}",
                    did=orig_dataset_id,
                )
            )

            # For each additional year, create a new dataset and move batches
            for year in years[1:]:
                new_dataset_id = _gen_id()
                conn.execute(
                    sa.text(
                        "INSERT INTO dataset "
                        "(dataset_id, workspace_id, dataset_name, dataset_description, "
                        " dataset_type, instrument, locked, dataset_utc_created) "
                        "VALUES (:did, :wid, :dname, :ddesc, 'ACQUISITION', :instr, 1, NOW())"
                    ).bindparams(
                        did=new_dataset_id,
                        wid=instr_ws_id,
                        dname=str(year),
                        ddesc=f"{year} acquisitions for {instrument}",
                        instr=instrument,
                    )
                )
                # Move batches from original dataset to new year dataset
                conn.execute(
                    sa.text(
                        "UPDATE sample_batch SET dataset_id = :new_did "
                        "WHERE dataset_id = :orig_did "
                        "AND SUBSTRING(sample_batch_name FROM '^(\\d{4})')::int = :yr"
                    ).bindparams(
                        new_did=new_dataset_id, orig_did=orig_dataset_id, yr=year
                    )
                )

    # Assign all remaining datasets (non-acquisition) to default workspace
    conn.execute(
        sa.text(
            "UPDATE dataset SET workspace_id = :wid WHERE workspace_id IS NULL"
        ).bindparams(wid=default_workspace_id)
    )

    # Add all existing users to all workspaces, mapping global role
    for user_id, role_id in users:
        ws_role = ROLE_MAP.get(role_id, "guest")
        for wid in all_workspace_ids:
            conn.execute(
                sa.text(
                    "INSERT INTO workspace_member "
                    "(workspace_member_id, workspace_id, user_id, workspace_role, granted_at) "
                    "VALUES (:mid, :wid, :uid, :role, NOW())"
                ).bindparams(mid=_gen_id(), wid=wid, uid=user_id, role=ws_role)
            )

    # 4c. Make workspace_id NOT NULL and add FK + index
    op.alter_column("dataset", "workspace_id", nullable=False)
    op.create_foreign_key(
        op.f("fk_dataset_workspace_id_workspace"),
        "dataset",
        "workspace",
        ["workspace_id"],
        ["workspace_id"],
        ondelete="CASCADE",
    )
    op.create_index(
        op.f("ix_dataset_workspace_id"),
        "dataset",
        ["workspace_id"],
    )

    # ===================================================================
    # 5. Add nullable workspace_id to target_collection
    # ===================================================================
    op.add_column(
        "target_collection",
        sa.Column("workspace_id", sa.String(16), nullable=True),
    )
    op.create_foreign_key(
        op.f("fk_target_collection_workspace_id_workspace"),
        "target_collection",
        "workspace",
        ["workspace_id"],
        ["workspace_id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_target_collection_workspace_id"),
        "target_collection",
        ["workspace_id"],
    )


def downgrade() -> None:
    """Remove workspace hierarchy tables."""

    # Remove FK and column from target_collection
    op.drop_constraint(
        op.f("fk_target_collection_workspace_id_workspace"),
        "target_collection",
        type_="foreignkey",
    )
    op.drop_index(
        op.f("ix_target_collection_workspace_id"), table_name="target_collection"
    )
    op.drop_column("target_collection", "workspace_id")

    # Remove FK and column from dataset
    op.drop_constraint(
        op.f("fk_dataset_workspace_id_workspace"), "dataset", type_="foreignkey"
    )
    op.drop_index(op.f("ix_dataset_workspace_id"), table_name="dataset")
    op.drop_column("dataset", "workspace_id")

    # Drop new tables in reverse dependency order
    op.drop_table("workspace_member")
    op.drop_table("workspace")
