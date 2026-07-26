"""Tests: reset/verification token secrets are derived, not hardcoded.

The former ``SECRET_RESET`` / ``SECRET_VERIFY`` constants were predictable
defaults that would let an attacker forge password-reset / email-verification
tokens if those flows were ever enabled. They are now derived per deployment
from the JWT secret with domain separation.
"""

from mascope_backend.api.new.auth.config import (
    _derive_token_secret,
    auth_settings,
)


def test_secrets_are_not_the_legacy_constants():
    assert auth_settings.RESET_PASSWORD_TOKEN_SECRET != "SECRET_RESET"
    assert auth_settings.VERIFICATION_TOKEN_SECRET != "SECRET_VERIFY"


def test_reset_and_verify_secrets_differ():
    # Domain separation: the two purposes must not share a secret.
    assert (
        auth_settings.RESET_PASSWORD_TOKEN_SECRET
        != auth_settings.VERIFICATION_TOKEN_SECRET
    )


def test_derivation_is_deterministic_and_domain_separated():
    assert _derive_token_secret("reset-password") == _derive_token_secret(
        "reset-password"
    )
    assert _derive_token_secret("a") != _derive_token_secret("b")
    # 32-byte HMAC-SHA256, hex-encoded.
    assert len(_derive_token_secret("reset-password")) == 64
