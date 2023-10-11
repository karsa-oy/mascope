from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import timezone, datetime as dt


class IsotopeRating(BaseModel):
    isotope_rating: int = Field(
        ..., ge=1, le=5, description="Match isotope rating from 1 to 5"
    )
    target_isotope_id: str = Field(
        ..., description="ID of the associated target isotope"
    )


class MatchRatingChecklist(BaseModel):
    isotopes_rating: List[IsotopeRating] = Field(
        ..., description="List of match isotopes with data and rating"
    )
    timeseries_good_match: bool = Field(
        ..., description="Do the timeseries indicate a good match between the isotopes"
    )
    timeseries_expected_behavior: int = Field(
        ...,
        ge=0,
        le=2,
        description="Do the timeseries indicate expected behavior? Where 0 - 'No', 1 - 'Maybe', 2 - 'Yes'",
    )
    comment: Optional[str] = Field(None, description="Optional comment")


class Environment(BaseModel):
    mz_calibration: Dict = Field(..., description="m/z calibration data of the sample")


class MatchRatingBase(BaseModel):
    sample_item_id: str = Field(..., description="ID of the associated sample item")
    target_ion_id: str = Field(..., description="ID of the associated target ion")
    rating: int = Field(..., ge=0, le=2, description="Rating value between 0 and 2")
    checklist: Optional[MatchRatingChecklist] = Field(
        None, description="Checklist for the match rating"
    )
    environment: Environment = Field(..., description="Environment-related data")


class MatchRatingCreate(MatchRatingBase):
    pass


class MatchRatingUpdate(MatchRatingBase):
    pass


class MatchRatingInDB(MatchRatingBase):
    match_rating_id: str = Field(..., description="ID of the match rating")
    match_rating_utc_created: dt = Field(
        ..., description="Creation timestamp of the match rating"
    )

    class Config:
        orm_mode = True
        # datetime fields will be represented in the ISO 8601 format in response
        json_encoders = {
            dt: lambda v: v.replace(tzinfo=timezone.utc).isoformat(timespec="seconds")
        }
