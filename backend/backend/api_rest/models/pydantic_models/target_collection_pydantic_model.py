from typing import List, Optional
from pydantic import BaseModel, Field, validator, root_validator
from .target_compound_pydantic_model import TargetCompoundBase, TargetCompoundUpdate

# TODO_configuration possible collection types
APP_COLLECTION_TYPES = ["TARGETS", "DIAGNOSTICS", "CALIBRANTS"]


class TargetCollectionBase(BaseModel):
    target_collection_name: str = Field(
        ..., description="Name of the target collection"
    )
    target_collection_description: Optional[str] = Field(
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


class TargetCollectionCreateBody(TargetCollectionBase):
    target_compounds_create: Optional[List[TargetCompoundBase]] = Field(
        None, description="Compounds to be created and added to the target collection"
    )
    target_compound_ids: Optional[List[str]] = Field(
        None,
        description="IDs of already existing in DB target compounds to be associated with the target collection",
    )
    sample_batch_ids: Optional[List[str]] = Field(
        None, description="IDs of sample batches where to add the new target collection"
    )

    @root_validator
    def check_at_least_one_compound_type_provided(cls, values):
        compounds_create, compound_ids = values.get(
            "target_compounds_create"
        ), values.get("target_compound_ids")
        if not compounds_create and not compound_ids:
            raise ValueError("At least one compound must be provided.")
        return values


class TargetCollectionUpdateBody(TargetCollectionBase):
    target_compound_ids: Optional[List[str]] = Field(
        None,
        description="IDs of already existing in db target compounds to be associated with the target collection",
    )
    target_compounds_create: Optional[List[TargetCompoundBase]] = Field(
        None, description="Compounds to be created and added to the target collection"
    )
    sample_batch_ids: Optional[List[str]] = Field(
        None, description="IDs of sample batches associated with the target collection"
    )

    @root_validator(pre=True)
    def check_compounds_or_batches(cls, values):
        compounds_create, compound_ids, batches = (
            values.get("target_compounds_create"),
            values.get("target_compound_ids"),
            values.get("sample_batch_ids"),
        )
        # When updating batches, ensure no compounds are provided
        if batches is not None and (compounds_create or compound_ids):
            raise ValueError(
                "You cannot update target compounds while simultaneously updating sample batch associations."
            )

        # When not updating batches, ensure at least one compound is provided
        if batches is None:
            if not compounds_create and not compound_ids:
                raise ValueError(
                    "At least one compound (to create or associate) must be provided when not updating sample batch associations."
                )

        return values


class TargetCollectionInDB(TargetCollectionBase):
    target_collection_id: str = Field(..., description="ID of the target collection")

    class Config:
        orm_mode = True
