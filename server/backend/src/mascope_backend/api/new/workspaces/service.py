"""
Workspace CRUD service module.

Provides core CRUD operations for workspaces and workspace membership.
"""

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import asc, select

from mascope_backend.api.lib.api_features import api_controller
from mascope_backend.api.lib.exceptions.api_exceptions import NotFoundException
from mascope_backend.api.new.workspaces.exceptions import (
    WorkspaceMemberAlreadyExistsException,
    WorkspaceMemberNotFoundException,
    WorkspaceNotFoundException,
)
from mascope_backend.db import User, Workspace, WorkspaceMember, async_session
from mascope_backend.db.id import gen_id


# ---------------------------------------------------------------------------
# Workspace CRUD
# ---------------------------------------------------------------------------


@api_controller()
async def get_workspaces(
    workspace_status: str | None = None,
    user_id: int | None = None,
) -> dict:
    """List workspaces, optionally filtered by status or user membership."""
    async with async_session() as session:
        query = select(Workspace)

        if workspace_status:
            query = query.where(Workspace.workspace_status == workspace_status)
        if user_id is not None:
            query = query.join(WorkspaceMember).where(
                WorkspaceMember.user_id == user_id
            )

        query = query.order_by(asc(Workspace.workspace_name))
        result = await session.execute(query)
        workspaces = result.scalars().all()

        return {
            "data": [p.to_dict() for p in workspaces],
            "total": len(workspaces),
        }


@api_controller()
async def get_workspace(workspace_id: str) -> dict:
    """Get a single workspace by ID."""
    async with async_session() as session:
        result = await session.execute(
            select(Workspace).where(Workspace.workspace_id == workspace_id)
        )
        workspace = result.scalar_one_or_none()
        if workspace is None:
            raise WorkspaceNotFoundException(workspace_id)
        return {"data": workspace.to_dict()}


@api_controller()
async def create_workspace(
    workspace_name: str,
    workspace_description: str | None = None,
    creator_user_id: int | None = None,
) -> dict:
    """Create a new workspace and add the creator as owner."""
    now = datetime.now(timezone.utc)
    workspace_id = gen_id()

    async with async_session() as session:
        workspace = Workspace(
            workspace_id=workspace_id,
            workspace_name=workspace_name,
            workspace_description=workspace_description,
            workspace_status="active",
            workspace_utc_created=now,
            workspace_utc_modified=now,
        )
        session.add(workspace)

        # Auto-add the creating user as workspace owner
        if creator_user_id is not None:
            member = WorkspaceMember(
                workspace_member_id=gen_id(),
                workspace_id=workspace_id,
                user_id=creator_user_id,
                workspace_role="owner",
                granted_at=now,
                granted_by=creator_user_id,
            )
            session.add(member)

        await session.commit()
        return {"data": workspace.to_dict()}


@api_controller()
async def update_workspace(
    workspace_id: str,
    workspace_name: str | None = None,
    workspace_description: str | None = None,
    workspace_status: str | None = None,
) -> dict:
    """Update a workspace's metadata."""
    async with async_session() as session:
        result = await session.execute(
            select(Workspace).where(Workspace.workspace_id == workspace_id)
        )
        workspace = result.scalar_one_or_none()
        if workspace is None:
            raise WorkspaceNotFoundException(workspace_id)

        if workspace.is_system:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="System workspaces cannot be modified.",
            )

        if workspace_name is not None:
            workspace.workspace_name = workspace_name
        if workspace_description is not None:
            workspace.workspace_description = workspace_description
        if workspace_status is not None:
            workspace.workspace_status = workspace_status

        workspace.workspace_utc_modified = datetime.now(timezone.utc)
        await session.commit()
        return {"data": workspace.to_dict()}


@api_controller()
async def delete_workspace(workspace_id: str) -> dict:
    """Delete a workspace and all its workspaces (cascading)."""
    async with async_session() as session:
        result = await session.execute(
            select(Workspace).where(Workspace.workspace_id == workspace_id)
        )
        workspace = result.scalar_one_or_none()
        if workspace is None:
            raise WorkspaceNotFoundException(workspace_id)

        if workspace.is_system:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="System workspaces cannot be deleted.",
            )

        await session.delete(workspace)
        await session.commit()
        return {"data": {"workspace_id": workspace_id, "deleted": True}}


# ---------------------------------------------------------------------------
# Workspace membership
# ---------------------------------------------------------------------------


@api_controller()
async def get_workspace_members(workspace_id: str) -> dict:
    """List all members of a workspace."""
    async with async_session() as session:
        result = await session.execute(
            select(WorkspaceMember).where(WorkspaceMember.workspace_id == workspace_id)
        )
        members = result.scalars().all()
        return {
            "data": [m.to_dict() for m in members],
            "total": len(members),
        }


@api_controller()
async def add_workspace_member(
    workspace_id: str,
    user_id: int,
    workspace_role: str = "guest",
    granted_by: int | None = None,
) -> dict:
    """Add a user to a workspace with a given role."""
    async with async_session() as session:
        # Validate workspace exists
        workspace = await session.get(Workspace, workspace_id)
        if workspace is None:
            raise WorkspaceNotFoundException(workspace_id)

        # Validate user exists
        user = await session.get(User, user_id)
        if user is None:
            raise NotFoundException(f"User with ID '{user_id}' not found.")

        # Check if already a member — reject duplicate
        result = await session.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
            )
        )
        if result.scalar_one_or_none() is not None:
            raise WorkspaceMemberAlreadyExistsException(workspace_id, user_id)

        member = WorkspaceMember(
            workspace_member_id=gen_id(),
            workspace_id=workspace_id,
            user_id=user_id,
            workspace_role=workspace_role,
            granted_at=datetime.now(timezone.utc),
            granted_by=granted_by,
        )
        session.add(member)
        await session.commit()
        return {"data": member.to_dict()}


@api_controller()
async def update_workspace_member(
    workspace_id: str,
    user_id: int,
    workspace_role: str,
) -> dict:
    """Update a member's role in a workspace."""
    async with async_session() as session:
        result = await session.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
            )
        )
        member = result.scalar_one_or_none()
        if member is None:
            raise WorkspaceMemberNotFoundException(
                f"User {user_id} is not a member of workspace {workspace_id}."
            )
        member.workspace_role = workspace_role
        await session.commit()
        return {"data": member.to_dict()}


@api_controller()
async def remove_workspace_member(workspace_id: str, user_id: int) -> dict:
    """Remove a user from a workspace."""
    async with async_session() as session:
        result = await session.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
            )
        )
        member = result.scalar_one_or_none()
        if member is None:
            raise WorkspaceMemberNotFoundException(
                f"User {user_id} is not a member of workspace {workspace_id}."
            )
        await session.delete(member)
        await session.commit()
        return {
            "data": {"workspace_id": workspace_id, "user_id": user_id, "removed": True}
        }
