from pydantic import BaseModel, Field


class InstrumentFunctionParams(BaseModel):
    threshold: float = Field(
        0.95,
        description="R-squared threshold filtering non-(skewed) Gaussian peaks from instrument function evaluation",
    )
