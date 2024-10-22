from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator
from mascope_server.api.models.target.compounds.target_compound_pydantic_model import (
    TargetCompoundBase,
)
from mascope_server.api.models.base_pydantic_model import QueryParamsModel

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

    @field_validator("target_collection_type")
    @classmethod
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

    @model_validator(mode="after")
    @classmethod
    def check_at_least_one_compound_provided(cls, values):
        compounds_create, compound_ids = (
            values.target_compounds_create,
            values.target_compound_ids,
        )
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

    @model_validator(mode="before")
    @classmethod
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


class GetTargetCollectionsQueryParams(QueryParamsModel):
    target_collection_type: Optional[str] = Field(
        None,
        description="The target collection type for which you want to fetch the target collections.",
    )
    target_collection_name: Optional[str] = Field(
        None,
        description="The name of the target collection for which you want to fetch the target collections.",
    )
    sample_batch_id: Optional[str] = Field(
        None, description="The ID of the sample batch to filter collections by."
    )
    sort: Optional[str] = Field(
        None,
        description="The column name by which you want to sort the results. The column name should be one of the fields of target_collection.",
    )
    order: Optional[str] = Field(
        None,
        description="Can either be asc for ascending order or desc for descending order.",
    )
    page: int = Field(0, description="The page number for pagination, default 0")
    limit: int = Field(10000, description="The number of results per page.")


class GetTargetCollectionsInSampleBatchQueryParams(QueryParamsModel):
    sample_batch_id: Optional[str] = Field(
        None,
        description="The sample batch ID filter for which you want to fetch the assosiated target collections ids.",
    )
    target_collection_id: Optional[str] = Field(
        None,
        description="The target collection ID filter for which you want to fetch the assosiated sample batches ids.",
    )
    sort: Optional[str] = Field(
        None,
        description="The column name by which you want to sort the results. The column name should be either sample_batch_id or target_collection_id.",
    )
    order: Optional[str] = Field(
        None,
        description="Can either be asc for ascending order or desc for descending order.",
    )
    page: int = Field(0, description="The page number for pagination, default 0")
    limit: int = Field(10000, description="The number of results per page.")
