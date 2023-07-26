from typing import Optional
from pydantic import BaseModel, Field


class TargetIsotopeBase(BaseModel):
    target_isotope_id: Optional[str] = Field(
        None, description="ID of the target isotope"
    )
    target_ion_id: str = Field(..., description="ID of the target ion")
    mz: float = Field(..., description="m/z value of the target isotope")
    relative_abundance: float = Field(
        ..., description="Relative abundance of the target isotope"
    )
