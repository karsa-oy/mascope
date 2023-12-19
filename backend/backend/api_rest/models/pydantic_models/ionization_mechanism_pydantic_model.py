from pydantic import BaseModel, Field


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
