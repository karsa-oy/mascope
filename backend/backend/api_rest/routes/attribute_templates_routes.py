from fastapi import APIRouter

from ..controllers.attribute_templates_controller import (
    get_attribute_template_by_id,
    get_attribute_templates,
)

attribute_templates_router = APIRouter()


@attribute_templates_router.get("/api/attribute_templates")
async def get_attribute_templates_route(
    sort: str = None,
    order: str = None,
    page: int = 0,
    limit: int = 100,
):
    return await get_attribute_templates(sort, order, page, limit)


@attribute_templates_router.get("/api/attribute_templates/{attribute_template_id}")
async def get_attribute_template_by_id_route(attribute_template_id: str):
    return await get_attribute_template_by_id(attribute_template_id)
