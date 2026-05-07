"""
Workspace-level access control dependencies.

These can be used in route definitions to enforce workspace membership checks
at the endpoint level, complementing the global RBAC in auth/dependencies.py.

**FastAPI dependency factories** (inject via ``Depends(...)``):

- ``require_workspace_role``:  resolves ``workspace_id`` **path** param
- ``require_dataset_role``:    resolves ``dataset_id`` **path** param → workspace
- ``require_dataset_query_role``: resolves ``dataset_id`` **query** param → workspace
- ``require_batch_role``:      resolves ``sample_batch_id`` **path** param → workspace
- ``require_sample_role``:       resolves ``sample_item_id`` **path** param → workspace
- ``require_acquisition_workspace_role``: resolves system Acquisitions workspace

**Explicit check functions** (call in route handler body):

- ``check_dataset_access``:   dataset_id from request body / other source
- ``check_batch_access``:     sample_batch_id from request body / other source
- ``check_batch_access_bulk``:  list of sample_batch_ids (single query)
- ``check_sample_access``:      sample_item_id from request body / other source
- ``check_sample_access_bulk``: list of sample_item_ids (single query)

All return ``WorkspaceMember`` on success or raise ``ForbiddenAccessException``.
"""

from fastapi import Depends, Path, Query
from sqlalchemy import select

from mascope_backend.api.new.auth.config import auth_settings
from mascope_backend.api.new.auth.dependencies import current_active_user
from mascope_backend.api.new.auth.exceptions import ForbiddenAccessException
from mascope_backend.db import (
    Dataset,
    SampleBatch,
    SampleItem,
    User,
    Workspace,
    WorkspaceMember,
    async_session,
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_role_levels = auth_settings.ROLE_ACCESS_LEVELS


async def _get_workspace_membership(
    workspace_id: str, user: User
) -> WorkspaceMember | None:
    """Fetch the user's membership record for a workspace."""
    async with async_session() as session:
        result = await session.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user.id,
            )
        )
        return result.scalar_one_or_none()


async def _get_workspace_id_from_dataset(dataset_id: str) -> str | None:
    """Resolve dataset_id to workspace_id."""
    async with async_session() as session:
        result = await session.execute(
            select(Dataset.workspace_id).where(Dataset.dataset_id == dataset_id)
        )
        return result.scalar_one_or_none()


async def _get_workspace_id_from_batch(sample_batch_id: str) -> str | None:
    """Resolve sample_batch_id → dataset_id → workspace_id."""
    async with async_session() as session:
        result = await session.execute(
            select(Dataset.workspace_id)
            .join(SampleBatch, SampleBatch.dataset_id == Dataset.dataset_id)
            .where(SampleBatch.sample_batch_id == sample_batch_id)
        )
        return result.scalar_one_or_none()


async def _get_workspace_id_from_sample(sample_item_id: str) -> str | None:
    """Resolve sample_item_id → sample_batch_id → dataset_id → workspace_id."""
    async with async_session() as session:
        result = await session.execute(
            select(Dataset.workspace_id)
            .join(SampleBatch, SampleBatch.dataset_id == Dataset.dataset_id)
            .join(SampleItem, SampleItem.sample_batch_id == SampleBatch.sample_batch_id)
            .where(SampleItem.sample_item_id == sample_item_id)
        )
        return result.scalar_one_or_none()


async def _get_acquisition_workspace_id() -> str | None:
    """Resolve the system workspace that holds ACQUISITION datasets."""
    async with async_session() as session:
        result = await session.execute(
            select(Workspace.workspace_id).where(
                Workspace.workspace_name == "Acquisitions",
                Workspace.is_system.is_(True),
            )
        )
        return result.scalar_one_or_none()


async def _get_workspace_ids_from_batches(
    sample_batch_ids: list[str],
) -> set[str]:
    """Resolve a list of sample_batch_ids → unique workspace_ids in one query."""
    async with async_session() as session:
        result = await session.execute(
            select(Dataset.workspace_id)
            .distinct()
            .join(SampleBatch, SampleBatch.dataset_id == Dataset.dataset_id)
            .where(SampleBatch.sample_batch_id.in_(sample_batch_ids))
        )
        return set(result.scalars().all())


async def _get_workspace_ids_from_samples(
    sample_item_ids: list[str],
) -> set[str]:
    """Resolve a list of sample_item_ids → unique workspace_ids in one query."""
    async with async_session() as session:
        result = await session.execute(
            select(Dataset.workspace_id)
            .distinct()
            .join(SampleBatch, SampleBatch.dataset_id == Dataset.dataset_id)
            .join(SampleItem, SampleItem.sample_batch_id == SampleBatch.sample_batch_id)
            .where(SampleItem.sample_item_id.in_(sample_item_ids))
        )
        return set(result.scalars().all())


def _superuser_member(workspace_id: str, user: User) -> WorkspaceMember:
    """Return a synthetic WorkspaceMember for superusers."""
    return WorkspaceMember(
        workspace_member_id="__superuser__",
        workspace_id=workspace_id,
        user_id=user.id,
        workspace_role="owner",
    )


async def _enforce(
    workspace_id: str | None,
    user: User,
    min_level: int,
) -> WorkspaceMember:
    """Core ACL check shared by all public functions."""
    if user.is_superuser:
        # Superusers bypass workspace membership checks
        return _superuser_member(workspace_id or "__resolved__", user)

    if workspace_id is None:
        raise ForbiddenAccessException()

    membership = await _get_workspace_membership(workspace_id, user)
    if membership is None:
        raise ForbiddenAccessException()

    user_level = _role_levels[membership.workspace_role]
    if user_level < min_level:
        raise ForbiddenAccessException()

    return membership


# ---------------------------------------------------------------------------
# Public: explicit check (for body-param routes)
# ---------------------------------------------------------------------------


async def check_dataset_access(
    dataset_id: str,
    user: User,
    min_role: str,
) -> WorkspaceMember:
    """Check workspace-level ACL given a dataset_id.

    Call this explicitly in route handlers where dataset_id comes from
    the request body (not injectable as a dependency).

    Usage::

        @router.post("")
        async def create_batch(
            body: SampleBatchCreate,
            user=Depends(current_active_user)
        ):
            await check_dataset_access(body.dataset_id, user, "editor")
            ...

    :raises ForbiddenAccessException: If user lacks the required workspace role.
    """
    workspace_id = await _get_workspace_id_from_dataset(dataset_id)
    return await _enforce(workspace_id, user, _role_levels[min_role])


async def check_batch_access(
    sample_batch_id: str,
    user: User,
    min_role: str,
) -> WorkspaceMember:
    """Check workspace-level ACL given a sample_batch_id.

    Resolves batch → dataset → workspace, then checks membership.

    :raises ForbiddenAccessException: If user lacks the required workspace role.
    """
    workspace_id = await _get_workspace_id_from_batch(sample_batch_id)
    return await _enforce(workspace_id, user, _role_levels[min_role])


async def check_batch_access_bulk(
    sample_batch_ids: list[str],
    user: User,
    min_role: str,
) -> None:
    """Check workspace-level ACL for a list of sample_batch_ids in one query.

    Resolves all batch → dataset → workspace in a single query, then checks
    membership for each unique workspace.

    :raises ForbiddenAccessException: If any batch resolves to a workspace
        the user lacks the required role for, or if any batch doesn't resolve.
    """
    workspace_ids = await _get_workspace_ids_from_batches(sample_batch_ids)
    if not workspace_ids:
        raise ForbiddenAccessException()
    min_level = _role_levels[min_role]
    for workspace_id in workspace_ids:
        await _enforce(workspace_id, user, min_level)


async def check_sample_access(
    sample_item_id: str,
    user: User,
    min_role: str,
) -> WorkspaceMember:
    """Check workspace-level ACL given a sample_item_id.

    Resolves sample → batch → dataset → workspace, then checks membership.

    :raises ForbiddenAccessException: If user lacks the required workspace role.
    """
    workspace_id = await _get_workspace_id_from_sample(sample_item_id)
    return await _enforce(workspace_id, user, _role_levels[min_role])


async def check_sample_access_bulk(
    sample_item_ids: list[str],
    user: User,
    min_role: str,
) -> None:
    """Check workspace-level ACL for a list of sample_item_ids in one query.

    Resolves all sample → batch → dataset → workspace in a single query, then
    checks membership for each unique workspace.

    :raises ForbiddenAccessException: If any sample resolves to a workspace
        the user lacks the required role for, or if any sample doesn't resolve.
    """
    workspace_ids = await _get_workspace_ids_from_samples(sample_item_ids)
    if not workspace_ids:
        raise ForbiddenAccessException()
    min_level = _role_levels[min_role]
    for workspace_id in workspace_ids:
        await _enforce(workspace_id, user, min_level)


# ---------------------------------------------------------------------------
# Public: FastAPI dependency factories
# ---------------------------------------------------------------------------


def require_workspace_role(min_role: str):
    """Enforce minimum workspace role via ``workspace_id`` **path** param.

    Usage::

        @router.get("/{workspace_id}/workspaces")
        async def list_ws(..., membership=Depends(require_workspace_role("guest"))):
    """
    min_level = _role_levels[min_role]

    async def dependency(
        workspace_id: str = Path(...),
        user: User = Depends(current_active_user),
    ) -> WorkspaceMember:
        return await _enforce(workspace_id, user, min_level)

    return dependency


def require_dataset_role(min_role: str):
    """Enforce minimum workspace role via ``dataset_id`` **path** param.

    Resolves dataset → workspace, then checks membership.

    Usage::

        @router.get("/{dataset_id}/details")
        async def get_ds(..., membership=Depends(require_dataset_role("guest"))):
    """
    min_level = _role_levels[min_role]

    async def dependency(
        dataset_id: str = Path(...),
        user: User = Depends(current_active_user),
    ) -> WorkspaceMember:
        workspace_id = await _get_workspace_id_from_dataset(dataset_id)
        return await _enforce(workspace_id, user, min_level)

    return dependency


def require_dataset_query_role(min_role: str):
    """Enforce minimum workspace role via ``dataset_id`` **query** param.

    For list endpoints where dataset_id is a required query filter.

    Usage::

        @router.get("")
        async def list_batches(
            dataset_id: str = Query(...),
            ...,
            membership=Depends(require_dataset_query_role("guest")),
        ):
    """
    min_level = _role_levels[min_role]

    async def dependency(
        dataset_id: str = Query(...),
        user: User = Depends(current_active_user),
    ) -> WorkspaceMember:
        workspace_id = await _get_workspace_id_from_dataset(dataset_id)
        return await _enforce(workspace_id, user, min_level)

    return dependency


def require_batch_role(min_role: str):
    """Enforce minimum workspace role via ``sample_batch_id`` **path** param.

    Resolves batch → dataset → workspace, then checks membership.
    """
    min_level = _role_levels[min_role]

    async def dependency(
        sample_batch_id: str = Path(...),
        user: User = Depends(current_active_user),
    ) -> WorkspaceMember:
        workspace_id = await _get_workspace_id_from_batch(sample_batch_id)
        return await _enforce(workspace_id, user, min_level)

    return dependency


def require_sample_role(min_role: str):
    """Enforce minimum workspace role via ``sample_item_id`` **path** param.

    Resolves sample → batch → dataset → workspace, then checks membership.
    """
    min_level = _role_levels[min_role]

    async def dependency(
        sample_item_id: str = Path(...),
        user: User = Depends(current_active_user),
    ) -> WorkspaceMember:
        workspace_id = await _get_workspace_id_from_sample(sample_item_id)
        return await _enforce(workspace_id, user, min_level)

    return dependency


def require_acquisition_workspace_role(min_role: str):
    """Enforce minimum workspace role on the system Acquisitions workspace.

    Resolves the ``Acquisitions`` system workspace and checks the caller's
    membership role.  Used by acquisition dataset endpoints that are not
    scoped to a specific dataset or workspace path parameter.
    """
    min_level = _role_levels[min_role]

    async def dependency(
        user: User = Depends(current_active_user),
    ) -> WorkspaceMember:
        workspace_id = await _get_acquisition_workspace_id()
        return await _enforce(workspace_id, user, min_level)

    return dependency
