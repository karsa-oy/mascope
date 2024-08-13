from typing import List, Optional, Annotated
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from mascope_server.api.models.target.compounds.target_compound_pydantic_model import (
    TargetCompoundMatches,
)
from mascope_server.api.models.match.match_pydantic_model import FilterParams


# TODO_configuration possible collection types
APP_COLLECTION_TYPES = ["TARGETS", "DIAGNOSTICS", "CALIBRANTS"]


#  Note that AlarmsList acts as a common base class that includes the alarms_list field and its field validator
class AlarmsList(BaseModel):
    alarms_list: List[Annotated[str, Field(description="Type of alarm")]] = Field(
        default=["TARGETS"],
        description="List of collection types to set alarm mode to true",
    )

    @field_validator("alarms_list")
    @classmethod
    def validate_alarms_list(cls, items):
        errors = []
        for item in items:
            if item not in APP_COLLECTION_TYPES:
                allowed_types = ", ".join(APP_COLLECTION_TYPES)
                errors.append(
                    f"{item} is not a valid collection type. Allowed types are {allowed_types}."
                )
        if errors:
            raise ValueError(" ".join(errors))
        return items


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


class GetSamplesQueryParams(BaseModel):
    sample_item_id: Optional[str] = Field(
        None, description="ID of the specific sample item to filter results by."
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
    match_category: Optional[int] = Field(
        None, description="Filter match samples by match category"
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


class GetSampleBody(AlarmsList):
    sample_matches_info: Optional[bool] = Field(
        default=True,
        description="Flag indicating whether the matches data should be calculated.",
    )


class GetSampleMatchFilterBody(BaseModel):
    target_ion_id: str = Field(None, description="ID of the target ion")
    filter_params: FilterParams = Field(
        None,
        description="Ion-specific filter parameters, used for match_score and sample_peak_area filtering",
    )
