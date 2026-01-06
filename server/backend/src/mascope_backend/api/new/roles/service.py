from typing import Optional

from sqlalchemy.future import select

from mascope_backend.api.lib.api_features import api_controller
from mascope_backend.api.new.auth.config import auth_settings
from mascope_backend.api.new.roles.exceptions import InvalidRoleException
from mascope_backend.db import Role, async_session


@api_controller()
async def get_roles(
    role_name_min: Optional[str] = None,
    role_name_max: Optional[str] = None,
) -> dict:
    """
    Retrieves all roles from the database with optional filtering.

    :param role_name_min: Minimum role name for filtering (inclusive), defaults to None.
    :type role_name_min: Optional[str]
    :param role_name_max: Maximum role name for filtering (inclusive), defaults to None.
    :type role_name_max: Optional[str]
    :raises InvalidRoleException: If any role_id does not match the configuration.
    :return: A list of roles with metadata and count.
    :rtype: dict
    """
    async with async_session() as session:
        # Step 1: Construct the base query
        query = select(Role)

        # Step 2: Apply filtering if specified
        if role_name_min or role_name_max:
            # Retrieve role levels from the configuration
            role_access_levels = auth_settings.ROLE_ACCESS_LEVELS

            if role_name_min:
                min_access_level = role_access_levels.get(role_name_min, None)
                if min_access_level is not None:
                    query = query.filter(Role.role_id >= min_access_level)

            if role_name_max:
                max_access_level = role_access_levels.get(role_name_max, None)
                if max_access_level is not None:
                    query = query.filter(Role.role_id <= max_access_level)

        # Step 3: Execute the query
        result = await session.execute(query)
        roles = result.scalars().all()

        # Step 4: Validate roles
        validated_roles = []
        for role in roles:
            if role.role_id not in auth_settings.ROLE_ACCESS_LEVELS.values():
                raise InvalidRoleException(
                    detail=f"Role '{role.role_name}' with ID '{role.role_id}' is not defined in the configuration."
                )
            validated_roles.append(role)

    # Step 5: Return validated roles with count
    return {
        "message": f"Retrieved {len(validated_roles)} roles.",
        "results": len(validated_roles),
        "data": [role.to_dict() for role in validated_roles],
    }
