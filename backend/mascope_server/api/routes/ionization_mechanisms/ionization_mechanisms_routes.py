from fastapi import APIRouter, Depends, Body
from mascope_server.api.new.auth.dependencies import guest_user, editor_user
from mascope_server.api.lib.api_features import api_route
from mascope_server.api.controllers.ionization_mechanisms.ionization_mechanisms_controller import (
    get_ionization_mechanisms,
    get_ionization_mechanism,
    create_ionization_mechanism,
    delete_ionization_mechanism,
)
from mascope_server.api.models.ionization_mechanisms.ionization_mechanism_pydantic_model import (
    IonizationMechanismCreate,
    GetIonizationMechanismsQueryParams,
)

ionization_mechanisms_router = APIRouter(
    prefix="/api/ionization_mechanisms",
    tags=["Ionization Mechanisms"],
)


@ionization_mechanisms_router.get("")
@api_route()
async def get_ionization_mechanisms_route(
    query_params: GetIonizationMechanismsQueryParams = Depends(),
    user=Depends(guest_user),
):
    """Retrieve a list of ionization mechanisms.

    :param query_params: Query parameters for filtering, sorting, and pagination.
    :type query_params: GetIonizationMechanismsQueryParams
    :param user: The current authenticated user, defaults to Depends(guest_user).
    :type user: User
    :return: A dictionary containing total count and list of ionization mechanisms.
    :rtype: dict
    """
    return await get_ionization_mechanisms(**query_params.model_dump())


@ionization_mechanisms_router.get("/{ionization_mechanism_id}")
@api_route()
async def get_ionization_mechanism_route(
    ionization_mechanism_id: str,
    user=Depends(guest_user),
):
    """Retrieve details of a specific ionization mechanism by ID.

    :param ionization_mechanism_id: Unique identifier of the ionization mechanism.
    :type ionization_mechanism_id: str
    :param user: The current authenticated user, defaults to Depends(guest_user).
    :type user: User
    :return: The requested ionization mechanism's details.
    :rtype: dict
    """
    return await get_ionization_mechanism(ionization_mechanism_id)


@ionization_mechanisms_router.post("")
@api_route(status_code=201)
async def create_ionization_mechanism_route(
    ionization_mechanism: IonizationMechanismCreate = Body(...),
    user=Depends(editor_user),
):
    """Create a new ionization mechanism.

    :param ionization_mechanism: Ionization mechanism to create.
    :type ionization_mechanism: IonizationMechanismCreate
    :param user: The current authenticated user with editor permissions, defaults to Depends(editor_user).
    :type user: User
    :return: Created ionization mechanism details.
    :rtype: dict
    """
    return await create_ionization_mechanism(ionization_mechanism)


@ionization_mechanisms_router.delete("/{ionization_mechanism_id}")
@api_route()
async def delete_ionization_mechanism_route(
    ionization_mechanism_id: str,
    user=Depends(editor_user),
):
    """Delete an ionization mechanism by ID.

    :param ionization_mechanism_id: Unique identifier of the ionization mechanism to delete.
    :type ionization_mechanism_id: str
    :param user: The current authenticated user with editor permissions, defaults to Depends(editor_user).
    :type user: User
    :return: Message confirming deletion.
    :rtype: dict
    """
    return await delete_ionization_mechanism(ionization_mechanism_id)
