from pydantic import BaseModel, Field


class FileDownloadBody(BaseModel):
    sample_file_ids: list[str] = Field(
        ..., description="The sample file IDs to download"
    )
