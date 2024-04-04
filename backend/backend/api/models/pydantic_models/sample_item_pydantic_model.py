from pydantic import BaseModel, Field, validator, root_validator
from typing import Optional, Dict
from datetime import timezone, datetime as dt
import re

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

    @root_validator
    def check_filter_id_based_on_item_type(cls, values):
        item_type = values.get("sample_item_type")
        filter_id = values.get("filter_id")
        if item_type in ["INSTRUMENT_BACKGROUND", "ONLINE"] and filter_id is not None:
            raise ValueError(
                f"There must be no filter_id for sample type '{item_type}'"
            )
        elif item_type not in ["INSTRUMENT_BACKGROUND", "ONLINE"] and filter_id is None:
            raise ValueError(
                f"The filter_id must be provided for sample type '{item_type}'"
            )
        return values

    @validator("sample_item_type")
    def check_item_type(cls, item):
        if item not in APP_ITEM_TYPES:
            allowed_types = ", ".join(APP_ITEM_TYPES)
            raise ValueError(
                f"{item} is not a valid sample_item_type. Allowed types are {allowed_types}."
            )
        return item

    @validator("filter_id", always=True)
    def validate_filter_id(cls, v, values, **kwargs):
        item_type = values.get("sample_item_type")
        # Only validate filter_id if it's required and provided
        if item_type not in ["INSTRUMENT_BACKGROUND", "ONLINE"] and v:
            if not re.match(FILTER_ID_REGEX, v):
                raise ValueError(
                    "Invalid filter_id format. Must be 6 characters long and contain only uppercase letters and numbers."
                )
        return v


class SampleItemCreate(SampleItemBase):
    pass


class SampleItemUpdate(SampleItemBase):
    pass


class SampleItemInDB(SampleItemBase):
    sample_item_id: str = Field(..., description="ID of the sample item")
    sample_item_utc_created: dt = Field(
        ..., description="Creation timestamp of the sample item"
    )
    sample_item_utc_modified: dt = Field(
        ..., description="Last modification timestamp of the sample item"
    )

    class Config:
        orm_mode = True
        # datetime and datetime_utc fields will be represented in the ISO 8601 format in response
        json_encoders = {
            dt: lambda v: v.replace(tzinfo=timezone.utc).isoformat(timespec="seconds")
        }


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
