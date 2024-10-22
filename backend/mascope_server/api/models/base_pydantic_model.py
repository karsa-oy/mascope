from pydantic import BaseModel, field_validator


class QueryParamsModel(BaseModel):
    """
    Custom base model for query parameter models.
    Handles common behaviors like decoding '+' signs in query parameters.
    """

    @field_validator("*", mode="before")
    @classmethod
    def decode_plus_sign(cls, value):
        """
        Automatically decode '+' signs for any string field in the query parameters.
        """
        if isinstance(value, str) and value:
            return value.replace(" ", "+")
        return value
