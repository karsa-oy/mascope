"""
Shared test utilities for the Mascope test suite.
"""

from nanoid import generate


def gen_test_id(size: int = 16) -> str:
    """Generate a random ID of exactly `size` characters using nanoid.

    Matches the ID generation used by application models. The default size of 16
    matches the `VARCHAR(16)` constraint on primary key columns — pass `size`
    explicitly when a column has a different length constraint.

    :param size: Character length of the generated ID
    :type size: int
    :return: Random nanoid string
    :rtype: str
    """
    return generate(size=size)
