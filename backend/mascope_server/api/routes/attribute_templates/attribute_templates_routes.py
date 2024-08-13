from fastapi import APIRouter, Depends
from mascope_server.api.lib.api_features import api_route

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

attribute_templates_router = APIRouter()


@attribute_templates_router.get("/api/attribute_templates")
@api_route()
async def get_attribute_templates_route(
    query_params: GetAttributeTemplatesQueryParams = Depends(),
):
    return await get_attribute_templates(**query_params.model_dump())


@attribute_templates_router.get("/api/attribute_templates/{attribute_template_id}")
@api_route()
async def get_attribute_template_route(attribute_template_id: str):
    return await get_attribute_template(attribute_template_id)


@attribute_templates_router.post("/api/attribute_templates")
@api_route(
    status_code=201,
    include_message=True,
    success_message="Attribute template created successfully",
)
async def create_attribute_template_route(body: AttributeTemplateCreateBody):
    return await create_attribute_template(body)


@attribute_templates_router.patch("/api/attribute_templates/{attribute_template_id}")
@api_route(
    include_message=True, success_message="Attribute template updated successfully"
)
async def update_attribute_template_route(
    attribute_template_id: str, body: AttributeTemplateUpdateBody
):
    return await update_attribute_template(attribute_template_id, body)


@attribute_templates_router.delete("/api/attribute_templates/{attribute_template_id}")
@api_route(
    include_data=False,
    include_message=True,
    success_message="Attribute template deleted successfully",
)
async def delete_attribute_template_route(attribute_template_id: str):
    await delete_attribute_template(attribute_template_id)
