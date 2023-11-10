from pydantic import BaseModel, Field
from typing import Optional, List


class MZCalibration(BaseModel):
    mode: int
    par: List = []
    verified: Optional[bool] = Field(
        False, description="Define if the sample was calibrated"
    )


class MatchComputeBatch(BaseModel):
    sample_batch_id: str = Field(..., description="ID of the sample batch")
    workspace_id: Optional[str] = Field(
        None, description="ID of the workspace associated with the sample batch"
    )


class MatchComputeItem(BaseModel):
    sample_item_id: str = Field(..., description="ID of the sample item")
    sample_item_name: str = Field(..., description="ID of the sample item")
    sample_batch_id: str = Field(..., description="ID of the sample batch")
    filename: str = Field(..., description="Filename of the sample item")
    instrument: str = Field(..., description="Instrument of the sample item")
    mz_calibration: MZCalibration = Field(..., description="mz calibration object")


class ProgressProperties(BaseModel):
    item_weight: Optional[float] = Field(
        None, description="Weight of the item in computation"
    )
    item_index: Optional[int] = Field(
        None, description="Index of the item being processed"
    )
    batch_index: Optional[int] = Field(
        None, description="Index of the batch being processed"
    )
    sample_batch_id: Optional[str] = Field(
        None, description="ID of the associated batch"
    )
    workspace_id: Optional[str] = Field(
        None, description="ID of the associated workspace"
    )
    total_samples: Optional[int] = Field(
        None, description="Total number of items to process"
    )
    total_batches: Optional[int] = Field(None, description="Total number of batches")
    progress_type: Optional[str] = Field(
        None,
        description="Type of progress computation ('match_batches' or 'match_item')",
    )
    sid: Optional[str] = Field(None, description="Session ID for the socket connection")
