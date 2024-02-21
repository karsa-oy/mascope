from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from .calibration_pydantic_model import CalibrationMzFitParams


class BuildParams(BaseModel):
    calibration_collection: str = Field(
        ..., description="ID of the calibration collection"
    )
    ion_mechanisms: List[str] = Field(..., description="List of ion mechanism IDs")

    @validator("calibration_collection")
    def check_calibration_collection_length(cls, v):
        if len(v) != 16:
            raise ValueError("Only one calibration collection can be applied")
        return v

    @validator("ion_mechanisms")
    def check_ion_mechanisms_non_empty(cls, v):
        if len(v) == 0:
            raise ValueError("At least one ionization mechanism must be provided")
        return v


class SampleBatchBase(BaseModel):
    workspace_id: str = Field(
        ..., description="ID of the workspace associated with the sample batch"
    )
    sample_batch_name: str = Field(..., description="Name of the sample batch")
    sample_batch_description: Optional[str] = Field(
        "", description="Description of the sample batch"
    )
    build_params: BuildParams = Field(
        ..., description="Build parameters of the sample batch"
    )


class SampleBatchCreateBody(SampleBatchBase):
    target_collection_ids: List[str] = Field(
        ..., description="IDs of target collections associated with the sample batch"
    )


class SampleBatchUpdateBody(SampleBatchBase):
    target_collection_ids: List[str] = Field(
        ..., description="IDs of target collections associated with the sample batch"
    )


class SampleBatchInDB(SampleBatchBase):
    sample_batch_id: str = Field(..., description="ID of the sample batch")
    sample_batch_utc_created: Optional[str] = Field(
        None, description="Creation timestamp of the sample batch"
    )
    sample_batch_utc_modified: Optional[str] = Field(
        None, description="Last modification timestamp of the sample batch"
    )

    class Config:
        orm_mode = True


class autoSamplerImportBatchData(BaseModel):
    sample_batch: dict
    sample_items: List[dict]
    params: CalibrationMzFitParams = CalibrationMzFitParams()


class SampleBatchCopyBody(BaseModel):
    workspace_id: str = Field(
        ..., description="ID of the workspace where to copy the batch"
    )
    sample_batch_name: str = Field(..., description="Name of the new sample batch")
    sample_batch_description: Optional[str] = Field(
        None, description="Description of the new sample batch"
    )


class SampleBatchExportPeaks(BaseModel):
    sample_batch_id: str = Field(..., description="ID of the sample batch")
    sample_batch_name: str = Field(..., description="Name of the sample batch")
