"""
Target isotope API routes.

Defines REST API endpoints for target isotope operations including
retrieval with filtering, sorting, and pagination capabilities.
"""

from fastapi import APIRouter, Depends, Query
from mascope_backend.api.new.auth.dependencies import guest_user
from mascope_backend.api.lib.api_features import api_route
from mascope_backend.api.controllers.target.isotopes.target_isotopes_controller import (
    get_target_isotope,
    get_target_isotopes,
)
from mascope_backend.api.models.target.isotopes.target_isotope_pydantic_model import (
    GetTargetIsotopesQueryParams,
)

target_isotopes_router = APIRouter(
    prefix="/api/target/isotopes", tags=["Target Isotopes"]
)


@target_isotopes_router.get("")
@api_route()
async def get_target_isotopes_route(
    query_params: GetTargetIsotopesQueryParams = Query(),
    user=Depends(guest_user),
):
    """Retrieve a list of target isotopes.

    :param query_params: Query parameters for sorting, filtering, and pagination.
    :type query_params: GetTargetIsotopesQueryParams
    :param user: The current authenticated user with guest permissions.
    :type user: User
    :return: A dictionary containing total count and list of target isotopes.
    :rtype: dict
    """
    return await get_target_isotopes(**query_params.model_dump())


@target_isotopes_router.get("/{target_isotope_id}")
@api_route()
async def get_target_isotope_route(
    target_isotope_id: str,
    user=Depends(guest_user),
):
    """Retrieve details of a specific target isotope by ID.

    :param target_isotope_id: The unique identifier of the target isotope.
    :param user: The authenticated user, defaults to Depends(guest_user).
    :return: Dictionary with detailed information of the target isotope.
    """
    return await get_target_isotope(target_isotope_id)
