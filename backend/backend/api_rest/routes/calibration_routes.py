from fastapi import APIRouter
from ..controllers.calibration_controller import calibration_mz_apply
from typing import List

calibration_router = APIRouter()


@calibration_router.post("/api/calibration/mz_apply")
async def calibration_mz_apply_route(fit: dict, sample_filenames: List[str]):
    return await calibration_mz_apply(fit, sample_filenames)
