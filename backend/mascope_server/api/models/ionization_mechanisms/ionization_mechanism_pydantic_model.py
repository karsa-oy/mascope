import re
from typing import Optional
from pydantic import BaseModel, Field, field_validator, model_validator
from mascope_server.api.models.base_pydantic_model import QueryParamsModel


class IonizationMechanismCreate(BaseModel):
    ionization_mechanism_polarity: str = Field(
        ...,
        description="Polarity of the ionization mechanism ('+' or '-')",
    )
    ionization_mechanism: str = Field(
        ...,
        description="Chemical formula modification (addition/abstraction) representing the ionized form.",
    )
    reagent: Optional[str] = Field(
        None, description="Reagent used in the ionization process, if applicable."
    )

    @field_validator("ionization_mechanism_polarity")
    @classmethod
    def validate_polarity(cls, value):
        if value not in ["+", "-"]:
            raise ValueError(f"Invalid polarity '{value}'. Must be '+' or '-'.")
        return value

    @field_validator("ionization_mechanism")
    @classmethod
    def validate_ionization_mechanism(cls, value):
        if not value.strip():
            raise ValueError("ionization_mechanism cannot be empty or just whitespace.")

        # Check if it starts with + or -
        if not re.match(r"^[\+\-]", value):
            raise ValueError(
                "The ionization mechanism must start with '+' (addition) or '-' (abstraction)."
            )

        # Check if it ends with + or -
        if not re.match(r".*[\+\-]$", value):
            raise ValueError(
                "The ionization mechanism must end with '+' or '-' to indicate the ion charge."
            )

        # Prevent invalid sequences like "+-" or "-+"
        if "+-" in value or "-+" in value:
            raise ValueError(
                "Invalid ionization mechanism: it cannot contain a combination of '+' and '-' in the middle."
            )

        return value

    @field_validator("reagent")
    @classmethod
    def validate_reagent(cls, value):
        if value is not None and not value.strip():
            raise ValueError("reagent cannot be an empty string.")
        return value

    @model_validator(mode="after")
    @classmethod
    def validate_ionization_mechanism_and_polarity(cls, values):
        polarity = values.ionization_mechanism_polarity
        ionization_mechanism = values.ionization_mechanism

        # Match the polarity with the final ion charge
        if polarity == "+" and not ionization_mechanism.endswith("+"):
            raise ValueError(
                "Polarity is '+', but the ionization mechanism does not end with '+'. The ion should carry a positive charge."
            )
        if polarity == "-" and not ionization_mechanism.endswith("-"):
            raise ValueError(
                "Polarity is '-', but the ionization mechanism does not end with '-'. The ion should carry a negative charge."
            )

        return values


class GetIonizationMechanismsQueryParams(QueryParamsModel):
    ionization_mechanism_polarity: Optional[str] = Field(
        None, description="Filter by the polarity of the ionization mechanism."
    )
    ionization_mechanism: Optional[str] = Field(
        None,
        description="Filter by the chemical formula modification of the ionization mechanism.",
    )
    reagent: Optional[str] = Field(
        None, description="Filter by the reagent used in the ionization process."
    )
    sort: Optional[str] = Field(None, description="Field to sort by.")
    order: Optional[str] = Field(
        None,
        description="Order of sorting, can be either 'asc' for ascending or 'desc' for descending.",
    )
    page: int = Field(0, description="Pagination page number.")
    limit: int = Field(10000, description="Number of items per page.")
