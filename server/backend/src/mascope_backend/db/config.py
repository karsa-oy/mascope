"""
Database configuration settings.

Centralized configuration for database connections, timeouts, and engine settings.
"""

from pydantic import BaseModel


class DatabaseConfig(BaseModel):
    """
    Configuration settings for database connections and operations.

    Provides consistent settings for both async SQLAlchemy engine and direct SQLite connections.
    """

    # Database timeout setting
    CONNECTION_TIMEOUT: int = 30  # How long to wait when database is locked

    # SQLAlchemy async engine settings
    POOL_SIZE: int = 20  # Base pool size - max persistent connections kept open
    MAX_OVERFLOW: int = (
        30  # Additional connections allowed beyond pool_size when needed
    )
    POOL_TIMEOUT: int = 60  # Seconds to wait for available connection before timeout
    POOL_PRE_PING: bool = True  # Check connection liveness before using from pool

    # SQLAlchemy session settings
    EXPIRE_ON_COMMIT: bool = False  # Keep objects loaded after commit

    @property
    def connect_args(self) -> dict:
        """Get connect_args dict for SQLAlchemy engine."""
        return {
            "timeout": self.CONNECTION_TIMEOUT,
        }


# Global database configuration instance
db_config = DatabaseConfig()
