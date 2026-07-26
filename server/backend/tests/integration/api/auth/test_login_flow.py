"""Tests: the real login route end-to-end (``POST /api/auth/login``).

The other integration tests mint JWTs directly, so nothing else exercises the
fastapi-users login flow - including the ``on_after_login`` hook, which now
re-reads the cached login form to clear the per-account rate-limit counter on
a successful sign-in. These tests pin that a real password login still works
with the limiter dependencies and the clearing hook wired in (both fail open
when Redis is not connected, as in this ASGI test setup).
"""

import pytest
import pytest_asyncio
from fastapi_users.password import PasswordHelper
from httpx import ASGITransport, AsyncClient

from mascope_backend.app.fast import fast
from mascope_backend.db import User


LOGIN_EMAIL = "login-flow@test.com"
LOGIN_PASSWORD = "correct-horse-battery-staple"


@pytest_asyncio.fixture
async def login_user(async_session_factory, roles):
    """A user with a real (verifiable) password hash, removed afterwards."""
    async with async_session_factory() as session:
        user = User(
            email=LOGIN_EMAIL,
            username="login_flow_user",
            hashed_password=PasswordHelper().hash(LOGIN_PASSWORD),
            is_active=True,
            is_verified=True,
            role_id=roles["guest"].role_id,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
    yield user
    async with async_session_factory() as session:
        db_user = await session.get(User, user.id)
        if db_user is not None:
            await session.delete(db_user)
            await session.commit()


@pytest.mark.asyncio
async def test_wrong_password_is_rejected(login_user):
    async with AsyncClient(
        transport=ASGITransport(app=fast), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/auth/login",
            data={"username": LOGIN_EMAIL, "password": "wrong-password"},
        )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_successful_login_sets_auth_cookie(login_user):
    """A correct password logs in; on_after_login must not break the flow."""
    async with AsyncClient(
        transport=ASGITransport(app=fast), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/auth/login",
            data={"username": LOGIN_EMAIL, "password": LOGIN_PASSWORD},
        )
    assert resp.status_code in (200, 204)
    assert "set-cookie" in resp.headers
