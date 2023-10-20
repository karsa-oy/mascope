from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from .calibration_pydantic_model import CalibrationMzFitParams


class SampleBatchBase(BaseModel):
    workspace_id: str = Field(
        ..., description="ID of the workspace associated with the sample batch"
    )
    sample_batch_name: str = Field(..., description="Name of the sample batch")
    sample_batch_description: Optional[str] = Field(
        None, description="Description of the sample batch"
    )
    build_params: Dict[str, Any] = Field(
        ..., description="Build parameters of the sample batch"
    )
    filter_params: Dict[str, Any] = Field(
        ..., description="Filter parameters of the sample batch"
    )


class SampleBatchCreate(SampleBatchBase):
    target_collection_id: List[str] = Field(
        ..., description="IDs of target collections associated with the sample batch"
    )


class SampleBatchUpdate(SampleBatchBase):
    sample_batch_name: Optional[str] = Field(
        None, description="Name of the sample batch"
    )
    target_collection_id: List[str] = Field(
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


class SampleBatchCopy(BaseModel):
    sample_batch_id: str = Field(..., description="ID of the sample batch to be copied")
    workspace_id: str = Field(
        ..., description="ID of the workspace where to copy the batch"
    )
    sample_batch_name: str = Field(..., description="Name of the new sample batch")
    sample_batch_description: Optional[str] = Field(
        None, description="Description of the new sample batch"
    )
