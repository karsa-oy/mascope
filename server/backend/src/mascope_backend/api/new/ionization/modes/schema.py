from pydantic import BaseModel, ConfigDict, Field, field_validator

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
        if not all(isinstance(item, str) for item in value):
            raise ValueError("All items in ionization_mechanism_ids must be strings")
        if not len(value):
            raise ValueError("ionization_mechanism_ids must contain at least one ID")
        return value


class IonizationModeTokenValidator:
    @field_validator("ionization_mode_token")
    @classmethod
    def validate_token(cls, value: str | None):
        """Strip trailing and leading whitespace and convert empty strings to None."""
        value = value.strip() if value else value
        if value == "":
            return None
        return value


class IonizationModeBase(
    IonizationModeBaseValidator, IonizationModeTokenValidator, BaseModel
):
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
        max_length=16,
        description="ID of the calibration collection to use for the scheme",
    )
    diagnostic_collection_id: str | None = Field(
        None,
        max_length=16,
        description="ID of the diagnostic collection to use for the scheme",
    )

    model_config = ConfigDict(from_attributes=True)


class IonizationModeCreate(IonizationModeBase):
    """Model for creating a new ionization mode."""

    pass


class IonizationModeUpdate(IonizationModeTokenValidator, BaseModel):
    """Model for updating an existing ionization mode."""

    ionization_mode_name: str = Field(
        ..., max_length=256, description="Friendly, unique name of the ionization mode"
    )
    ionization_mode_token: str | None = Field(
        None,
        max_length=256,
        description="Unique filename token for the ionization mode",
    )
    calibration_collection_id: str | None = Field(
        None,
        max_length=16,
        description=(
            "ID of the calibration collection to use for the scheme. "
            "When updating, only allowed if calibration collection is not yet defined."
        ),
    )
    diagnostic_collection_id: str | None = Field(
        None,
        max_length=16,
        description=(
            "ID of the diagnostic collection to use for the scheme. "
            "When updating, only allowed if diagnostic collection is not yet defined."
        ),
    )


class GetIonizationModesQueryParams(QueryParamsModel):
    """Placeholder for future query parameters for getting ionization modes."""

    pass
