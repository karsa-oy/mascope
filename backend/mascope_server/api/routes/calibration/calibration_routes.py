from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request
from mascope_server.db.id import gen_id
from mascope_server.api.lib.api_features import api_route
from mascope_server.api.lib.exceptions.api_exceptions import NotFoundException

from mascope_server.api.controllers.sample.items.sample_items_controller import (
    get_sample_item,
)
from mascope_server.api.controllers.sample.files.sample_files_controller import (
    get_sample_files,
)
from mascope_server.api.controllers.sample.batches.sample_batches_controller import (
    get_sample_batch,
)
from mascope_server.api.controllers.calibration.calibration_controller import (
    get_mz_calibration,
    calibration_mz_fit,
    calibration_mz_apply,
    calibration_mz_calibrate_sample,
    calibration_mz_calibrate_batch,
)
from mascope_server.api.models.calibration.calibration_pydantic_model import (
    GetMzCalibrationQueryParams,
    CalibrationMzFitParams,
    CalibrationMzApplyBody,
)

calibration_router = APIRouter()


@calibration_router.get("/api/calibration/mz_calibration")
@api_route()
async def get_sample_mz_calibration_route(
    query_params: GetMzCalibrationQueryParams = Depends(),
):
    return await get_mz_calibration(**query_params.model_dump())


@calibration_router.post("/api/calibration/mz_fit")
@api_route(
    status_code=202,
)
async def calibration_mz_fit_route(
    request: Request,
    body: CalibrationMzFitParams,
    background_tasks: BackgroundTasks,
    sample_item_id: str = Query(
        ..., description="The sample item ID to query for sample mz_calibration"
    ),
):
    # Verify the existance of sample item
    sample = await get_sample_item(sample_item_id)
    sample_item_name = sample["sample_item_name"]

    # Get data for notifications
    sid = request.headers.get("X-SID")
    process_id = gen_id(8)

    background_tasks.add_task(
        calibration_mz_fit,
        sample_item_id=sample_item_id,
        params=body,
        independent_transaction=True,
        sid=sid,
        process_id=process_id,
    )
    return {
        "message": f"Started to m/z fit sample '{sample_item_name}', please wait.",
        "process_id": process_id,
    }


@calibration_router.post("/api/calibration/mz_apply")
@api_route(
    status_code=202,
)
async def calibration_mz_apply_route(
    request: Request,
    body: CalibrationMzApplyBody,
    background_tasks: BackgroundTasks,
    filename: str = Query(..., description="The filename to aply m/z fit"),
):
    # Verify the existance of sample file
    sample_file_data = await get_sample_files(filename=filename)
    if not sample_file_data["data"][0]:
        raise NotFoundException(f"Sample file '{filename}' not found")

    # Get data for notifications
    sid = request.headers.get("X-SID")
    process_id = gen_id(8)

    background_tasks.add_task(
        calibration_mz_apply,
        filename=filename,
        fit=body.fit,
        independent_transaction=True,
        sid=sid,
        process_id=process_id,
    )
    return {
        "message": f"Started to apply m/z fit for sample file '{filename}', please wait.",
        "process_id": process_id,
    }


@calibration_router.post("/api/calibration/mz_calibrate/sample/{sample_item_id}")
@api_route(
    status_code=202,
)
async def calibration_mz_calibrate_sample_route(
    request: Request,
    sample_item_id: str,
    body: CalibrationMzFitParams,
    background_tasks: BackgroundTasks,
):
    # Verify the existance of sample item
    sample = await get_sample_item(sample_item_id)
    sample_item_name = sample["sample_item_name"]

    # Get data for notifications
    sid = request.headers.get("X-SID")
    process_id = gen_id(8)

    background_tasks.add_task(
        calibration_mz_calibrate_sample,
        sample_item_id=sample_item_id,
        params=body,
        independent_transaction=True,
        sid=sid,
        process_id=process_id,
    )
    return {
        "message": f"Started to m/z calibrate sample '{sample_item_name}', please wait.",
        "process_id": process_id,
    }


@calibration_router.post("/api/calibration/mz_calibrate/batch/{sample_batch_id}")
@api_route(
    status_code=202,
)
async def calibration_mz_calibrate_batch_route(
    request: Request,
    sample_batch_id: str,
    body: CalibrationMzFitParams,
    background_tasks: BackgroundTasks,
):
    # Verify the existance of sample batch
    sample_batch = await get_sample_batch(sample_batch_id)
    sample_batch_name = sample_batch["sample_batch_name"]

    # Get data for notifications
    sid = request.headers.get("X-SID")
    process_id = gen_id(8)

    background_tasks.add_task(
        calibration_mz_calibrate_batch,
        sample_batch_id=sample_batch_id,
        params=body,
        independent_transaction=True,
        sid=sid,
        process_id=process_id,
    )
    return {
        "message": f"Started to m/z calibrate sample batch '{sample_batch_name}', please wait.",
        "process_id": process_id,
    }
