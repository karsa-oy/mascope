from pydantic import BaseModel, Field
from typing import Optional, Dict
from .sample_pydantic_model import FilterParams


class TargetIonUpdate(BaseModel):
    filter_params: Dict[str, FilterParams] = Field(
        None, description="Ion-specific filter parameters"
    )
    delete_instrument_filters: Optional[str] = Field(
        None, description="Instrument name which filter parameteres to delete"
    )

    class Config:
        orm_mode = True
