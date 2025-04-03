import re
from typing import Optional, Dict
from pydantic import BaseModel, Field, field_validator, model_validator
from mascope_backend.api.models.calibration.calibration_pydantic_model import (
    MzCalibrationParams,
)
from mascope_backend.api.models.base_pydantic_model import QueryParamsModel
from mascope_backend.api.new.instrument_configs.schemas import (
    SetInstrumentConfigBody,
)

# TODO_configuration possible sample item types list, split by filter_id presence
SAMPLE_TYPES_FILTER_ID_REQUIRED = ["FILTER_REGENERATION", "FILTER_BACKGROUND"]
SAMPLE_TYPES_FILTER_ID_OPTIONAL = ["BLANK", "SAMPLE", "UNKNOWN"]
SAMPLE_TYPES_FILTER_ID_NOT_ALLOWED = ["INSTRUMENT_BACKGROUND", "ONLINE"]

# Regular expression for filter_id validation
FILTER_ID_REGEX = r"^[0-9A-Z]{6}$"


class SampleItemBase(BaseModel):
    sample_batch_id: str = Field(..., description="ID of the associated sample batch")
    filename: str = Field(..., description="Name of the sample file")
    sample_item_name: str = Field(..., description="Name of the sample item")
    sample_item_type: str = Field(..., description="Type of the sample item")
    sample_item_attributes: Dict = Field(
        ..., description="Attributes of the sample item"
    )
    filter_id: Optional[str] = Field(
        None, description="Optional filter_id of the sample item"
    )

    @field_validator("filter_id")
    @classmethod
    def validate_filter_id(cls, filter_id):
        if filter_id and not re.match(FILTER_ID_REGEX, filter_id):
            raise ValueError(
                "Invalid filter_id format. Must be 6 characters long and contain only uppercase letters and numbers."
            )
        return filter_id

    @field_validator("sample_item_type")
    @classmethod
    def validate_sample_item_type(cls, sample_type):
        """Ensure `sample_item_type` is one of the allowed types."""
        all_sample_types = (
            SAMPLE_TYPES_FILTER_ID_REQUIRED
            + SAMPLE_TYPES_FILTER_ID_OPTIONAL
            + SAMPLE_TYPES_FILTER_ID_NOT_ALLOWED
        )
        if sample_type not in all_sample_types:
            allowed_types = ", ".join(all_sample_types)
            raise ValueError(
                f"Invalid sample item type '{sample_type}'. Allowed types are: {allowed_types}."
            )
        return sample_type

    @model_validator(mode="after")
    @classmethod
    def validate_sample_item_type_based_on_filter_id(cls, values):
        """
        Validates sample_item_type options based on filter_id presence:
        - For types in SAMPLE_TYPES_FILTER_ID_REQUIRED, filter_id is mandatory.
        - For types in SAMPLE_TYPES_FILTER_ID_NOT_ALLOWED, filter_id must be absent.
        """
        sample_type, filter_id = values.sample_item_type, values.filter_id

        # Determine allowed types based on the presence or absence of filter_id
        if sample_type in SAMPLE_TYPES_FILTER_ID_REQUIRED and not filter_id:
            raise ValueError(f"Sample item type '{sample_type}' requires a filter ID.")
        elif sample_type in SAMPLE_TYPES_FILTER_ID_NOT_ALLOWED and filter_id:
            raise ValueError(
                f"Sample item type '{sample_type}' cannot have a filter ID."
            )

        return values


class SampleItemCreate(SampleItemBase):
    pass


class SampleItemUpdate(SampleItemBase):
    pass


class GetSampleItemsQueryParams(QueryParamsModel):
    sample_batch_id: Optional[str] = Field(
        None,
        description="The sample batch ID for which you want to fetch the sample items.",
    )
    filename: Optional[str] = Field(
        None, description="The filename for which you want to fetch the sample items."
    )
    sort: Optional[str] = Field(
        "sample_item_utc_created",
        description="The column name by which you want to sort the results. The column name should be one of the columns in the sample_Item table.",
    )
    order: Optional[str] = Field(
        "asc",
        description="Can either be asc for ascending order or desc for descending order.",
    )
    page: int = Field(0, description="The page number for pagination, default 0")
    limit: int = Field(10000, description="The number of results per page.")


class SampleItemUpdateBody(BaseModel):
    sample_item: SampleItemUpdate = Field(
        ..., description="The sample item fields to update"
    )
    instrument_config: SetInstrumentConfigBody | None = Field(
        None,
        description="An instrument config to set for the sample item.",
    )


class SampleItemsDeleteBody(BaseModel):
    sample_item_ids: list[str] = Field(
        ..., description="The sample item IDs of samples to be deleted"
    )


class SampleItemsCopyBody(BaseModel):
    sample_batch_id: str = Field(
        ..., description="ID of the sample batch where to copy sample items"
    )
    sample_item_ids: list[str] = Field(..., description="Sample item IDs to copy")


class SampleItemsMoveBody(BaseModel):
    sample_batch_id: str = Field(
        ..., description="ID of the sample batch where to move sample items"
    )
    sample_item_ids: list[str] = Field(..., description="Sample item IDs to move")


class SampleItemProcessBody(BaseModel):
    sample_item: SampleItemCreate = Field(
        ..., description="Sample item to be processed (created, calibrated, matched)"
    )
    instrument_config: SetInstrumentConfigBody = Field(
        ..., description="Instrument config to set for the sample item"
    )
    mz_calibration_params: MzCalibrationParams = MzCalibrationParams()
