from pydantic import BaseModel, Field, field_validator
from mascope_server.api.new.auth.config import auth_settings


class AccessTokenRequest(BaseModel):
    """
    Schema for validating access token request body.
    """

    service_name: str = Field(
        ...,
        description="The name of the service for which the access token is generated.",
    )

    @field_validator("service_name")
    @classmethod
    def validate_role_name(cls, service_name):
        """
        Validates that `service_name` exists in the access_token configuration.
        """
        allowed_services = auth_settings.access_token.ALLOWED_SERVICES
        if service_name not in allowed_services:
            raise ValueError(f"Invalid service name: '{service_name}'.")
        return service_name
