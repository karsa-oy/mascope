from typing import Optional

from pydantic import BaseModel, Field, model_validator

from mascope_backend.api.new.auth.config import auth_settings


class RoleRead(BaseModel):
    """
    Schema for reading roles.
    Maps role_id to its corresponding access level in the application.
    """

    role_id: int = Field(
        ...,
        description="Unique identifier for the role (used as access level from the auth configs).",
    )
    role_name: str = Field(..., description="Name of the role.")
    permissions: Optional[dict] = Field(
        None, description="Permissions associated with this role. Currently not used."
    )

    model_config = {"from_attributes": True}


class GetRolesQueryParams(BaseModel):
    """
    Query parameter model for retrieving roles with filtering options.
    """

    role_name_min: Optional[str] = Field(
        None, description="Minimum role name for filtering (e.g., 'guest')."
    )
    role_name_max: Optional[str] = Field(
        None, description="Maximum role name for filtering (e.g., 'admin')."
    )

    @model_validator(mode="after")
    @classmethod
    def validate_roles(cls, values):
        role_access_levels = auth_settings.ROLE_ACCESS_LEVELS
        role_name_min = values.role_name_min
        role_name_max = values.role_name_max

        # Validate role_name_min exists in configuration
        if role_name_min and role_name_min not in role_access_levels:
            raise ValueError(f"Invalid role_name_min: '{role_name_min}'.")

        # Validate role_name_max exists in configuration
        if role_name_max and role_name_max not in role_access_levels:
            raise ValueError(f"Invalid role_name_max: '{role_name_max}'.")

        # Validate role_name_min <= role_name_max based on access levels
        if role_name_min and role_name_max:
            min_level = role_access_levels[role_name_min]
            max_level = role_access_levels[role_name_max]
            if min_level > max_level:
                raise ValueError(
                    f"Invalid range: role_name_min '{role_name_min}' cannot have a higher access level than role_name_max '{role_name_max}'."
                )

        return values
