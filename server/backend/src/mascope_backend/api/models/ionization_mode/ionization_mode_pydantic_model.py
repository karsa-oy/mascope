"""
Pydantic models for ionization mode API endpoints.
"""

from pydantic import BaseModel, Field, field_validator

from mascope_backend.api.models.base_pydantic_model import QueryParamsModel


class IonizationModeBaseValidator:
    @field_validator("ionization_mode_polarity")
    @classmethod
    def validate_polarity(cls, value: str):
        if value not in ["+", "-"]:
            raise ValueError('Polarity must be either "+" or "-"')
        return value

    @field_validator("ionization_mechanism_ids")
    @classmethod
    def validate_ionization_mechanism_ids(cls, value: list[str]):
        if not isinstance(value, list):
            raise ValueError("ionization_mechanism_ids must be a list")
        return value


class IonizationModeBase(IonizationModeBaseValidator, BaseModel):
    """Base model for ionization mode with common fields."""

    ionization_mode_name: str = Field(
        ..., max_length=256, description="Friendly, unique name of the ionization mode"
    )
    ionization_mode_token: str | None = Field(
        None,
        max_length=256,
        description="Unique filename token for the ionization mode",
    )
    ionization_mode_polarity: str = Field(
        ..., max_length=1, description="Polarity of the ionization mode (+ or -)"
    )
    ionization_mechanism_ids: list[str] = Field(
        default_factory=list,
        description="List of ionization mechanism IDs to apply for the scheme",
    )
    calibration_collection_id: str | None = Field(
        None,
        max_length=256,
        description="ID of the calibration collection to use for the scheme",
    )
    diagnostic_collection_id: str | None = Field(
        None,
        max_length=256,
        description="ID of the diagnostic collection to use for the scheme",
    )


class IonizationModeCreate(IonizationModeBase):
    """Model for creating a new ionization mode."""

    pass


class IonizationModeUpdate(IonizationModeBase):
    """Model for updating an existing ionization mode."""

    pass


class GetIonizationModesQueryParams(QueryParamsModel):
    ionization_mode_polarity: str | None = Field(
        None, description="Filter by ionization mode polarity ('+' or '-')"
    )
