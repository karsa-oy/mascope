from functools import wraps
from fastapi.responses import JSONResponse
from ..exceptions import process_exception


def controller_handler(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            result = await func(*args, **kwargs)
            return JSONResponse(status_code=200, content={"data": result})
        except Exception as e:
            custom_exc = process_exception(e, func.__name__)
            return JSONResponse(
                status_code=custom_exc.status_code,
                content={
                    "error": custom_exc.user_message,
                    "detail": custom_exc.tech_message,
                },
            )

    return wrapper
