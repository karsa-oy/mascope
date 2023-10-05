from fastapi import APIRouter, BackgroundTasks
from typing import List
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
    CalibrationMzCalibrateBatchData,
)

calibration_router = APIRouter()


@calibration_router.post("/api/calibration/mz_apply")
async def calibration_mz_apply_route(data: CalibrationMzApplyData):
    return await calibration_mz_apply(data.fit, data.sample_filename)


@calibration_router.get("/api/calibration/last_mz_calibration")
async def get_last_mz_calibration_route(
    instrument: str,
):
    return await get_mz_calibration(instrument=instrument)


@calibration_router.get("/api/calibration/sample_mz_calibration/{sample_item_id}")
async def get_sample_mz_calibration_route(
    sample_item_id: str,
):
    return await get_mz_calibration(sample_item_id=sample_item_id)


@calibration_router.post("/api/calibration/mz_fit/{sample_item_id}")
async def calibration_mz_fit_route(
    sample_item_id: str,
    params: CalibrationMzFitParams,
    background_tasks: BackgroundTasks,
):
    return await calibration_mz_fit(sample_item_id, params, background_tasks)


@calibration_router.post("/api/calibration/mz_calibrate/sample")
async def calibration_mz_calibrate_sample_route(
    sample_item: dict,
    params: CalibrationMzFitParams,
    background_tasks: BackgroundTasks,
):
    return await calibration_mz_calibrate_sample(sample_item, params, background_tasks)


@calibration_router.post("/api/calibration/mz_calibrate/batch")
async def calibration_mz_calibrate_batch_route(data: CalibrationMzCalibrateBatchData):
    return await calibration_mz_calibrate_batch(
        data.sample_batch, data.sample_items, data.params
    )
