from typing import List, Optional
from pydantic import BaseModel, Field, validator
from .target_compound_pydantic_model import TargetCompoundBase, TargetCompoundUpdate
from .match_pydantic_model import MatchComputeBatch

# TODO_configuration possible collection types
APP_COLLECTION_TYPES = ["TARGETS", "DIAGNOSTICS", "CALIBRANTS"]


class TargetCollectionBase(BaseModel):
    target_collection_name: str = Field(
        ..., description="Name of the target collection"
    )
    target_collection_description: str = Field(
        "", description="Description of the target collection"
    )
    target_collection_type: str = Field(
        ..., description="Type of the target collection"
    )

    @validator("target_collection_type")
    def check_collection_type(cls, item):
        if item not in APP_COLLECTION_TYPES:
            allowed_types = ", ".join(APP_COLLECTION_TYPES)
            raise ValueError(
                f"{item} is not a valid target_collection_type. Allowed types are {allowed_types}."
            )
        return item


class TargetCollectionCreate(TargetCollectionBase):
    target_compounds: Optional[List[TargetCompoundBase]] = Field(
        None, description="Compounds in the target collection"
    )
    sample_batches: Optional[List[MatchComputeBatch]] = Field(
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
