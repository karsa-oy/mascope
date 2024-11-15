from fastapi import APIRouter, Depends
from mascope_server.api.lib.api_features import api_route
from mascope_server.api.new.auth.dependencies import editor_user, guest_user
from mascope_server.api.controllers.attribute_templates.attribute_templates_controller import (
    get_attribute_templates,
    get_attribute_template,
    create_attribute_template,
    update_attribute_template,
    delete_attribute_template,
)
from mascope_server.api.models.attribute_templates.attribute_template_pydantic_model import (
    AttributeTemplateCreateBody,
    AttributeTemplateUpdateBody,
    GetAttributeTemplatesQueryParams,
)

attribute_templates_router = APIRouter(
    prefix="/api/attribute_templates", tags=["Attribute Templates"]
)


@attribute_templates_router.get("")
@api_route()
async def get_attribute_templates_route(
    query_params: GetAttributeTemplatesQueryParams = Depends(), user=Depends(guest_user)
):
    """Retrieve a list of attribute templates.

    :param query_params: Query parameters for sorting and pagination, defaults to Depends().
    :type query_params: GetAttributeTemplatesQueryParams, optional
    :param user: The current authenticated user, defaults to Depends(guest_user).
    :type user: User, optional
    :return: A dictionary containing total count and list of attribute templates.
    :rtype: dict
    """
    return await get_attribute_templates(**query_params.model_dump())


@attribute_templates_router.get("/{attribute_template_id}")
@api_route()
async def get_attribute_template_route(
    attribute_template_id: str, user=Depends(guest_user)
):
    """Retrieve details of a specific attribute template by ID.

    :param attribute_template_id: The unique identifier of the attribute template.
    :type attribute_template_id: str
    :param user: The current authenticated user, defaults to Depends(guest_user).
    :type user: User, optional
    :return: A dictionary containing the attribute template details.
    :rtype: dict
    """
    return await get_attribute_template(attribute_template_id)


@attribute_templates_router.post("")
@api_route(status_code=201)
async def create_attribute_template_route(
    body: AttributeTemplateCreateBody, user=Depends(editor_user)
):
    """Create a new attribute template.

    :param body: The attribute template creation data.
    :type body: AttributeTemplateCreateBody
    :param user: The current authenticated user with editor permissions, defaults to Depends(editor_user).
    :type user: User, optional
    :return: A dictionary containing the newly created attribute template's details.
    :rtype: dict
    """
    return await create_attribute_template(body)


@attribute_templates_router.patch("/{attribute_template_id}")
@api_route()
async def update_attribute_template_route(
    attribute_template_id: str,
    body: AttributeTemplateUpdateBody,
    user=Depends(editor_user),
):
    """Update an existing attribute template's details.

    :param attribute_template_id: The unique identifier of the attribute template.
    :type attribute_template_id: str
    :param body: The attribute template update data.
    :type body: AttributeTemplateUpdateBody
    :param user: The current authenticated user with editor permissions, defaults to Depends(editor_user).
    :type user: User, optional
    :return: A dictionary containing the updated attribute template's details.
    :rtype: dict
    """
    return await update_attribute_template(attribute_template_id, body)


@attribute_templates_router.delete("/{attribute_template_id}")
@api_route()
async def delete_attribute_template_route(
    attribute_template_id: str, user=Depends(editor_user)
):
    """Delete a specific attribute template by ID.

    :param attribute_template_id: The unique identifier of the attribute template.
    :type attribute_template_id: str
    :param user: The current authenticated user with editor permissions, defaults to Depends(editor_user).
    :type user: User, optional
    :return: A dictionary confirming deletion (if applicable).
    :rtype: dict or None
    """
    return await delete_attribute_template(attribute_template_id)
