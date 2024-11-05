from .schema import Params


async def get_params() -> Params:
    return {"message": "Retrieved global params", "data": {"params": Params()}}
