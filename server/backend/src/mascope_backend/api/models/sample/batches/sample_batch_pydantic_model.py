"""
Sample batch pydantic models for API validation and serialization.

Defines data models for sample batch related requests and responses
with validation rules and business logic constraints.
"""

from datetime import datetime
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict

from mascope_file.name import get_instrument_type

from mascope_backend.api.new.instrument_configs.schemas import (
    SetInstrumentConfigBody,
)
from mascope_backend.api.models.calibration.calibration_pydantic_model import (
    MzCalibrationParams,
)
from mascope_backend.api.models.sample.items.sample_item_pydantic_model import (
    SampleItemCreate,
)
from mascope_backend.api.models.base_pydantic_model import QueryParamsModel
from mascope_backend.api.models.sample.batches.config import sample_batch_config


class BuildParams(BaseModel):
    calibration_collection: str | None = Field(
        None, description="ID of the calibration collection (optional for ACQUISITION)"
    )
    ion_mechanisms: list[str] = Field(
        ..., description="List of ionisation mechanism IDs for matching"
    )
    calibration_ion_mechanisms: list[str] | None = Field(
        [], description="List of ionisation mechanism IDs for calibration"
    )

    @field_validator("calibration_collection")
    @classmethod
    def check_calibration_collection_length(cls, v):
        """Validate length if calibration_collection is provided"""
        if v is not None:
            # Convert empty strings to None
            if isinstance(v, str) and v.strip() == "":
                return None
            # Validate length for non-empty values
            if len(v) != 16:
                raise ValueError("Only one calibration collection can be applied")
        return v

    @field_validator("ion_mechanisms")
    @classmethod
    def check_ion_mechanisms_non_empty(cls, v):
        if len(v) == 0:
            raise ValueError("At least one ionization mechanism must be provided")
        return v


class SampleBatchBaseValidator:
    """Base validation logic for sample batch shared fields."""

    @field_validator("sample_batch_name")
    @classmethod
    def validate_sample_batch_name(cls, sample_batch_name: str | None) -> str | None:
        """Validate sample batch name is not empty or whitespace."""
        if sample_batch_name is not None and sample_batch_name.strip() == "":
            raise ValueError(
                "Sample batch name cannot be empty or contain only whitespace."
            )
        return sample_batch_name


class SampleBatchValidator(SampleBatchBaseValidator):
    """Validators for all fields."""

    @field_validator("sample_batch_type")
    @classmethod
    def validate_sample_batch_type(cls, sample_batch_type: str | None) -> str | None:
        """Complete validation logic for all sample batch fields."""
        if (
            sample_batch_type
            and sample_batch_type not in sample_batch_config.SAMPLE_BATCH_TYPES
        ):
            raise ValueError(
                f"Invalid sample batch type. Must be one of: {', '.join(sample_batch_config.SAMPLE_BATCH_TYPES)}"
            )
        return sample_batch_type

    @field_validator("polarity")
    @classmethod
    def validate_polarity(cls, polarity: str | None) -> str | None:
        """Validate polarity values."""
        if polarity and polarity not in sample_batch_config.all_sample_batch_polarities:
            raise ValueError(
                f"Invalid sample batch polarity. Must be one of: {', '.join(sample_batch_config.all_sample_batch_polarities)}"
            )
        return polarity

    @model_validator(mode="after")
    @classmethod
    def validate_polarity_by_batch_type(cls, values):
        """Validate polarity constraints based on sample batch type."""
        sample_batch_type, polarity = values.sample_batch_type, values.polarity

        if sample_batch_type == "ACQUISITION":
            if polarity not in sample_batch_config.ACQUISITION_POLARITY:
                raise ValueError(
                    f"Invalid acquisition batch polarity. Must be one of: {', '.join(sample_batch_config.ACQUISITION_POLARITY)}. "
                    f"Got: '{polarity}'"
                )
        elif sample_batch_type == "ANALYSIS":
            if polarity != sample_batch_config.ANALYSIS_POLARITY:
                raise ValueError(
                    f"Analysis batch should have polarity '{sample_batch_config.ANALYSIS_POLARITY}'. "
                    f"Got: '{polarity}'"
                )

        return values


class SampleBatchBase(SampleBatchValidator, BaseModel):
    """Base model with common fields for SampleBatch."""

    workspace_id: str = Field(
        ..., description="ID of the workspace associated with the sample batch"
    )
    sample_batch_name: str = Field(..., description="Name of the sample batch")
    sample_batch_description: str | None = Field(
        "", description="Description of the sample batch"
    )
    sample_batch_type: str = Field(
        default=sample_batch_config.DEFAULT_SAMPLE_BATCH_TYPE,
        description="Type of sample batch (ACQUISITION or ANALYSIS)",
    )
    polarity: str = Field(
        default=sample_batch_config.ANALYSIS_POLARITY,
        description="Polarity of the sample batch (+, -, or +-)",
    )
    build_params: BuildParams = Field(
        ..., description="Build parameters of the sample batch"
    )

    model_config = ConfigDict(from_attributes=True)


class SampleBatchCreate(SampleBatchBase):
    """Model used for sample batch creation requests."""

    target_collection_ids: list[str] = Field(
        ..., description="IDs of target collections associated with the sample batch"
    )


class SampleBatchRead(SampleBatchBase):
    """Sample batch response model with added database fields."""

    sample_batch_id: str = Field(
        ..., description="Unique identifier for the sample batch"
    )
    locked: int = Field(
        ..., description="Lock status of the sample batch (0=unlocked, 1=locked)"
    )
    sample_batch_utc_created: datetime = Field(
        ..., description="Timestamp when sample batch was created"
    )
    sample_batch_utc_modified: datetime | None = Field(
        None, description="Timestamp when sample batch was last modified"
    )


class SampleBatchUpdate(SampleBatchBaseValidator, BaseModel):
    """
    Model for updating sample batches - only user-editable fields.

    Target collections associations and build parameters are always included
    in the update request, on service level they are handled separately.
    """

    sample_batch_name: str | None = Field(None, description="Name of the sample batch")
    sample_batch_description: str | None = Field(
        None, description="Description of the sample batch"
    )
    build_params: BuildParams = Field(
        ..., description="Build parameters of the sample batch"
    )
    target_collection_ids: list[str] = Field(
        ..., description="IDs of target collections associated with the sample batch"
    )

    model_config = ConfigDict(from_attributes=True)


class GetSampleBatchesQueryParams(QueryParamsModel):
    workspace_id: str | None = Field(
        None,
        description="Filter by the workspace ID for which you want to fetch the sample batches.",
    )
    sample_batch_name: str | None = Field(
        None, description="Filter by name of the sample batch"
    )
    sample_batch_type: list[str] | None = Field(
        default=None,
        description="Filter by sample batch types (ACQUISITION, ANALYSIS). Can specify multiple types.",
    )
    polarity: list[str] | None = Field(
        default=None,
        description="Filter by polarities (+, -, +-). Can specify multiple polarities.",
    )
    sort: str | None = Field(
        "sample_batch_utc_created",
        description="Column name by which you want to sort the results. The column name should be one of the columns in the sample batch table.",
    )
    order: str | None = Field(
        "asc",
        description="Sorting order which can be asc for ascending or desc for descending.",
    )
    page: int = Field(0, description="Page number for pagination.")
    limit: int = Field(10000, description="Number of results per page.")

    @field_validator("sample_batch_type")
    @classmethod
    def validate_sample_batch_type_list(
        cls, sample_batch_types: list[str] | None
    ) -> list[str] | None:
        """Validate sample batch types."""
        if sample_batch_types:
            for sample_batch_type in sample_batch_types:
                if sample_batch_type not in sample_batch_config.SAMPLE_BATCH_TYPES:
                    raise ValueError(
                        f"Invalid sample batch type '{sample_batch_type}'. Must be one of: {', '.join(sample_batch_config.SAMPLE_BATCH_TYPES)}"
                    )
        return sample_batch_types

    @field_validator("polarity")
    @classmethod
    def validate_polarity_list(cls, polarities: list[str] | None) -> list[str] | None:
        """Validate polarities."""
        if polarities:
            for polarity in polarities:
                if polarity not in sample_batch_config.all_sample_batch_polarities:
                    raise ValueError(
                        f"Invalid polarity '{polarity}'. Must be one of: {', '.join(sample_batch_config.all_sample_batch_polarities)}"
                    )
        return polarities


class GetSampleBatchTargetsQueryParams(QueryParamsModel):
    deduplicate: bool | None = Field(
        False,
        description="Drop the potential duplicates (added to several target collections). Target collection info added if deduplicate is False.",
    )


class SampleBatchImportSamplesBody(BaseModel):
    sample_items: list[SampleItemCreate] = Field(
        ..., description="Sample items to be created and imported to the sample batch"
    )
    mz_calibration_params: MzCalibrationParams = MzCalibrationParams()
    instrument_config: SetInstrumentConfigBody = Field(
        ...,
        description="Instrument config to use for imported sample files",
    )
    calibrate_batch: bool = Field(
        default=True,
        description="Flag to control whether the batch should be calibrated.",
    )

    @model_validator(mode="after")
    @classmethod
    def check_sample_items(cls, values):
        sample_items = values.sample_items
        batch_ids = {item.sample_batch_id for item in sample_items}
        instruments = set(get_instrument_type(item.filename) for item in sample_items)
        if len(batch_ids) > 1:
            raise ValueError(
                "All samples should be imported to the same batch, please check if the sample batch ID is the same for all importing samples."
            )
        if len(instruments) > 1:
            raise ValueError(
                "Importing samples from different instruments is not supported, please import samples for each instrument separately."
            )
        return values


class SampleBatchCopyBody(BaseModel):
    workspace_id: str = Field(
        ..., description="ID of the workspace where to copy the batch"
    )
    sample_batch_name: str = Field(..., description="Name of the new sample batch")
    sample_batch_description: str | None = Field(
        None, description="Description of the new sample batch"
    )
