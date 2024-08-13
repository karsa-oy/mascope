from typing import Optional, List
from mascope_lib.file_func import get_instrument_type
from pydantic import BaseModel, Field, field_validator, model_validator
from mascope_server.api.models.calibration.calibration_pydantic_model import (
    CalibrationMzFitParams,
)
from mascope_server.api.models.sample.items.sample_item_pydantic_model import (
    SampleItemCreate,
)


class BuildParams(BaseModel):
    calibration_collection: str = Field(
        ..., description="ID of the calibration collection"
    )
    ion_mechanisms: List[str] = Field(
        ..., description="List of ionisation mechanism IDs"
    )

    @field_validator("calibration_collection")
    @classmethod
    def check_calibration_collection_length(cls, v):
        if len(v) != 16:
            raise ValueError("Only one calibration collection can be applied")
        return v

    @field_validator("ion_mechanisms")
    @classmethod
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


class GetSampleBatchesQueryParams(BaseModel):
    workspace_id: Optional[str] = Field(
        None,
        description="Filter by the workspace ID for which you want to fetch the sample batches.",
    )
    sort: Optional[str] = Field(
        "sample_batch_utc_created",
        description="Column name by which you want to sort the results. The column name should be one of the columns in the sample batch table.",
    )
    order: Optional[str] = Field(
        "asc",
        description="Sorting order which can be asc for ascending or desc for descending.",
    )
    page: int = Field(0, description="Page number for pagination.")
    limit: int = Field(10000, description="Number of results per page.")


class SampleBatchImportSamplesBody(BaseModel):
    sample_items: List[SampleItemCreate] = Field(
        ..., description="Sample items to be created and imported to the sample batch"
    )
    params: CalibrationMzFitParams = CalibrationMzFitParams()
    calibrate_batch: bool = Field(
        default=True,
        description="Flag to control whether the batch should be calibrated.",
    )

    @model_validator(mode="after")
    @classmethod
    def check_sample_items(cls, values):
        sample_items = values.sample_items
        batch_ids = {item.sample_batch_id for item in sample_items}
        instruments = set(get_instrument_type(item.filename) for item in sample_items)
        if len(batch_ids) > 1:
            raise ValueError(
                "All samples should be imported to the same batch, please check if the sample batch ID is the same for all importing samples."
            )
        if len(instruments) > 1:
            raise ValueError(
                "Importing samples from different instruments is not supported, please import samples for each instrument separately."
            )
        return values


class SampleBatchCopyBody(BaseModel):
    workspace_id: str = Field(
        ..., description="ID of the workspace where to copy the batch"
    )
    sample_batch_name: str = Field(..., description="Name of the new sample batch")
    sample_batch_description: Optional[str] = Field(
        None, description="Description of the new sample batch"
    )
