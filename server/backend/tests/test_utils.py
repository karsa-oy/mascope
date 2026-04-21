"""
Shared test utilities for the Mascope test suite.
"""

from mascope_backend.db.id import gen_id


def gen_test_id(size: int = 16) -> str:
    """Generate a random ID of exactly `size` characters.

    Delegates to `mascope_backend.db.id.gen_id` — same alphabet and
    generation logic used by application models (alphanumeric only, no
    `-` or `_`). Centralised here so test files have a single import
    point and any test-specific ID generation changes stay in one place.

    The default size of 16 matches the `VARCHAR(16)` constraint on
    primary key columns — pass `size` explicitly when a column has a
    different constraint.

    :param size: Character length of the generated ID
    :type size: int
    :return: Random alphanumeric nanoid string
    :rtype: str
    """
    return gen_id(size)
