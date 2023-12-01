from fastapi import APIRouter

from ..controllers.peaks_controller import (
    get_sample_file_peaks,
    get_sample_file_peak_timeseries,
)
from ..models.pydantic_models.peaks_pydantic_model import GetPeakTimeseriesBody

peaks_router = APIRouter()


@peaks_router.get("/api/peaks/{filename}")
async def get_peaks_by_filename_route(filename: str):
    return await get_sample_file_peaks(filename)


@peaks_router.post("/api/peak_timeseries")
async def get_peak_timeseries_route(body: GetPeakTimeseriesBody):
    return await get_sample_file_peak_timeseries(
        filename=body.filename,
        peak_mz=body.peak_mz,
        peak_mz_tolerance_ppm=body.peak_mz_tolerance_ppm,
    )
