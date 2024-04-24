from typing import List, Optional
from pydantic import BaseModel, Field, validator
from datetime import datetime
from .target_compound_pydantic_model import TargetCompoundMatches


# TODO_configuration possible collection types
APP_COLLECTION_TYPES = ["TARGETS", "DIAGNOSTICS", "CALIBRANTS"]
# TODO_configuration Default Filter Parameters
DEFAULT_MZ_TOLERANCE = 15
DEFAULT_MIN_ISOTOPE_ABUNDANCE = 0.15
DEFAULT_ISOTOPE_RATIO_TOLERANCE = 0.15
DEFAULT_PEAK_MIN_INTENSITY = 0.0
DEFAULT_MIN_ISOTOPE_CORRELATION = 0.8
DEFAULT_PROBABLE_MATCH_THRESHOLD = 0.8
DEFAULT_POSSIBLE_MATCH_THRESHOLD = 0.7


class FilterParams(BaseModel):
    mz_tolerance: int = Field(
        DEFAULT_MZ_TOLERANCE,
        description="Tolerance for mass-to-charge ratio (m/z) error.",
    )
    isotope_ratio_tolerance: float = Field(
        DEFAULT_ISOTOPE_RATIO_TOLERANCE,
        description="Tolerance for the ratio of isotopic abundances.",
    )
    peak_min_intensity: float = Field(
        DEFAULT_PEAK_MIN_INTENSITY,
        description="Minimum peak intensity threshold for considering a match.",
    )
    min_isotope_abundance: float = Field(
        DEFAULT_MIN_ISOTOPE_ABUNDANCE,
        description="Minimum relative abundance of isotopes to consider in the match.",
    )
    min_isotope_correlation: float = Field(
        DEFAULT_MIN_ISOTOPE_CORRELATION,
        description="Minimum correlation of isotopic pattern required for a match.",
    )
    probable_match_threshold: float = Field(
        DEFAULT_PROBABLE_MATCH_THRESHOLD,
        description="Threshold score above which a match is considered probable.",
    )
    possible_match_threshold: float = Field(
        DEFAULT_POSSIBLE_MATCH_THRESHOLD,
        description="Threshold score above which a match is considered possible, but below the probable match threshold.",
    )

    @validator("possible_match_threshold")
    def validate_thresholds(cls, possible_match_threshold, values):
        if "probable_match_threshold" in values:
            if possible_match_threshold > values["probable_match_threshold"]:
                raise ValueError(
                    "Possible match threshold must be less than or equal to probable match threshold"
                )
        return possible_match_threshold


#  Note that AlarmsList acts as a common base class that includes the alarms_list field and its validator
class AlarmsList(BaseModel):
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


class GetSamplesBody(AlarmsList):
    sample_item_id: Optional[str] = Field(
        None, description="ID of the specific sample item to filter results by."
    )
    sample_item_id_active: Optional[str] = Field(
        None,
        description="ID of the active sample item for setting the selection status. TODO not in use?",
    )
    sample_file_id: Optional[str] = Field(
        None, description="ID of the sample file to filter results by."
    )
    sample_batch_id: Optional[str] = Field(
        None,
        description="ID of the sample batch to filter results by. Required for batch match info.",
    )
    filename: Optional[str] = Field(
        None, description="Filename of the sample to filter results by."
    )
    instrument: Optional[str] = Field(
        None, description="Instrument name to filter results by."
    )
    sample_item_type: Optional[str] = Field(
        None, description="Type of the sample item to filter results by."
    )
    datetime_min: Optional[datetime] = Field(
        None, description="Minimum datetime of the sample file to filter results by."
    )
    datetime_max: Optional[datetime] = Field(
        None, description="Maximum datetime of the sample file to filter results by."
    )
    sort: Optional[str] = Field(
        "datetime_utc",
        description="Column name by which to sort the results. Default is 'datetime_utc'.",
    )
    order: Optional[str] = Field(
        "asc",
        description="Sorting order, either 'asc' for ascending or 'desc' for descending. Default is 'asc'.",
    )
    page: Optional[int] = Field(
        0, description="Page number for pagination. Default is 0."
    )
    limit: Optional[int] = Field(
        10000, description="Number of results per page. Default is 10000."
    )
    batch_matches_info: Optional[bool] = Field(
        True,
        description="Flag indicating whether to calculate and include batch match information. Default is True.",
    )
    match_samples: Optional[bool] = Field(
        True,
        description="Flag indicating whether to include matched samples in the response. Default is True.",
    )
    match_compounds: Optional[bool] = Field(
        True,
        description="Flag indicating whether to include matched compounds in the response. Default is True.",
    )
    match_ions: Optional[bool] = Field(
        True,
        description="Flag indicating whether to include matched ions in the response. Default is True.",
    )
    match_isotopes: Optional[bool] = Field(
        False,
        description="Flag indicating whether to include matched isotopes in the response. Default is False.",
    )


class GetSampleBody(AlarmsList):
    sample_matches_info: Optional[bool] = Field(
        default=True,
        description="Flag indicating whether the matches data should be calculated.",
    )


class GetSampleIonMatchesBody(AlarmsList):
    target_ion_id: str = Field(..., description="ID of the target ion")
    target_collection_id: str = Field(
        ..., description="ID of the target collection to remove possible dublicates"
    )
    filter_params: FilterParams = Field(
        ...,
        description="Ion-specific filter parameters, used for match_score and sample_peak_area filtering",
    )


class GetSampleCompoundMatchesBody(BaseModel):
    target_compound: TargetCompoundMatches = Field(
        ..., description="Target compound with required formula and optional name"
    )
    filter_params: FilterParams = FilterParams()


class GetSampleMatchFilterBody(BaseModel):
    target_ion_id: str = Field(None, description="ID of the target ion")
    filter_params: FilterParams = Field(
        None,
        description="Ion-specific filter parameters, used for match_score and sample_peak_area filtering",
    )
