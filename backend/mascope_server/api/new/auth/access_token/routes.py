from fastapi import APIRouter, Body, Depends
from mascope_server.api.new.auth import auth_backend_access_token
from mascope_server.api.new.auth.dependencies import current_active_user
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
    user=Depends(current_active_user),
    strategy=Depends(auth_backend_access_token.get_strategy),
):
    """
    API route to generate a new access token.

    This endpoint generates an access token for the authenticated user,
    which can be used to authenticate requests to external services as Jupyter server.
    """
    return await generate_access_token(
        user=user, strategy=strategy, service_name=access_token_request.service_name
    )


@access_token_router.post("/remove", name="auth:access-token.remove")
async def access_token_remove_route(
    access_token_request: AccessTokenRequest = Body(...),
    user=Depends(current_active_user),
    strategy=Depends(auth_backend_access_token.get_strategy),
):
    """
    API route to remove all of a user's access tokens.

    This endpoint deletes all access tokens associated with the authenticated user.
    """
    return await remove_access_tokens(
        user=user, strategy=strategy, service_name=access_token_request.service_name
    )
