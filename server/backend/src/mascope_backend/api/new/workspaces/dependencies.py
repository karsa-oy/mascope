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

**Explicit check functions** (call in route handler body, preferred for
acquisition/instrument routes):

- ``check_dataset_access``:   dataset_id from request body / other source
- ``check_batch_access``:     sample_batch_id from request body / other source
- ``check_batch_access_bulk``:  list of sample_batch_ids (single query)
- ``check_sample_access``:      sample_item_id from request body / other source
- ``check_sample_access_bulk``: list of sample_item_ids (single query)
- ``check_sample_file_access_bulk``: list of sample_file_ids via items (single query)
- ``check_sample_file_instrument_access``: sample_file_id via instrument → workspace
- ``check_sample_file_instrument_access_bulk``: list of sample_file_ids via instruments
- ``check_instrument_workspace_access``: instrument name → workspace
- ``accessible_acquisition_instruments``: set of instruments user can access
- ``check_target_collection_access``:  target_collection_id → workspace_id
- ``accessible_workspace_ids_for_user``: set of workspace_ids user is a member of

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
    SampleFile,
    SampleItem,
    TargetCollection,
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


async def _get_workspace_id_from_collection(target_collection_id: str) -> str | None:
    """Resolve target_collection_id → workspace_id (may be None for global).

    :raises ValueError: If the collection does not exist.
    """
    async with async_session() as session:
        result = await session.execute(
            select(TargetCollection.workspace_id).where(
                TargetCollection.target_collection_id == target_collection_id
            )
        )
        row = result.one_or_none()
        if row is None:
            raise ValueError(f"Target collection {target_collection_id} not found")
        return row[0]


async def _get_workspace_id_from_instrument(instrument: str) -> str | None:
    """Resolve an instrument name to its system acquisition workspace ID."""
    from mascope_backend.api.models.dataset.config import dataset_config

    workspace_name = f"{dataset_config.ACQUISITION_NAME_PREFIX} {instrument}"
    async with async_session() as session:
        result = await session.execute(
            select(Workspace.workspace_id).where(
                Workspace.workspace_name == workspace_name,
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


async def accessible_acquisition_instruments(user: User) -> set[str] | None:
    """Return the set of instrument names the user may access, or *None* if
    the user has full visibility (superuser, global admin, or global owner).

    Resolves instrument names from the user's acquisition workspace
    memberships by stripping the workspace name prefix.
    """
    from mascope_backend.api.models.dataset.config import dataset_config

    if user.is_superuser or (
        user.role_id is not None and user.role_id >= _role_levels["admin"]
    ):
        return None

    prefix = f"{dataset_config.ACQUISITION_NAME_PREFIX} "
    async with async_session() as session:
        result = await session.execute(
            select(Workspace.workspace_name)
            .join(
                WorkspaceMember,
                WorkspaceMember.workspace_id == Workspace.workspace_id,
            )
            .where(
                WorkspaceMember.user_id == user.id,
                Workspace.is_system.is_(True),
                Workspace.workspace_name.like(f"{prefix}%"),
            )
        )
        return {name.removeprefix(prefix) for name in result.scalars().all()}


async def check_sample_file_instrument_access(
    sample_file_id: str,
    user: User,
    min_role: str,
) -> WorkspaceMember:
    """Check workspace-level ACL for a sample file via its instrument.

    Checks (in order):
    1. Global admin/owner bypass: full visibility.
    2. Instrument workspace: the user is a member of the system workspace
       for this file's instrument.
    3. Item-based: the file is linked to a sample item in a workspace
       the user has access to.

    :raises ForbiddenAccessException: If no path grants access.
    """
    if user.is_superuser or (
        user.role_id is not None and user.role_id >= _role_levels["admin"]
    ):
        return _superuser_member("__admin__", user)

    async with async_session() as session:
        instrument = (
            await session.execute(
                select(SampleFile.instrument).where(
                    SampleFile.sample_file_id == sample_file_id
                )
            )
        ).scalar_one_or_none()

    if instrument is None:
        raise ForbiddenAccessException()

    # Path 1: instrument workspace membership
    workspace_id = await _get_workspace_id_from_instrument(instrument)
    if workspace_id is not None:
        membership = await _get_workspace_membership(workspace_id, user)
        if membership is not None:
            user_level = _role_levels[membership.workspace_role]
            if user_level >= _role_levels[min_role]:
                return membership

    # Path 2: item-based workspace membership
    await check_sample_file_access_bulk([sample_file_id], user, min_role)
    return WorkspaceMember(
        workspace_member_id="__fallback__",
        workspace_id="__fallback__",
        user_id=user.id,
        workspace_role=min_role,
    )


async def check_sample_file_instrument_access_bulk(
    sample_file_ids: list[str],
    user: User,
    min_role: str,
) -> None:
    """Check per-instrument workspace ACL for a list of sample file IDs.

    Resolves the unique instruments from the given files in a single query,
    then verifies the user has at least *min_role* in each instrument's
    system workspace.

    :raises ForbiddenAccessException: If any file's instrument workspace
        denies access, or if any file ID does not exist.
    """
    if user.is_superuser or (
        user.role_id is not None and user.role_id >= _role_levels["admin"]
    ):
        return

    if not sample_file_ids:
        raise ForbiddenAccessException()

    async with async_session() as session:
        result = await session.execute(
            select(SampleFile.instrument)
            .distinct()
            .where(SampleFile.sample_file_id.in_(sample_file_ids))
        )
        instruments = set(result.scalars().all())

    if not instruments:
        raise ForbiddenAccessException()

    min_level = _role_levels[min_role]
    for instrument in instruments:
        workspace_id = await _get_workspace_id_from_instrument(instrument)
        if workspace_id is None:
            raise ForbiddenAccessException()
        await _enforce(workspace_id, user, min_level)


async def check_instrument_workspace_access(
    instrument: str,
    user: User,
    min_role: str,
) -> WorkspaceMember:
    """Check workspace-level ACL for an instrument's acquisition workspace.

    Resolves the instrument name to its system workspace and checks that the
    user has at least *min_role*.  If no workspace exists yet for this
    instrument the check passes (the workspace will be created during
    auto-processing and the uploading user will be made owner).

    :param instrument: Instrument name (e.g. ``"Orbion"``).
    :param user: The authenticated user.
    :param min_role: Minimum workspace role required (e.g. ``"editor"``).
    :raises ForbiddenAccessException: If the workspace exists and the user
        lacks the required role.
    :return: The user's WorkspaceMember record (synthetic for superusers or
        when no workspace exists yet).
    """
    if user.is_superuser or (
        user.role_id is not None and user.role_id >= _role_levels["admin"]
    ):
        return _superuser_member("__instrument__", user)

    workspace_id = await _get_workspace_id_from_instrument(instrument)
    if workspace_id is None:
        # No workspace exists for this instrument. Allow for auto-processing to create
        # and assign the user as owner.
        return WorkspaceMember(
            workspace_member_id="__new_instrument__",
            workspace_id="__new_instrument__",
            user_id=user.id,
            workspace_role=min_role,
        )

    return await _enforce(workspace_id, user, _role_levels[min_role])


async def check_workspace_access(
    workspace_id: str,
    user: User,
    min_role: str,
) -> WorkspaceMember:
    """Check workspace-level ACL given a workspace_id directly.

    For routes where the target workspace_id comes from the request body
    (e.g. a dataset move target) rather than a path param. Unlike
    check_dataset_access, no resolution is needed - the workspace_id is
    already in hand.

    :param workspace_id: The workspace to check membership against.
    :param user: The authenticated user.
    :param min_role: Minimum workspace role required.
    :raises ForbiddenAccessException: If user lacks the required workspace role.
    :return: The user's WorkspaceMember record (synthetic for superusers).
    """
    return await _enforce(workspace_id, user, _role_levels[min_role])


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


async def check_sample_file_access_bulk(
    sample_file_ids: list[str],
    user: User,
    min_role: str,
) -> None:
    """Check workspace-level ACL for a list of sample_file_ids via sample items.

    For each requested file, verifies that at least one sample_item referencing
    it belongs to a workspace where the user has the required role.  This
    correctly handles the one-to-many relationship between sample files and
    sample items — a file is accessible if ANY of its sample items is in an
    accessible workspace.

    :raises ForbiddenAccessException: If any file has no sample item in an
        accessible workspace, or if any file has no sample items at all.
    """
    if user.is_superuser:
        return

    if not sample_file_ids:
        raise ForbiddenAccessException()

    min_level = _role_levels[min_role]
    async with async_session() as session:
        # Find which of the requested file IDs have at least one sample item
        # in a workspace where the user has sufficient membership.
        result = await session.execute(
            select(SampleItem.sample_file_id)
            .distinct()
            .join(
                SampleBatch, SampleBatch.sample_batch_id == SampleItem.sample_batch_id
            )
            .join(Dataset, Dataset.dataset_id == SampleBatch.dataset_id)
            .join(
                WorkspaceMember,
                WorkspaceMember.workspace_id == Dataset.workspace_id,
            )
            .where(
                SampleItem.sample_file_id.in_(sample_file_ids),
                WorkspaceMember.user_id == user.id,
                WorkspaceMember.workspace_role.in_(
                    [r for r, lvl in _role_levels.items() if lvl >= min_level]
                ),
            )
        )
        accessible_ids = set(result.scalars().all())

    if not set(sample_file_ids).issubset(accessible_ids):
        raise ForbiddenAccessException()


async def check_target_collection_access(
    target_collection_id: str,
    user: User,
    min_role: str,
) -> WorkspaceMember | None:
    """Check workspace-level ACL given a target_collection_id.

    Resolves collection → workspace_id, then checks membership.

    - **Global collections** (workspace_id is NULL): readable by any
      authenticated user; mutations (editor+) require global admin role.
    - **Workspace collections**: standard ``_enforce`` membership check.

    :raises ForbiddenAccessException: If user lacks the required workspace role
        or collection not found.
    :return: The user's WorkspaceMember record, or *None* for global
        collections readable by the caller.
    """
    try:
        workspace_id = await _get_workspace_id_from_collection(target_collection_id)
    except ValueError:
        raise ForbiddenAccessException()

    if workspace_id is None:
        # Global collection – anyone can read, admins+ can mutate.
        min_level = _role_levels[min_role]
        if min_level > _role_levels["guest"]:
            if not user.is_superuser and (
                user.role_id is None or user.role_id < _role_levels["admin"]
            ):
                raise ForbiddenAccessException()
        return None

    return await _enforce(workspace_id, user, _role_levels[min_role])


async def accessible_workspace_ids_for_user(user: User) -> set[str]:
    """Return the set of workspace_ids the user is a member of.

    Superusers get all workspace_ids.  Used by list endpoints that need to
    filter results by workspace membership.
    """
    async with async_session() as session:
        if user.is_superuser:
            result = await session.execute(select(Workspace.workspace_id))
        else:
            result = await session.execute(
                select(WorkspaceMember.workspace_id).where(
                    WorkspaceMember.user_id == user.id
                )
            )
        return set(result.scalars().all())


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
