"""Helpers for turning exceptions into user-notification error strings."""


def describe_exception(e: BaseException) -> str:
    """
    Human-readable one-liner for an exception destined for a user notification.

    The bare message of common builtin exceptions is cryptic on its own - a
    ``KeyError('Configuration File')`` renders as just ``'Configuration File'``
    - so the exception class name is prefixed unless the message already reads
    as a sentence.

    :param e: The exception to describe.
    :return: A one-line description safe to show in a notification.
    :rtype: str
    """
    message = str(e).strip()
    if not message:
        return type(e).__name__
    if (
        isinstance(e, (KeyError, IndexError, TypeError, AttributeError))
        or " " not in message
    ):
        return f"{type(e).__name__}: {message}"
    return message
