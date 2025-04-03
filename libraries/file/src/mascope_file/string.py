def norm(name: str, lower: bool = False) -> str:
    """
    Normalize a string by stripping leading and trailing spaces and converting to lowercase if specified.

    :param name: The string to normalize.
    :param lower: Whether to convert the string to lowercase. Defaults to False.
    :return: The normalized string.
    :rtype: str
    """
    if lower:
        name = name.lower()
    return " ".join(name.strip().split())
