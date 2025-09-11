from pydantic import BaseModel, Field, model_validator


class RematchBatchesBody(BaseModel):
    sample_batch_ids: list[str] = Field(
        ..., description="List of sample batch IDs to rematch"
    )


class FilterSamplePayload(BaseModel):
    sample_batch_id: str | None = Field(
        None, description="Filter samples by ID of the sample batch"
    )
    sample_item_id: str | None = Field(
        None, description="Filter samples by ID of the sample item"
    )

    @model_validator(mode="before")
    @classmethod
    def check_sample_item_id_or_sample_batch_id(cls, values):
        sample_item_id = values.get("sample_item_id")
        sample_batch_id = values.get("sample_batch_id")

        if sample_item_id and sample_batch_id:
            raise ValueError(
                "Specify either a sample batch ID or a sample item ID, not both."
            )
        if not sample_item_id and not sample_batch_id:
            raise ValueError(
                "Please specify at least one: a sample batch ID or a sample item ID."
            )

        return values
