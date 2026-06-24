"""
Fixtures for dataset integration tests.

Provides a test workspace with all test users added as members,
so that workspace-scoped dataset routes pass ACL checks.
"""

from datetime import datetime, timezone

import pytest_asyncio

from mascope_backend.db import Workspace, WorkspaceMember
from mascope_backend.db.id import gen_id


@pytest_asyncio.fixture(scope="session")
async def test_workspace(async_session_factory, test_users):
    """Create a workspace and add all test users as members.

    - owner  → workspace role "owner"
    - admin  → workspace role "admin"
    - editor → workspace role "editor"
    - guest  → workspace role "guest"

    Returns the workspace_id string, which tests embed in URL paths.
    """
    workspace_id = gen_id()
    now = datetime.now(timezone.utc)

    async with async_session_factory() as session:
        workspace = Workspace(
            workspace_id=workspace_id,
            workspace_name="Test Workspace",
            workspace_description="Workspace for integration tests",
            workspace_status="active",
            workspace_utc_created=now,
            workspace_utc_modified=now,
        )
        session.add(workspace)

        for role_name, user in test_users.items():
            member = WorkspaceMember(
                workspace_member_id=gen_id(),
                workspace_id=workspace_id,
                user_id=user.id,
                workspace_role=role_name,
                granted_at=now,
                granted_by=user.id,
            )
            session.add(member)

        await session.commit()

    return workspace_id
