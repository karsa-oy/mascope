from typing import List
from fastapi import APIRouter, Depends
from mascope_server.api.lib.api_features import api_route
from mascope_server.api.controllers.target.compounds.target_compounds_controller import (
    get_target_compounds,
    get_target_compound,
    create_target_compound,
    delete_target_compound,
    update_target_compound,
)
from mascope_server.api.models.target.compounds.target_compound_pydantic_model import (
    TargetCompoundBase,
    TargetCompoundUpdate,
    GetTargetCompoundsQueryParams,
)

# TODO_target_compound_management refactor to send the same result as as other routes

target_compounds_router = APIRouter()


@target_compounds_router.get("/api/target/compounds")
@api_route()
async def get_target_compounds_route(
    query_params: GetTargetCompoundsQueryParams = Depends(),
):
    return await get_target_compounds(**query_params.model_dump())


@target_compounds_router.get("/api/target/compounds/{target_compound_id}")
@api_route()
async def get_target_compound_route(target_compound_id: str):
    return await get_target_compound(target_compound_id)


@target_compounds_router.post("/api/target/compounds")
@api_route(
    status_code=201,
    include_message=True,
    success_message="Target compounds created successfully",
)
async def create_target_compounds_route(target_compounds: List[TargetCompoundBase]):
    result = await create_target_compound(
        target_compounds=target_compounds,
        independent_transaction=True,
    )
    response = {
        "created_compounds_count": len(result["created_compounds"]),
        "created_compounds": result["created_compounds"],
        "existing_compounds_count": len(result["existing_compounds"]),
        "existing_compounds": result["existing_compounds"],
        "message-logs": result["message_logs"],
    }
    return response


@target_compounds_router.patch("/api/target/compounds")
@api_route(
    include_message=True,
    success_message="Target compounds updated successfully",
)
async def update_target_compound_route(
    target_compounds: List[TargetCompoundUpdate],
):
    result = await update_target_compound(target_compounds)
    response = {
        "not_changed_compounds_count": len(result["not_changed_compounds"]),
        "not_changed_compounds": result["not_changed_compounds"],
        "updated_compounds_count": len(result["updated_compounds"]),
        "updated_compounds": result["updated_compounds"],
        "not_updated_compounds_count": len(result["not_updated_compounds"]),
        "not_updated_compounds": result["not_updated_compounds"],
        "existing_compounds_count": len(result["existing_compounds"]),
        "existing_compounds": result["existing_compounds"],
        "message-logs": result["message_logs"],
    }
    return response


@target_compounds_router.delete("/api/target/compounds/{target_compound_id}")
@api_route(
    include_data=False,
    include_message=True,
    success_message="Target compound deleted successfully",
)
async def delete_target_compound_route(target_compound_id: str):
    return await delete_target_compound(
        target_compound_id=target_compound_id,
        independent_transaction=True,
    )
