"""Workspace-specific exceptions."""

from mascope_backend.api.lib.exceptions.api_exceptions import (
    DuplicateException,
    NotFoundException,
)


class WorkspaceNotFoundException(NotFoundException):
    def __init__(self, workspace_id: str):
        super().__init__(detail=f"Workspace '{workspace_id}' not found.")


class WorkspaceMemberNotFoundException(NotFoundException):
    def __init__(self, detail: str = "Workspace member not found."):
        super().__init__(detail=detail)


class WorkspaceMemberAlreadyExistsException(DuplicateException):
    def __init__(self, workspace_id: str, user_id: int):
        super().__init__(
            detail=f"User '{user_id}' is already a member of workspace '{workspace_id}'"
        )
