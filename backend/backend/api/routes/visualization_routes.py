from fastapi import APIRouter, Request, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from ..controllers.visualization_controller import visualize_ion_focus
from ..exceptions import ApiException

visualization_router = APIRouter()


@visualization_router.get("/api/visualization/ion_focus")
async def visualization_ion_focus_route(
    request: Request,
    background_tasks: BackgroundTasks,
    sample_item_id: str = Query(..., description="ID of the sample item"),
    target_ion_id: str = Query(..., description="ID of the target ion"),
    min_isotope_abundance: float = Query(
        ...,
        description="Minimum relative abundance of isotopes to consider in the match.",
    ),
    peak_min_intensity: float = Query(
        ..., description="Minimum peak intensity threshold for considering a match."
    ),
    mz_tolerance: int = Query(
        ..., description="Tolerance for mass-to-charge ratio (m/z) error."
    ),
):
    try:
        sid = request.headers.get("X-SID")
        background_tasks.add_task(
            visualize_ion_focus,
            sid,
            sample_item_id,
            target_ion_id,
            min_isotope_abundance,
            peak_min_intensity,
            mz_tolerance,
        )
        return JSONResponse(
            status_code=200,
            content={
                "message": f"Visualizing target ion '{target_ion_id}' in sample '{sample_item_id}'.",
            },
        )
    except ApiException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"error": e.user_message, "detail": e.tech_message},
        )
