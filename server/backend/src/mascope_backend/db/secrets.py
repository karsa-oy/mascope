"""Database secrets management."""

from mascope_backend.runtime import runtime


postgres_password = runtime.secret("POSTGRES_PASSWORD_FILE", "postgres_password.txt")
