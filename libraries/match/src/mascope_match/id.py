"""
ID generation utilities for the match library.

TODO refactor to db lib? It is same as `gen_id` util used in the Mascope backend.
"""

from nanoid import generate


# Used the same alphabet as the backend `gen_id` for consistency
alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890"


def generate_id(length: int = 16) -> str:
    """Generate a random ID of specified length.

    :param length: Length of the ID to generate, defaults to 16
    :type length: int, optional
    :return: Random ID string
    :rtype: str
    """
    return generate(alphabet, length)
