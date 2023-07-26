from typing import Optional
from pydantic import BaseModel, Field


class TargetIonBase(BaseModel):
    target_ion_id: Optional[str] = Field(None, description="ID of the target ion")
    target_compound_id: str = Field(..., description="ID of the target compound")
    ionization_mechanism_id: str = Field(
        ..., description="ID of the ionization mechanism"
    )
    target_ion_formula: str = Field(..., description="Formula of the target ion")
