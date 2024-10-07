from fastapi import APIRouter, Request, BackgroundTasks, Depends
from mascope_server.db.id import gen_id
from mascope_server.api.lib.api_features import api_route
from mascope_server.api.controllers.sample.items.sample_items_controller import (
    get_sample_item,
)
from mascope_server.api.controllers.target.ions.target_ions_controller import (
    get_target_ion,
)
from mascope_server.api.controllers.visualization.visualization_controller import (
    visualize_ion_focus,
)
from mascope_server.api.models.visualization.visualization_pydantic_model import (
    GetVisualizationIonFocusQueryParams,
)

visualization_router = APIRouter()


@visualization_router.get("/api/visualization/ion_focus")
@api_route(
    status_code=202,
)
async def visualization_ion_focus_route(
    request: Request,
    background_tasks: BackgroundTasks,
    query_params: GetVisualizationIonFocusQueryParams = Depends(),
):
    # Verify the existance
    sample = await get_sample_item(query_params.sample_item_id)
    sample_item_name = sample["sample_item_name"]
    ion = await get_target_ion(query_params.target_ion_id)
    target_ion_formula = ion["target_ion_formula"]

    # Get data for notifications
    sid = request.headers.get("X-SID")
    process_id = gen_id(8)

    background_tasks.add_task(
        visualize_ion_focus,
        **query_params.model_dump(),
        independent_transaction=True,
        sid=sid,
        process_id=process_id,
    )

    return {
        "message": f"Visualizing target ion '{target_ion_formula}' in sample '{sample_item_name}', please wait.",
        "process_id": process_id,
    }
