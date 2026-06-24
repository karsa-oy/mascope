"""
Seed fixed, well-known demo credentials into the active database.

Used by the local demo (`mascope demo`) so a newcomer can log into the web UI
and use the SDK with zero setup. Idempotent: safe to run repeatedly. It

- ensures the four roles exist (guest/editor/admin/owner),
- upserts a demo user with a fixed email/username/password (owner + superuser,
  active + verified), resetting the password each run so it always matches -
  being an owner also satisfies the app's "first owner" registration gate,
- (re)creates fixed service access tokens (mascope_sdk, file-converter,
  file-agent) with a fresh ``created_at`` so they never show up expired
  regardless of how old the restored snapshot is. The file-converter token is
  required by the upload route; file-agent is the File Agent's bearer token.

The demo user is a superuser, so it bypasses workspace-membership checks and
sees all demo data without extra wiring.

These credentials are intentionally public and for LOCAL demo use only - never
seed them into a real deployment.

Usage:
    mascope dev db script run seed_demo
    (also invoked automatically by `mascope demo`)
"""

import asyncio
from datetime import datetime, timezone

from fastapi_users.password import PasswordHelper
from sqlalchemy import delete, select

from mascope_backend.api.new.auth.config import auth_settings
from mascope_backend.db import (
    AccessToken,
    Role,
    User,
    async_session,
    configure_database_engine,
)
from mascope_backend.runtime import runtime

# --- Fixed, well-known demo credentials (LOCAL DEMO ONLY) ------------------
# Keep in sync with `_print_access()` in the mascope CLI demo command and
# docs/demo_dataset.md.
DEMO_EMAIL = "demo@mascope.app"
DEMO_USERNAME = "demo"
DEMO_PASSWORD = "mascope-demo"
# Owner so the demo user satisfies the "first owner" gate (the app shows a
# first-owner signup page until an owner-role user exists) and can do anything
# in the local demo without a separate signup step.
DEMO_ROLE = "owner"
# Fixed access tokens per service (each <= 43 chars - AccessToken.token column).
# - mascope_sdk: notebook/SDK access (MASCOPE_ACCESS_TOKEN)
# - file-converter: required internally by the upload route (get_access_token)
#   and used by the converter for its API/socket callbacks
# - file-agent: bearer token for the File Agent uploader (if used)
DEMO_TOKENS = {
    "mascope_sdk": "mascope_demo_sdk_token",
    "file-converter": "mascope_demo_file_converter_token",
    "file-agent": "mascope_demo_file_agent_token",
}
# Back-compat alias for the SDK token (referenced by docs / CLI output).
DEMO_SERVICE = "mascope_sdk"
DEMO_TOKEN = DEMO_TOKENS["mascope_sdk"]


async def _ensure_roles(session) -> None:
    """Insert any missing roles using the fixed access-level ids."""
    for name, role_id in auth_settings.ROLE_ACCESS_LEVELS.items():
        if await session.get(Role, role_id) is None:
            session.add(Role(role_id=role_id, role_name=name))
    await session.flush()


async def _upsert_demo_user(session) -> User:
    """Create or reset the demo user to the fixed credentials."""
    role_id = auth_settings.ROLE_ACCESS_LEVELS[DEMO_ROLE]
    hashed = PasswordHelper().hash(DEMO_PASSWORD)

    user = (
        await session.execute(select(User).where(User.email == DEMO_EMAIL))
    ).scalar_one_or_none()

    if user is None:
        user = User(
            email=DEMO_EMAIL,
            username=DEMO_USERNAME,
            hashed_password=hashed,
            is_active=True,
            is_verified=True,
            is_superuser=True,
            role_id=role_id,
        )
        session.add(user)
        runtime.logger.info(f"Created demo user '{DEMO_EMAIL}'")
    else:
        user.username = DEMO_USERNAME
        user.hashed_password = hashed
        user.is_active = True
        user.is_verified = True
        user.is_superuser = True
        user.role_id = role_id
        runtime.logger.info(f"Reset demo user '{DEMO_EMAIL}'")

    await session.flush()
    return user


async def _refresh_demo_tokens(session, user: User) -> None:
    """Replace the demo service tokens with fresh, non-expired ones."""
    now = datetime.now(timezone.utc)
    for service, token in DEMO_TOKENS.items():
        # Drop any prior token for this user+service, and any holder of the
        # fixed token string (the PK) from a previous run.
        await session.execute(
            delete(AccessToken).where(
                AccessToken.user_id == user.id,
                AccessToken.service_name == service,
            )
        )
        await session.execute(delete(AccessToken).where(AccessToken.token == token))
        session.add(
            AccessToken(
                token=token,
                user_id=user.id,
                service_name=service,
                created_at=now,
            )
        )


async def seed_demo() -> None:
    """Idempotently seed the demo user, roles, and SDK access token."""
    await configure_database_engine()
    async with async_session() as session:
        await _ensure_roles(session)
        user = await _upsert_demo_user(session)
        await _refresh_demo_tokens(session, user)
        await session.commit()

    runtime.logger.success(
        f"Demo credentials seeded - login '{DEMO_EMAIL}' / '{DEMO_PASSWORD}', "
        f"SDK token '{DEMO_TOKEN}' (services: {', '.join(DEMO_TOKENS)})"
    )


def main() -> None:
    """Entry point for the seed script (discovered by the CLI script runner)."""
    try:
        asyncio.run(seed_demo())
    except KeyboardInterrupt:
        runtime.logger.info("\nDemo seed cancelled by user (Ctrl+C)")
    except Exception:
        runtime.logger.exception("Demo seed script failed")
        raise


if __name__ == "__main__":
    main()
