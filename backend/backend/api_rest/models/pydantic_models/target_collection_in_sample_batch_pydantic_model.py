from pydantic import BaseModel, Field


class TargetCollectionInSampleBatchBase(BaseModel):
    target_collection_id: str = Field(..., description="ID of the target collection")
    sample_batch_id: str = Field(..., description="ID of the sample batch")


class TargetCollectionInSampleBatchInDB(TargetCollectionInSampleBatchBase):
    class Config:
        orm_mode = True
