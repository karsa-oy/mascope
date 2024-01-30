from typing import List, Optional

from fastapi import APIRouter
from ..controllers.target_compounds_controller import (
    get_target_compound_by_id,
    get_target_compounds,
    create_target_compound,
    delete_target_compound,
    update_target_compound,
)
from ..models.pydantic_models.target_compound_pydantic_model import (
    TargetCompoundBase,
    TargetCompoundUpdate,
)

target_compounds_router = APIRouter()


@target_compounds_router.get("/api/target_compounds")
async def get_target_compounds_route(
    target_compound_name: Optional[str] = None,
    target_compound_formula: Optional[str] = None,
    sample_batch_id: Optional[str] = None,
    sort: str = None,
    order: str = None,
    page: int = 0,
    limit: int = 100,
):
    return await get_target_compounds(
        target_compound_name,
        target_compound_formula,
        sample_batch_id,
        sort,
        order,
        page,
        limit,
    )


@target_compounds_router.get("/api/target_compounds/{target_compound_id}")
async def get_target_compound_by_id_route(target_compound_id: str):
    return await get_target_compound_by_id(target_compound_id)


@target_compounds_router.delete("/api/target_compounds/{target_compound_id}")
async def delete_target_compound_route(target_compound_id: str):
    return await delete_target_compound(target_compound_id)


@target_compounds_router.post("/api/target_compounds")
async def create_target_compounds_route(target_compounds: List[TargetCompoundBase]):
    result = await create_target_compound(target_compounds)
    response = {
        "created_compounds_count": len(result["created_compounds"]),
        "created_compounds": result["created_compounds"],
        "existing_compounds_count": len(result["existing_compounds"]),
        "existing_compounds": result["existing_compounds"],
        "message-logs": result["message_logs"],
    }
    return response


@target_compounds_router.patch("/api/target_compounds")
async def update_target_compound_route(target_compounds: List[TargetCompoundUpdate]):
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
