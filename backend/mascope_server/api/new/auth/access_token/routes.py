from fastapi import APIRouter, Body, Depends
from mascope_server.api.new.auth import auth_backend_access_token
from mascope_server.api.new.auth.dependencies import (
    guest_user,
    role_based_access,
)
from mascope_server.api.new.auth.access_token.schemas import AccessTokenRequest
from mascope_server.api.new.auth.access_token.service import (
    generate_access_token,
    remove_access_tokens,
)

# Access token-based routes for Jupyter server or external API access
access_token_router = APIRouter(prefix="/access_token")


@access_token_router.post("/generate", name="auth:access-token.generate")
async def access_token_generate_route(
    access_token_request: AccessTokenRequest = Body(...),
    user=Depends(guest_user),
    strategy=Depends(auth_backend_access_token.get_strategy),
):
    """
    API route to generate a new access token.

    This endpoint generates an access token for the authenticated user.
    Different services require different minimum roles:
    - mascope_api: guest or higher - for Jupyter access by mascope_api library.
    - tof-agent: editor or higher - for access to TOF agent.
    """
    service_name = access_token_request.service_name

    # Verify user has required role for the service
    if service_name == "mascope-api":
        await role_based_access(user, "guest")
    elif service_name == "tof-agent":
        await role_based_access(user, "editor")

    return await generate_access_token(
        user=user, strategy=strategy, service_name=service_name
    )


@access_token_router.post("/remove", name="auth:access-token.remove")
async def access_token_remove_route(
    access_token_request: AccessTokenRequest = Body(...),
    user=Depends(guest_user),
    strategy=Depends(auth_backend_access_token.get_strategy),
):
    """
    API route to remove all of a user's access tokens.

    This endpoint deletes all access tokens associated with the authenticated user.
    """
    return await remove_access_tokens(
        user=user, strategy=strategy, service_name=access_token_request.service_name
    )
