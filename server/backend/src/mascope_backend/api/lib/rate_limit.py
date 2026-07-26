"""
Redis-backed, per-client rate limiting for sensitive endpoints.

Exposed as a FastAPI dependency factory so a limit can be attached to routes
we do not own (e.g. the fastapi-users login route) as well as our own, via the
router/route ``dependencies=[...]`` argument. Counting uses the shared async
Redis connection (``redis_storage_client``), so a limit is enforced
consistently across all uvicorn workers rather than per-process.

The window is a simple fixed window: the first request for a key sets the
counter's expiry, and each request increments it until the window rolls over.
This is intentionally lightweight; it is meant to blunt brute-force and
credential-stuffing bursts, not to be a precise quota system.
"""

from fastapi import HTTPException, Request, status

from mascope_backend.runtime import runtime
from mascope_backend.socket.storage import redis_storage_client


def _client_ip(request: Request) -> str:
    """
    Best-effort client IP for rate-limit keying.

    Prefer ``X-Real-IP``, which nginx sets to the real peer address and
    overwrites on every request, so a client cannot spoof it (and the backend
    has no host port, so nginx is the only way in). Fall back to the direct
    peer address for setups without the proxy (dev, or a direct connection).

    :param request: Incoming request.
    :return: Client IP string, or ``"unknown"`` if it cannot be determined.
    """
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "unknown"


async def _over_fixed_window(key: str, times: int, seconds: int) -> int | None:
    """
    Increment the fixed-window counter for ``key`` and report whether the
    caller is over the limit.

    :param key: Redis key namespacing this window.
    :param times: Maximum number of hits allowed within the window.
    :param seconds: Window length in seconds.
    :return: ``Retry-After`` seconds if the limit is exceeded, else ``None``.
    :raises Exception: On any Redis error, so callers can fail open.
    """
    client = redis_storage_client.client
    count = await client.incr(key)
    if count == 1:
        # First hit in this window: start the expiry countdown.
        await client.expire(key, seconds)
    if count > times:
        retry_after = await client.ttl(key)
        # ttl can be -1 (no expiry set due to a race); fall back to the full
        # window so the header is always sensible.
        if retry_after is None or retry_after < 0:
            retry_after = seconds
        return retry_after
    return None


def rate_limit(*, times: int, seconds: int, scope: str):
    """
    Build a dependency that allows at most ``times`` requests per ``seconds``
    per client IP for the given ``scope``.

    On limit exceed it raises ``429 Too Many Requests`` with a ``Retry-After``
    header. If Redis is unavailable the check fails open (the request is
    allowed) and logs an error -- the app already requires Redis to function,
    so a Redis outage is a broader failure than the rate limiter, and we prefer
    not to lock every user out on a transient blip.

    :param times: Maximum number of requests allowed within the window.
    :param seconds: Window length in seconds.
    :param scope: Namespacing label so different endpoints count independently.
    :return: An async FastAPI dependency callable.
    """

    async def dependency(request: Request) -> None:
        ip = _client_ip(request)
        key = f"mascope:ratelimit:{scope}:{ip}"
        try:
            retry_after = await _over_fixed_window(key, times, seconds)
        except Exception:
            # Fail open on Redis errors, but make the gap visible.
            runtime.logger.exception(f"Rate limit check failed for scope '{scope}'")
            return
        if retry_after is not None:
            # Expected throttling of a noisy client, not a server fault.
            runtime.logger.info(f"Rate limit exceeded for scope '{scope}' from {ip}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please wait and try again.",
                headers={"Retry-After": str(retry_after)},
            )

    return dependency


def rate_limit_login_by_account(
    *, times: int, seconds: int, scope: str = "auth-login-account"
):
    """
    Build a dependency that limits login attempts **per account**, keyed on the
    submitted login identifier (the form ``username`` field).

    This complements the per-IP :func:`rate_limit`: on its own the per-IP limit
    does not stop a distributed attack that guesses one account's password from
    many rotating IPs. Keying on the account blunts that.

    No-ops when the request carries no form identifier (e.g. logout, which
    shares the auth router), and fails open on Redis errors like
    :func:`rate_limit`.

    Trade-off: because it counts by account, sustained bogus attempts against a
    known address can briefly delay that user's own logins. The window is short
    and self-expiring, and the threshold is set well above normal use, so this
    only bites under an actual attack.

    :param times: Maximum login attempts allowed per account within the window.
    :param seconds: Window length in seconds.
    :param scope: Namespacing label for the Redis keys.
    :return: An async FastAPI dependency callable.
    """

    async def dependency(request: Request) -> None:
        try:
            form = await request.form()
        except Exception:
            # Not a form-encoded request (nothing to key on); let it through.
            return
        identifier = form.get("username")
        if not identifier:
            return
        account = str(identifier).strip().lower()
        key = f"mascope:ratelimit:{scope}:{account}"
        try:
            retry_after = await _over_fixed_window(key, times, seconds)
        except Exception:
            runtime.logger.exception("Account login rate limit check failed")
            return
        if retry_after is not None:
            # Expected throttling of a noisy client, not a server fault.
            runtime.logger.info(f"Login rate limit exceeded for account '{account}'")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    "Too many login attempts for this account. "
                    "Please wait and try again."
                ),
                headers={"Retry-After": str(retry_after)},
            )

    return dependency
