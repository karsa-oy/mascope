from typing import List, Optional
from pydantic import BaseModel, Field
from .target_compound_pydantic_model import TargetCompoundBase, TargetCompoundUpdate


class TargetCollectionBase(BaseModel):
    target_collection_name: str = Field(
        ..., description="Name of the target collection"
    )
    target_collection_description: Optional[str] = Field(
        None, description="Description of the target collection"
    )


class TargetCollectionCreate(TargetCollectionBase):
    target_compounds: Optional[List[TargetCompoundBase]] = Field(
        None, description="Compounds in the target collection"
    )
    sample_batches: Optional[List[str]] = Field(
        None, description="List of sample batch ids related to the target collection"
    )


class TargetCollectionUpdate(TargetCollectionBase):
    compounds_to_add: List[TargetCompoundUpdate] = Field(
        [], description="List of compounds to add to the target collection"
    )
    compounds_to_remove: List[TargetCompoundUpdate] = Field(
        [], description="List of compounds to remove from the target collection"
    )


class TargetCollectionInDB(TargetCollectionBase):
    target_collection_id: str = Field(..., description="ID of the target collection")

    class Config:
        orm_mode = True
