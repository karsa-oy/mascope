from pydantic import BaseModel, Field
from typing import List


class TargetCollectionInSampleBatchBase(BaseModel):
    target_collection_id: str = Field(..., description="ID of the target collection")
    sample_batch_id: str = Field(..., description="ID of the sample batch")


class TargetCollectionInSampleBatchInDB(TargetCollectionInSampleBatchBase):
    class Config:
        orm_mode = True


class TargetCollectionInSampleBatchPayload(BaseModel):
    target_collections: List[TargetCollectionInSampleBatchBase]
    skipRematch: bool = False
