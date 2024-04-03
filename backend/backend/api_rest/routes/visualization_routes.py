from fastapi import APIRouter, Request, BackgroundTasks, Depends
from ..utils.api_features import api_route
from ..controllers.visualization_controller import visualize_ion_focus
from ..models.pydantic_models.visualization_pydantic_model import (
    GetVisualizationIonFocusQueryParams,
)

visualization_router = APIRouter()


@visualization_router.get("/api/visualization/ion_focus")
@api_route(
    include_data=False,
    include_message=True,
    success_message="Visualizing target ion target in sample started.",
)
async def visualization_ion_focus_route(
    request: Request,
    background_tasks: BackgroundTasks,
    query_params: GetVisualizationIonFocusQueryParams = Depends(),
):
    sid = request.headers.get("X-SID")
    background_tasks.add_task(
        visualize_ion_focus,
        **query_params.dict(),
        independent_transaction=True,
        sid=sid,
    )
