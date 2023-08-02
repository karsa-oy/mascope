from typing import Optional
from pydantic import BaseModel, Field


class TargetCompoundBase(BaseModel):
    target_compound_id: Optional[str] = Field(
        None, description="ID of the target compound"
    )
    target_compound_name: str = Field(..., description="Name of the target compound")
    target_compound_formula: str = Field(
        ..., description="Formula of the target compound"
    )
    cas_number: Optional[str] = Field(
        None, description="CAS Number of the target compound"
    )


class TargetCompoundUpdate(BaseModel):
    target_compound_id: str = Field(..., description="ID of the target compound")
    target_compound_name: str = Field(None, description="Name of the target compound")
    target_compound_formula: Optional[str] = Field(
        None, description="Formula of the target compound"
    )
    cas_number: Optional[str] = Field(
        None, description="CAS Number of the target compound"
    )
