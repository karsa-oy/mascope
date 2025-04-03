from pydantic import Field
from mascope_backend.api.models.base_pydantic_model import QueryParamsModel


class GetVisualizationIonFocusQueryParams(QueryParamsModel):
    sample_item_id: str = Field(..., description="ID of the sample item")
    target_ion_id: str = Field(..., description="ID of the target ion")
    min_isotope_abundance: float = Field(
        ...,
        description="Minimum relative abundance of isotopes to consider in the match.",
    )
    peak_min_intensity: float = Field(
        ..., description="Minimum peak intensity threshold for considering a match."
    )
    mz_tolerance: int = Field(
        ..., description="Tolerance for mass-to-charge ratio (m/z) error."
    )
