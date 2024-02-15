from pydantic import BaseModel, Field, validator
from typing import Optional, Dict
from datetime import timezone, datetime as dt

# TODO_configuration possible item types
APP_ITEM_TYPES = [
    "FILTER_REGENERATION",
    "FILTER_BACKGROUND",
    "INSTRUMENT_BACKGROUND",
    "BLANK",
    "SAMPLE",
    "UNKNOWN",
]


class SampleItemBase(BaseModel):
    sample_batch_id: str = Field(..., description="ID of the associated sample batch")
    filename: str = Field(..., description="Name of the sample file")
    sample_item_name: str = Field(..., description="Name of the sample item")
    sample_item_type: str = Field(..., description="Type of the sample item")
    sample_item_attributes: Dict = Field(
        ..., description="Attributes of the sample item"
    )
    filter_id: Optional[str] = Field(None, description="Filter ID of the sample item")

    @validator("sample_item_type")
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


class SampleItemCopyBody(BaseModel):
    sample_batch_id: str = Field(
        ..., description="ID of the sample batch where to copy sample item"
    )
    sample_item_name: str = Field(..., description="Name of the new sample item")
    independent_transaction: Optional[bool] = Field(
        default=True,
        description="Flag indicating whether the sample item copy is an independent transaction and if the operation should emit a reload event for the sample batch and if the sample should be rematched for new batch targets.",
    )
