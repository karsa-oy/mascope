from fastapi import APIRouter
from ..controllers.target_compounds_controller import (
    get_target_compound_by_id,
    get_target_compounds,
    delete_target_compound,
)

target_compounds_router = APIRouter()


@target_compounds_router.get("/api/target_compounds")
async def get_target_compounds_route(
    target_compound_name: str = None,
    target_compound_formula: str = None,
    sort: str = None,
    order: str = None,
    page: int = 0,
    limit: int = 100,
):
    return await get_target_compounds(
        target_compound_name, target_compound_formula, sort, order, page, limit
    )


@target_compounds_router.get("/api/target_compounds/{target_compound_id}")
async def get_target_compound_by_id_route(target_compound_id: str):
    return await get_target_compound_by_id(target_compound_id)


@target_compounds_router.delete("/api/target_compounds/{target_compound_id}")
async def delete_target_compound_route(target_compound_id: str):
    return await delete_target_compound(target_compound_id)
