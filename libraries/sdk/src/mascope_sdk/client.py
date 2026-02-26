"""Mascope API Client.

This module provides the main client class for interacting with the Mascope API.
"""

import os
from pathlib import Path
from typing import Any

from .exceptions import ConfigurationError


def _parse_env_file(env_path: Path) -> dict[str, str]:
    """Parse a .env file and return a dictionary of key-value pairs.

    This is a simple parser that handles basic .env files without requiring
    the python-dotenv package.

    :param env_path: Path to the .env file.
    :type env_path: Path
    :return: Dictionary of environment variables from the file.
    :rtype: dict[str, str]
    """
    env_vars: dict[str, str] = {}

    if not env_path.exists():
        return env_vars

    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue
            # Handle key=value pairs
            if "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip()
                # Remove surrounding quotes if present
                if (value.startswith('"') and value.endswith('"')) or (
                    value.startswith("'") and value.endswith("'")
                ):
                    value = value[1:-1]
                env_vars[key] = value

    return env_vars


def _load_env_file(env_path: Path | str | None = None) -> dict[str, str]:
    """Load environment variables from a .env file.

    Searches for .env file in the following order:
    1. Explicitly provided path
    2. Current working directory
    3. Parent directories (up to 5 levels)

    :param env_path: Optional explicit path to .env file.
    :type env_path: Path | str | None, optional
    :return: Dictionary of loaded environment variables.
    :rtype: dict[str, str]
    """
    if env_path is not None:
        path = Path(env_path)
        if path.exists():
            return _parse_env_file(path)
        return {}

    # Search in current directory and parent directories
    cwd = Path.cwd()
    search_paths = [cwd] + list(cwd.parents)[:5]

    for directory in search_paths:
        env_file = directory / ".env"
        if env_file.exists():
            return _parse_env_file(env_file)

    return {}


class MascopeClient:
    """Client for interacting with the Mascope API.

    The client can be configured in several ways:

    1. **Environment variables** (recommended for production):
        Set `MASCOPE_URL` and `MASCOPE_ACCESS_TOKEN` environment variables.

    2. **`.env` file** (recommended for Jupyter notebooks):
        Create a `.env` file in your working directory or any parent directory::

            MASCOPE_URL=https://your-mascope-instance.com
            MASCOPE_ACCESS_TOKEN=your-api-token

    3. **Explicit parameters**:
        Pass `url` and `access_token` directly to the constructor.

    Configuration priority (highest to lowest):
        1. Constructor parameters
        2. Environment variables
        3. `.env` file

    :ivar url: The base URL of the Mascope instance.
    :vartype url: str
    :ivar access_token: The API access token.
    :vartype access_token: str
    :ivar workspaces: Resource for workspace operations.
    :vartype workspaces: WorkspacesResource
    :ivar batches: Resource for sample batch operations.
    :vartype batches: BatchesResource
    :ivar samples: Resource for sample operations.
    :vartype samples: SamplesResource
    :ivar matching: Resource for compound matching operations.
    :vartype matching: MatchingResource
    :ivar cheminfo: Resource for chemical information queries.
    :vartype cheminfo: ChemInfoResource

    Example::

        from mascope_sdk import MascopeClient

        # Auto-configure from .env or environment variables
        mascope = MascopeClient()

        # List all workspaces
        workspaces = mascope.workspaces.list()

        # Get samples from a batch
        samples = mascope.samples.list(sample_batch_id="batch-123")

        # Get spectrum data
        spectrum = mascope.samples.get_spectrum(sample_id="sample-456")
    """

    def __init__(
        self,
        url: str | None = None,
        access_token: str | None = None,
        *,
        env_file: Path | str | None = None,
        verify_ssl: bool = False,
        service_name: str = "mascope_sdk",
    ):
        """Initialize the Mascope client.

        :param url: The base URL of the Mascope instance.
                    Falls back to ``MASCOPE_URL`` environment variable.
        :type url: str, optional
        :param access_token: The API access token.
                            Falls back to ``MASCOPE_ACCESS_TOKEN`` environment variable.
        :type access_token: str, optional
        :param env_file: Optional path to a ``.env`` file. If not provided, searches
                        for ``.env`` in the current directory and parent directories.
        :type env_file: Path | str | None, optional
        :param verify_ssl: Whether to verify SSL certificates. Defaults to False
                          for compatibility with self-signed certificates.
        :type verify_ssl: bool, optional
        :param service_name: Service name for request headers.
        :type service_name: str, optional
        :raises ConfigurationError: If URL or access token cannot be determined.

        Example::

            # Using .env file (automatic)
            mascope = MascopeClient()

            # Explicit configuration
            mascope = MascopeClient(
                url="https://mascope.example.com",
                access_token="your-token"
            )

            # Custom .env file location
            mascope = MascopeClient(env_file="/path/to/.env")
        """
        # Load .env file
        env_vars = _load_env_file(env_file)

        # Resolve URL (parameter > env var > .env file)
        self._url = url or os.environ.get("MASCOPE_URL") or env_vars.get("MASCOPE_URL")
        if not self._url:
            raise ConfigurationError(
                "Mascope URL not configured. "
                "Set MASCOPE_URL environment variable, create a .env file, "
                "or pass url parameter to MascopeClient()."
            )

        # Normalize URL (remove trailing slash)
        self._url = self._url.rstrip("/")

        # Resolve access token (parameter > env var > .env file)
        self._access_token = (
            access_token
            or os.environ.get("MASCOPE_ACCESS_TOKEN")
            or env_vars.get("MASCOPE_ACCESS_TOKEN")
        )
        if not self._access_token:
            raise ConfigurationError(
                "Mascope access token not configured. "
                "Set MASCOPE_ACCESS_TOKEN environment variable, create a .env file, "
                "or pass access_token parameter to MascopeClient()."
            )

        self._verify_ssl = verify_ssl
        self._service_name = service_name

        # Initialize resource objects (lazy imports to avoid circular dependencies)
        self._workspaces: Any = None
        self._batches: Any = None
        self._samples: Any = None
        self._matching: Any = None
        self._cheminfo: Any = None
        self._ionization: Any = None

    @property
    def url(self) -> str:
        """The base URL of the Mascope instance."""
        return self._url

    @property
    def access_token(self) -> str:
        """The API access token."""
        return self._access_token

    @property
    def workspaces(self) -> "WorkspacesResource":
        """Resource for workspace operations."""
        if self._workspaces is None:
            from .resources.workspaces import WorkspacesResource

            self._workspaces = WorkspacesResource(self)
        return self._workspaces

    @property
    def batches(self) -> "BatchesResource":
        """Resource for sample batch operations."""
        if self._batches is None:
            from .resources.batches import BatchesResource

            self._batches = BatchesResource(self)
        return self._batches

    @property
    def samples(self) -> "SamplesResource":
        """Resource for sample operations."""
        if self._samples is None:
            from .resources.samples import SamplesResource

            self._samples = SamplesResource(self)
        return self._samples

    @property
    def matching(self) -> "MatchingResource":
        """Resource for compound matching operations."""
        if self._matching is None:
            from .resources.matching import MatchingResource

            self._matching = MatchingResource(self)
        return self._matching

    @property
    def cheminfo(self) -> "ChemInfoResource":
        """Resource for chemical information queries."""
        if self._cheminfo is None:
            from .resources.cheminfo import ChemInfoResource

            self._cheminfo = ChemInfoResource(self)
        return self._cheminfo

    @property
    def ionization(self) -> "IonizationResource":
        """Resource for ionization mechanism operations."""
        if self._ionization is None:
            from .resources.ionization import IonizationResource

            self._ionization = IonizationResource(self)
        return self._ionization

    def __repr__(self) -> str:
        return f"MascopeClient(url='{self._url}')"


# Type hints for lazy-loaded resources
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .resources.batches import BatchesResource
    from .resources.cheminfo import ChemInfoResource
    from .resources.ionization import IonizationResource
    from .resources.matching import MatchingResource
    from .resources.samples import SamplesResource
    from .resources.workspaces import WorkspacesResource
