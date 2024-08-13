import re
from typing import Optional, Dict
from pydantic import BaseModel, Field, field_validator, model_validator
from mascope_server.api.models.calibration.calibration_pydantic_model import (
    CalibrationMzFitParams,
)

# TODO_configuration possible item types
APP_ITEM_TYPES = [
    "FILTER_REGENERATION",
    "FILTER_BACKGROUND",
    "INSTRUMENT_BACKGROUND",
    "BLANK",
    "SAMPLE",
    "UNKNOWN",
    "ONLINE",  # At the moment not selectable from the UI
]

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
    filter_id: Optional[str] = Field(None, description="Filter ID of the sample item")

    @model_validator(mode="after")
    @classmethod
    def check_filter_id_based_on_item_type(cls, values):
        item_type, filter_id = values.sample_item_type, values.filter_id
        if item_type in ["INSTRUMENT_BACKGROUND", "ONLINE"] and filter_id is not None:
            raise ValueError(
                f"There must be no filter_id for sample type '{item_type}'"
            )
        elif item_type not in ["INSTRUMENT_BACKGROUND", "ONLINE"] and filter_id is None:
            raise ValueError(
                f"The filter_id must be provided for sample type '{item_type}'"
            )
        if filter_id and not re.match(FILTER_ID_REGEX, filter_id):
            raise ValueError(
                "Invalid filter_id format. Must be 6 characters long and contain only uppercase letters and numbers."
            )
        return values

    @field_validator("sample_item_type")
    @classmethod
    def check_item_type(cls, item):
        if item not in APP_ITEM_TYPES:
            allowed_types = ", ".join(APP_ITEM_TYPES)
            raise ValueError(
                f"{item} is not a valid sample_item_type. Allowed types are {allowed_types}."
            )
        return item


class SampleItemCreate(SampleItemBase):
    pass


class SampleItemUpdate(SampleItemBase):
    pass


class GetSampleItemsQueryParams(BaseModel):
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


class SampleItemCopyBody(BaseModel):
    sample_batch_id: str = Field(
        ..., description="ID of the sample batch where to copy sample item"
    )
    sample_item_name: str = Field(..., description="Name of the new sample item")


class SampleItemProcessBody(BaseModel):
    sample_item: SampleItemCreate = Field(
        ..., description="Sample item to be processed (created, calibrated, matched)"
    )
    mz_calibration_params: CalibrationMzFitParams = CalibrationMzFitParams()
