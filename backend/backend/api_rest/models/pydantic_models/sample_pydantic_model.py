from typing import List, Optional
from pydantic import BaseModel, Field, validator
from datetime import datetime


# TODO_configuration possible collection types
APP_COLLECTION_TYPES = ["TARGETS", "DIAGNOSTICS", "CALIBRANTS"]


class FilterParams(BaseModel):
    mz_tolerance: int = Field(
        ..., description="Tolerance for mass-to-charge ratio (m/z) error."
    )
    isotope_ratio_tolerance: float = Field(
        ..., description="Tolerance for the ratio of isotopic abundances."
    )
    peak_min_intensity: float = Field(
        ..., description="Minimum peak intensity threshold for considering a match."
    )
    min_isotope_abundance: float = Field(
        ...,
        description="Minimum relative abundance of isotopes to consider in the match.",
    )
    min_isotope_correlation: float = Field(
        ..., description="Minimum correlation of isotopic pattern required for a match."
    )
    probable_match_threshold: float = Field(
        ..., description="Threshold score above which a match is considered probable."
    )
    possible_match_threshold: float = Field(
        ...,
        description="Threshold score above which a match is considered possible, but below the probable match threshold.",
    )

    @validator("possible_match_threshold")
    def validate_thresholds(cls, possible_match_threshold, values):
        if "probable_match_threshold" in values:
            if possible_match_threshold > values["probable_match_threshold"]:
                raise ValueError(
                    "possible_match_threshold must be less than or equal to probable_match_threshold"
                )
        return possible_match_threshold


#  Note that GetSampleBody also acts as a common base class that includes the alarms_list field and its validator
class GetSampleBody(BaseModel):
    alarms_list: List[str] = Field(
        default=["TARGETS"],
        description="List of collection types to set alarm mode to true",
    )

    @validator("alarms_list", each_item=True)
    def validate_alarms_list(cls, item):
        if item not in APP_COLLECTION_TYPES:
            allowed_types = ", ".join(APP_COLLECTION_TYPES)
            raise ValueError(
                f"{item} is not a valid collection type. Allowed types are {allowed_types}."
            )
        return item


class GetSamplesBody(GetSampleBody):
    sample_item_id: Optional[str] = None
    sample_item_id_active: Optional[str] = None
    sample_file_id: Optional[str] = None
    sample_batch_id: Optional[str] = None
    filename: Optional[str] = None
    instrument: Optional[str] = None
    sample_item_type: Optional[str] = None
    minDatetime: Optional[datetime] = None
    maxDatetime: Optional[datetime] = None
    sort: Optional[str] = None
    order: Optional[str] = None
    page: Optional[int] = 0
    limit: Optional[int] = 10000
    batch_matches_info: Optional[bool] = False
    match_samples: Optional[bool] = True
    match_compounds: Optional[bool] = True
    match_ions: Optional[bool] = True
    match_isotopes: Optional[bool] = False


class GetSampleIonMatchesBody(GetSampleBody):
    target_ion_id: str = Field(..., description="ID of the target ion")
    target_collection_id: str = Field(
        ..., description="ID of the target collection to remove possible dublicates"
    )
    filter_params: FilterParams = Field(
        ...,
        description="Ion-specific filter parameters, used for match_score and sample_peak_area filtering",
    )


class MatchFilterBody(BaseModel):
    target_ion_id: str = Field(None, description="ID of the target ion")
    filter_params: FilterParams = Field(
        None,
        description="Ion-specific filter parameters, used for match_score and sample_peak_area filtering",
    )
