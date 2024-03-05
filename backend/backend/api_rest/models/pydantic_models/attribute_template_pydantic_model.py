from typing import List, Optional
from pydantic import BaseModel, Field, validator


class TemplateField(BaseModel):
    label: str = Field(..., description="Label of the template field")
    required: Optional[bool] = Field(
        default=False, description="Indicates if the field is required"
    )
    value: Optional[str] = Field(
        default="", description="Default value for the template field"
    )


class AttributeTemplateBase(BaseModel):
    name: str = Field(..., description="Name of the attribute template")
    type: str = Field(
        ..., description="Type of the attribute template, e.g., 'sample_item'"
    )
    template: List[TemplateField] = Field(
        ..., description="List of template fields for the attribute template"
    )

    @validator("type")
    def validate_type(cls, item):
        allowed_types = ", ".join(
            [
                "sample_item",
            ]
        )
        if item not in allowed_types:
            raise ValueError(
                f"The '{item}' is not a valid type for template. Allowed type is '{allowed_types}'"
            )
        return item

    @validator("template")
    def validate_unique_labels(cls, template_fields):
        labels = [field.label for field in template_fields]
        if len(labels) != len(set(labels)):
            raise ValueError(
                "Duplicate labels found in template fields. Each label must be unique."
            )
        return template_fields


class AttributeTemplateCreateBody(AttributeTemplateBase):
    pass


class AttributeTemplateUpdateBody(AttributeTemplateBase):
    pass


class AttributeTemplateInDB(AttributeTemplateBase):
    attribute_template_id: str = Field(
        ..., description="Unique ID for the attribute template"
    )

    class Config:
        orm_mode = True
