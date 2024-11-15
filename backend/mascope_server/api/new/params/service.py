from .schema import Params


async def get_params() -> dict:
    """Fetch parameters for the application.

    :return: A dictionary with a success message and the parameter data.
    """
    return {
        "message": "Retrieved parameters successfully.",
        "data": {"params": Params()},
    }
