from typing import List, Optional
from pydantic import BaseModel, Field
from .target_compound_pydantic_model import TargetCompoundBase

# class TargetCompoundBase(BaseModel):
#     target_compound_id: Optional[str] = Field(
#         None, description="ID of the target compound"
#     )
#     target_compound_name: str = Field(..., description="Name of the target compound")
#     target_compound_formula: str = Field(
#         ..., description="Formula of the target compound"
#     )
#     cas_number: Optional[str] = Field(
#         None, description="CAS Number of the target compound"
#     )


class TargetCollectionBase(BaseModel):
    target_collection_name: str = Field(
        ..., description="Name of the target collection"
    )
    target_collection_description: Optional[str] = Field(
        None, description="Description of the target collection"
    )


class TargetCollectionCreate(TargetCollectionBase):
    target_compounds: List[TargetCompoundBase] = Field(
        ..., description="Compounds in the target collection"
    )
    sample_batches: Optional[List[str]] = Field(
        None, description="List of sample batch ids related to the target collection"
    )


class TargetCollectionInDB(TargetCollectionBase):
    target_collection_id: str = Field(..., description="ID of the target collection")

    class Config:
        orm_mode = True
