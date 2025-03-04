from pydantic import BaseModel, Field

from .mode import RuntimeMode


class RuntimeOptions(BaseModel):
    env: str | None = Field(None, description="")
    path: str | None = Field(None, description="")
    mode: RuntimeMode | None = Field(None, description="")
