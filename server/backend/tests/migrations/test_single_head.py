"""
Single-head check: assert the revision graph has exactly one head.

Multiple heads usually mean an uncaught merge conflict — two PRs both
added a migration off the same parent and were merged in parallel.
This breaks `alembic upgrade head` at deployment time. Catching it in
PR CI is the whole point.

Re-exports pytest-alembic's `test_single_head_revision`. See
`tests/README.md` (Migration tests) for the broader category context.
"""

from pytest_alembic.tests import test_single_head_revision  # noqa: F401
