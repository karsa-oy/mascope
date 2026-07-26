"""Tests: api_route enforces a real auth dependency, not just a `user` param.

The decorator refuses at import/registration time to wire up a non-public route
that does not bind an auth dependency to ``user`` - closing the gap where a
handler declares a ``user`` parameter without ``Depends(...)`` and is silently
unauthenticated.
"""

import pytest
from fastapi import Depends

from mascope_backend.api.lib.api_features import api_route


def _auth_dep():
    return None


def test_route_with_depends_user_is_accepted():
    @api_route()
    async def handler(user=Depends(_auth_dep)):
        return {}

    # No exception: the user param is bound to a dependency.


def test_public_route_needs_no_user():
    @api_route(public=True)
    async def handler():
        return {}

    # No exception: explicitly public.


def test_missing_user_param_is_rejected():
    with pytest.raises(ValueError, match="user"):

        @api_route()
        async def handler():
            return {}


def test_user_without_depends_is_rejected():
    # A plain `user` parameter (no Depends) must not pass as authenticated.
    with pytest.raises(ValueError, match="user"):

        @api_route()
        async def handler(user=None):
            return {}
