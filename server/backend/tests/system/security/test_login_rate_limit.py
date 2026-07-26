"""Tests: per-account login throttling (``rate_limit_login_by_account``).

Complements the per-IP login limiter: it caps attempts against a single
identifier regardless of source IP, so a distributed credential-stuffing attack
on one account is blunted once the network firewall is removed. Fails open on
Redis errors and no-ops when the request carries no login identifier. Keys are
hashed (never the raw identifier) and a successful login clears the counter so
only failed attempts count.
"""

import hashlib

import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from httpx import ASGITransport, AsyncClient

from mascope_backend.api.lib import rate_limit as rl


class FakeRedis:
    """Minimal in-memory stand-in for the fixed-window Redis operations."""

    def __init__(self, *, fail: bool = False):
        self.counts: dict[str, int] = {}
        self.fail = fail

    async def incr(self, key: str) -> int:
        if self.fail:
            raise ConnectionError("redis down")
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]

    async def expire(self, key: str, seconds: int) -> bool:
        return True

    async def ttl(self, key: str) -> int:
        return 42

    async def delete(self, key: str) -> int:
        return 1 if self.counts.pop(key, None) is not None else 0


class FakeRequest:
    """Stand-in request whose ``form()`` returns fixed data (or raises)."""

    def __init__(self, form_data):
        self._form_data = form_data

    async def form(self):
        if self._form_data is None:
            raise ValueError("not a form request")
        return self._form_data


@pytest.fixture
def fake_redis(monkeypatch):
    # Patches the client's private ``_client`` attribute (what the ``client``
    # property returns) rather than a public seam - if the storage client is
    # ever refactored, this fixture is why these tests break.
    redis = FakeRedis()
    monkeypatch.setattr(rl.redis_storage_client, "_client", redis)
    return redis


async def _call_n(dep, request, n):
    """Invoke the dependency ``n`` times, returning the last raised status (or None)."""
    status_code = None
    for _ in range(n):
        try:
            await dep(request)
        except HTTPException as exc:
            status_code = exc.status_code
    return status_code


@pytest.mark.asyncio
async def test_blocks_account_after_limit(fake_redis):
    dep = rl.rate_limit_login_by_account(times=2, seconds=60)
    req = FakeRequest({"username": "victim@test.com", "password": "x"})

    # First two attempts pass; the third is blocked with 429 + Retry-After.
    assert await _call_n(dep, req, 2) is None
    with pytest.raises(HTTPException) as exc:
        await dep(req)
    assert exc.value.status_code == 429
    assert "Retry-After" in exc.value.headers


@pytest.mark.asyncio
async def test_distinct_accounts_are_independent(fake_redis):
    dep = rl.rate_limit_login_by_account(times=2, seconds=60)
    victim = FakeRequest({"username": "victim@test.com"})
    other = FakeRequest({"username": "someone-else@test.com"})

    await _call_n(dep, victim, 3)  # drive victim over the limit
    # A different account is unaffected.
    assert await _call_n(dep, other, 2) is None


@pytest.mark.asyncio
async def test_identifier_is_normalized(fake_redis):
    dep = rl.rate_limit_login_by_account(times=2, seconds=60)
    # Same account with different casing/whitespace shares one counter.
    await dep(FakeRequest({"username": "  Victim@Test.com "}))
    await dep(FakeRequest({"username": "victim@test.com"}))
    with pytest.raises(HTTPException):
        await dep(FakeRequest({"username": "VICTIM@TEST.COM"}))


@pytest.mark.asyncio
async def test_redis_key_is_hashed_and_fixed_size(fake_redis):
    """Keys embed a digest, never the raw (attacker-controlled) identifier.

    Hashing keeps key size fixed no matter how long the submitted username is,
    and keeps the typed value (occasionally a password) out of Redis keyspace.
    """
    dep = rl.rate_limit_login_by_account(times=5, seconds=60)
    identifier = "victim@test.com" + "x" * 10_000
    await dep(FakeRequest({"username": identifier}))

    (key,) = fake_redis.counts.keys()
    assert identifier not in key
    assert "victim" not in key
    digest = hashlib.sha256(identifier.strip().lower().encode()).hexdigest()
    assert key.endswith(digest)


@pytest.mark.asyncio
async def test_successful_login_clears_the_counter(fake_redis):
    """clear_login_rate_limit resets the account budget (failures-only count).

    Driven over the limit, then cleared as on_after_login does on a successful
    sign-in: the account may immediately attempt again.
    """
    dep = rl.rate_limit_login_by_account(times=2, seconds=60)
    req = FakeRequest({"username": "victim@test.com", "password": "x"})

    await _call_n(dep, req, 3)  # over the limit
    with pytest.raises(HTTPException):
        await dep(req)

    await rl.clear_login_rate_limit("victim@test.com")
    assert await _call_n(dep, req, 2) is None  # budget restored


@pytest.mark.asyncio
async def test_clear_normalizes_like_the_limiter(fake_redis):
    """Clearing with a differently-cased identifier hits the same counter."""
    dep = rl.rate_limit_login_by_account(times=1, seconds=60)
    await _call_n(dep, FakeRequest({"username": "victim@test.com"}), 2)

    await rl.clear_login_rate_limit("  Victim@Test.com ")
    assert fake_redis.counts == {}


@pytest.mark.asyncio
async def test_clear_swallows_redis_errors(monkeypatch):
    """Clearing is best-effort: a Redis outage must not fail the login."""
    monkeypatch.setattr(rl.redis_storage_client, "_client", FakeRedis(fail=True))

    async def failing_delete(key):
        raise ConnectionError("redis down")

    monkeypatch.setattr(rl.redis_storage_client._client, "delete", failing_delete)
    await rl.clear_login_rate_limit("victim@test.com")  # never raises


@pytest.mark.asyncio
async def test_no_username_is_noop(fake_redis):
    dep = rl.rate_limit_login_by_account(times=1, seconds=60)
    # e.g. logout shares the auth router but sends no identifier.
    for _ in range(5):
        await dep(FakeRequest({"grant_type": "refresh"}))  # never raises


@pytest.mark.asyncio
async def test_non_form_request_is_noop(fake_redis):
    dep = rl.rate_limit_login_by_account(times=1, seconds=60)
    for _ in range(5):
        await dep(FakeRequest(None))  # form() raises -> treated as nothing to key on


@pytest.mark.asyncio
async def test_fails_open_on_redis_error(monkeypatch):
    monkeypatch.setattr(rl.redis_storage_client, "_client", FakeRedis(fail=True))
    dep = rl.rate_limit_login_by_account(times=1, seconds=60)
    req = FakeRequest({"username": "victim@test.com"})
    # Redis unavailable must not lock users out.
    for _ in range(5):
        await dep(req)  # never raises


@pytest.mark.asyncio
async def test_limiter_coexists_with_oauth_form_handler(monkeypatch):
    """The limiter reads the form, but the login handler still parses it.

    Mirrors the real wiring: a route-level limiter dependency runs before the
    handler's ``OAuth2PasswordRequestForm``. Both call ``request.form()``;
    Starlette caches it, so consuming it in the dependency must not starve the
    handler.
    """
    monkeypatch.setattr(rl.redis_storage_client, "_client", FakeRedis())
    app = FastAPI()

    @app.post(
        "/login",
        dependencies=[Depends(rl.rate_limit_login_by_account(times=5, seconds=60))],
    )
    async def login(creds: OAuth2PasswordRequestForm = Depends()):
        return {"user": creds.username}

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/login", data={"username": "a@b.com", "password": "secret"}
        )
    assert resp.status_code == 200
    assert resp.json()["user"] == "a@b.com"
