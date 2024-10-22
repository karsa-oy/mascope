from pydantic import BaseModel, Field
from typing import Optional
from mascope_server.api.models.base_pydantic_model import QueryParamsModel


class IonizationMechanismCreate(BaseModel):
    ionization_mechanism_polarity: str = Field(
        ..., description="Polarity of the ionization mechanism (e.g., '+', '-')"
    )
    ionization_mechanism: str = Field(
        ...,
        description="Description of the ionization mechanism, representing the ionized form.",
    )
    reagent: str = Field(
        ...,
        description="Reagent used in the ionization process, if applicable.",
    )


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
