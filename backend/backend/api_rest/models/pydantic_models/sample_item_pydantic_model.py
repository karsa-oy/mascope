from pydantic import BaseModel, Field
from typing import Optional, Dict
from datetime import timezone, datetime as dt


class SampleItemBase(BaseModel):
    sample_batch_id: str = Field(..., description="ID of the associated sample batch")
    filename: str = Field(..., description="Name of the sample file")
    sample_item_name: str = Field(..., description="Name of the sample item")
    sample_item_type: str = Field(..., description="Type of the sample item")
    sample_item_attributes: Dict = Field(
        ..., description="Attributes of the sample item"
    )
    filter_id: Optional[str] = Field(None, description="Filter ID of the sample item")


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
