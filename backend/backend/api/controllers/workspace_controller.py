from fastapi import HTTPException
from sqlalchemy import asc, desc, func
from sqlalchemy.future import select
from datetime import datetime

from backend.db import async_session
from backend.api_sio import sio
from backend.db.id import gen_id
from ..models.models import Workspace
from ..models.pydantic_models.workspace_pydantic_model import (
    WorkspaceCreate,
    WorkspaceUpdate,
)


async def get_workspaces(sort: str, order: str, page: int, limit: int):
    async with async_session() as session:
        stmt = select(Workspace)

        if sort:
            if order == "desc":
                stmt = stmt.order_by(desc(getattr(Workspace, sort)))
            else:
                stmt = stmt.order_by(asc(getattr(Workspace, sort)))

        # Get total count
        count_stmt = select(func.count()).select_from(stmt)
        total = await session.scalar(count_stmt)

        # Get paginated results
        stmt = stmt.offset(page * limit).limit(limit)
        result = await session.execute(stmt)
        workspaces = result.scalars().all()

        return {
            "results": total,
            "data": [workspace.to_dict() for workspace in workspaces],
        }


async def get_workspace(workspace_id: str):
    async with async_session() as session:
        stmt = select(Workspace).filter(Workspace.workspace_id == workspace_id)
        result = await session.execute(stmt)
        workspace = result.scalars().first()

        if not workspace:
            raise HTTPException(
                status_code=404,
                detail=f"Workspace with ID {workspace_id} not found",
            )

        return workspace.to_dict()


async def create_workspace(workspace: WorkspaceCreate):
    async with async_session() as session:
        new_workspace = Workspace(
            workspace_id=gen_id(16),
            workspace_name=workspace.workspace_name,
            workspace_description=workspace.workspace_description,
            workspace_utc_created=datetime.utcnow(),
        )
        session.add(new_workspace)
        await session.commit()
        await session.refresh(new_workspace)
        # emit the event to inform the clients about the new workspace
        await sio.emit("org_reload", namespace="/")
        return new_workspace


async def update_workspace(workspace_id: str, workspace: WorkspaceUpdate):
    async with async_session() as session:
        existing_workspace = await session.get(Workspace, workspace_id)
        if not existing_workspace:
            raise HTTPException(status_code=404, detail="Workspace not found")

        update_data = workspace.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(existing_workspace, key, value)

        existing_workspace.workspace_utc_modified = datetime.utcnow()
        await session.commit()
        # emit the event to inform the clients about changes in the workspace
        await sio.emit("org_reload", namespace="/")
        await sio.emit("workspace_reload", room=workspace_id, namespace="/")
        return existing_workspace


async def delete_workspace(workspace_id: str):
    async with async_session() as session:
        result = await session.execute(
            select(Workspace).filter(Workspace.workspace_id == workspace_id)
        )
        workspace = result.scalar_one_or_none()
        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found")

        await session.delete(workspace)
        await session.commit()
        # emit the event to inform the clients about deletion of the workspace
        await sio.emit("org_reload", namespace="/")
        await sio.emit("workspace_reload", room=workspace_id, namespace="/")
