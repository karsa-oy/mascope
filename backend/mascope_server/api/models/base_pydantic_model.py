from pydantic import BaseModel, field_validator


class QueryParamsModel(BaseModel):
    """
    Custom base model for query parameter models.
    Handles common behaviors like decoding '+' signs in query parameters.
    """

    @field_validator(
        "ionization_mechanism_polarity",
        "ionization_mechanism",
        "reagent",
        "filename",
        check_fields=False,  # allows the validator to work across models without requiring these fields
        mode="before",
    )
    @classmethod
    def decode_plus_sign(cls, value):
        """
        Automatically decode '+' signs for specific string fields in the query parameters.
        """
        if isinstance(value, str) and value:
            return value.replace(" ", "+")
        return value
