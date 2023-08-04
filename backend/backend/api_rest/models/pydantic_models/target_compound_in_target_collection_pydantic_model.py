from pydantic import BaseModel, Field


class TargetCompoundInTargetCollectionBase(BaseModel):
    target_compound_id: str = Field(..., description="ID of the target compound")
    target_collection_id: str = Field(..., description="ID of the target collection")


class TargetCompoundInTargetCollectionInDB(TargetCompoundInTargetCollectionBase):
    class Config:
        orm_mode = True
