from fastapi import APIRouter, BackgroundTasks, Query, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from ..exceptions import ApiException

from ..controllers.calibration_controller import (
    get_mz_calibration,
    calibration_mz_fit,
    calibration_mz_apply,
    calibration_mz_calibrate_sample,
    calibration_mz_calibrate_batch,
)
from ..models.pydantic_models.calibration_pydantic_model import (
    CalibrationMzFitParams,
    CalibrationMzApplyData,
    CalibrationMzCalibrateBody,
)

calibration_router = APIRouter()


@calibration_router.get("/api/calibration/mz_calibration")
async def get_sample_mz_calibration_route(
    sample_item_id: str = Query(
        None, description="The sample item ID to query for sample mz_calibration"
    ),
    instrument: str = Query(
        None,
        description="The instrument name to query for the last mz_calibration of that instrument",
    ),
):
    if (sample_item_id and instrument) or (not sample_item_id and not instrument):
        raise HTTPException(
            status_code=400,
            detail="Must provide either instrument either sample_item_id.",
        )
    return await get_mz_calibration(
        instrument=instrument, sample_item_id=sample_item_id
    )


@calibration_router.post("/api/calibration/mz_fit")
async def calibration_mz_fit_route(
    params: CalibrationMzFitParams,
    background_tasks: BackgroundTasks,
    sample_item_id: str = Query(
        ..., description="The sample item ID to query for sample mz_calibration"
    ),
):
    return await calibration_mz_fit(sample_item_id, params, background_tasks)


@calibration_router.post("/api/calibration/mz_apply")
async def calibration_mz_apply_route(
    data: CalibrationMzApplyData,
    sample_filename: str = Query(
        ..., description="The sample filename to query for sample mz_apply"
    ),
):
    return await calibration_mz_apply(data.fit, sample_filename)


@calibration_router.post("/api/calibration/mz_calibrate/sample/{sample_item_id}")
async def calibration_mz_calibrate_sample_route(
    request: Request,
    sample_item_id: str,
    body: CalibrationMzCalibrateBody,
    background_tasks: BackgroundTasks,
):
    sid = request.headers.get("X-SID")
    background_tasks.add_task(
        calibration_mz_calibrate_sample,
        sample_item_id,
        body.params,
    )
    return JSONResponse(
        status_code=200,
        content={
            "message": f"Sample '{sample_item_id}' m/z calibration has started, please wait for completion.",
        },
    )


@calibration_router.post("/api/calibration/mz_calibrate/batch/{sample_batch_id}")
async def calibration_mz_calibrate_batch_route(
    request: Request,
    sample_batch_id: str,
    body: CalibrationMzCalibrateBody,
    background_tasks: BackgroundTasks,
):
    sid = request.headers.get("X-SID")
    background_tasks.add_task(
        calibration_mz_calibrate_batch,
        sample_batch_id,
        body.params,
        body.independent_transaction,
    )
    return JSONResponse(
        status_code=200,
        content={
            "message": f"Sample batch '{sample_batch_id}' m/z calibration has started, please wait for completion.",
        },
    )
