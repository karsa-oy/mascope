from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from ..controllers.attribute_templates_controller import (
    get_attribute_templates,
    get_attribute_template,
    create_attribute_template,
    update_attribute_template,
    delete_attribute_template,
)
from ..models.pydantic_models.attribute_template_pydantic_model import (
    AttributeTemplateCreateBody,
    AttributeTemplateUpdateBody,
)
from ..exceptions import ApiException

attribute_templates_router = APIRouter()


@attribute_templates_router.get("/api/attribute_templates")
async def get_attribute_templates_route(
    sort: str = Query(
        None, description="The column name by which you want to sort the results."
    ),
    order: str = Query(
        None,
        description="Can either be 'asc' for ascending order or 'desc' for descending order.",
    ),
    page: int = Query(0, description="The page number for pagination, default 0"),
    limit: int = Query(100, description="The number of results per page."),
):
    try:
        result = await get_attribute_templates(sort, order, page, limit)
        result_data = jsonable_encoder(result)
        return JSONResponse(status_code=200, content=result_data)
    except ApiException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"error": e.user_message, "detail": e.tech_message},
        )


@attribute_templates_router.get("/api/attribute_templates/{attribute_template_id}")
async def get_attribute_template_route(attribute_template_id: str):
    try:
        result = await get_attribute_template(attribute_template_id)
        result_data = jsonable_encoder(result)
        return JSONResponse(status_code=200, content=result_data)
    except ApiException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"error": e.user_message, "detail": e.tech_message},
        )


@attribute_templates_router.post("/api/attribute_templates")
async def create_attribute_template_route(
    body: AttributeTemplateCreateBody,
):
    try:
        result = await create_attribute_template(body)
        result_data = jsonable_encoder(result)
        return JSONResponse(
            status_code=201,
            content={
                "message": "Attribute template created successfully.",
                "data": result_data,
            },
        )
    except ApiException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"error": e.user_message, "detail": e.tech_message},
        )


@attribute_templates_router.patch("/api/attribute_templates/{attribute_template_id}")
async def update_attribute_template_route(
    attribute_template_id: str,
    body: AttributeTemplateUpdateBody,
):
    try:
        result = await update_attribute_template(attribute_template_id, body)
        result_data = jsonable_encoder(result)
        return JSONResponse(
            status_code=200,
            content={
                "message": "Attribute template updated successfully.",
                "data": result_data,
            },
        )
    except ApiException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"error": e.user_message, "detail": e.tech_message},
        )


@attribute_templates_router.delete("/api/attribute_templates/{attribute_template_id}")
async def delete_attribute_template_route(
    attribute_template_id: str,
):
    try:
        await delete_attribute_template(attribute_template_id)
        return JSONResponse(
            status_code=200,
            content={
                "message": "Attribute template deleted successfully.",
            },
        )
    except ApiException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"error": e.user_message, "detail": e.tech_message},
        )
