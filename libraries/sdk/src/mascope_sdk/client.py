"""Mascope API Client.

This module provides the main client class for interacting with the Mascope API.
"""

# pylint: disable=import-outside-toplevel

import os
import sys
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import dotenv_values, find_dotenv
from loguru import logger
from tqdm import tqdm

from .exceptions import ConfigurationError

# Track whether we've already configured the SDK's loguru handler
_log_handler_id: int | None = None


def _configure_logging(env_vars: dict[str, str | None]) -> None:
    """Configure the SDK's loguru handler (env var > .env > default INFO)."""
    global _log_handler_id  # pylint: disable=global-statement

    level = (
        os.environ.get("MASCOPE_SDK_LOG_LEVEL")
        or env_vars.get("MASCOPE_SDK_LOG_LEVEL")
        or "INFO"
    ).upper()

    if _log_handler_id is not None:
        logger.remove(_log_handler_id)
    else:
        # First call: remove loguru's default handler to avoid double logging
        logger.remove()

    _log_handler_id = logger.add(
        lambda msg: tqdm.write(
            msg, end="", file=sys.stderr
        ),  # Use tqdm.write for clean logging alongside progress bars
        level=level,
        filter="mascope_sdk",
        colorize=True,
    )


class MascopeClient:
    """Client for interacting with the Mascope API.

    The client can be configured in several ways:

    1. **Environment variables** (recommended for production):
        Set `MASCOPE_URL` and `MASCOPE_ACCESS_TOKEN` environment variables.

    2. **`.env` file** (recommended for Jupyter notebooks):
        Create a `.env` file in your working directory or any parent directory::

            MASCOPE_URL=https://example.mascope.app
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
        verify_ssl: bool | None = None,
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
        :param verify_ssl: Whether to verify SSL certificates. Defaults to True.
        :type verify_ssl: bool, optional
        :param service_name: Service name for request headers.
        :type service_name: str, optional
        :raises ConfigurationError: If URL or access token cannot be determined.

        Example::

            # Using .env file (automatic)
            mascope = MascopeClient()

            # Explicit configuration
            mascope = MascopeClient(
                url="https://example.mascope.app",
                access_token="your-token"
            )

            # Custom .env file location
            mascope = MascopeClient(env_file="/path/to/.env")
        """
        # Load .env file
        dotenv_path = (
            str(env_file) if env_file is not None else find_dotenv(usecwd=True)
        )
        env_vars = dotenv_values(dotenv_path) if dotenv_path else {}

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

        # Resolve verify_ssl (parameter > env var > .env > default True)
        if verify_ssl is None:
            env_val = os.environ.get("MASCOPE_SDK_VERIFY_SSL") or env_vars.get(
                "MASCOPE_SDK_VERIFY_SSL"
            )
            self._verify_ssl = (
                env_val.lower() not in ("0", "false", "no") if env_val else True
            )
        else:
            self._verify_ssl = verify_ssl

        self._service_name = service_name

        # Configure loguru log level (env var > .env > default INFO)
        _configure_logging(env_vars)

        # Metadata cache for workspace/batch/sample listings
        self._cache: dict[str, pd.DataFrame] = {}

        # Initialize resource objects (lazy imports to avoid circular dependencies)
        self._workspaces: Any = None
        self._batches: Any = None
        self._samples: Any = None
        self._matching: Any = None
        self._cheminfo: Any = None
        self._ionization: Any = None

        # Pre-instantiate workspaces resource for early error detection
        self.workspaces.list()

    @property
    def url(self) -> str:
        """The base URL of the Mascope instance."""
        return self._url  # type: ignore

    @property
    def access_token(self) -> str:
        """The API access token."""
        return self._access_token  # type: ignore

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

    def load_peaks(
        self,
        workspace: str,
        batches: str | None = None,
        *,
        samples: str | None = None,
        matches: bool = True,
        areas: bool = True,
        heights: bool = True,
        average: bool = True,
        confirm_above: int | None = 100,
        max_workers: int = 8,
    ) -> pd.DataFrame | None:
        """Load peaks for all samples across one or more batches.

        This is a high-level convenience method that handles the typical workflow
        of selecting a workspace, filtering batches by name, iterating all samples,
        and concatenating peak data into a single DataFrame enriched with batch and
        sample metadata.

        Requests are made concurrently for better performance. A progress bar is
        displayed during loading.

        :param workspace: Workspace name (or substring) or workspace ID.
        :type workspace: str
        :param batches: Optional substring filter on batch names (case-insensitive).
                        If not provided, all batches in the workspace are loaded.
        :type batches: str, optional
        :param samples: Optional substring filter on sample names (case-insensitive).
        :type samples: str, optional
        :param matches: Include matched compounds/ions/isotopes. Defaults to True.
        :type matches: bool
        :param areas: Include peak areas. Defaults to True.
        :type areas: bool
        :param heights: Include peak heights. Defaults to True.
        :type heights: bool
        :param average: Return averaged data across time. Defaults to True.
        :type average: bool
        :param confirm_above: If the number of samples exceeds this threshold,
                              an interactive confirmation prompt is shown before
                              loading starts. Set to ``None`` to disable.
                              Defaults to 100.
        :type confirm_above: int | None
        :param max_workers: Maximum number of concurrent requests. Defaults to 8.
        :type max_workers: int
        :return: A DataFrame containing all peaks enriched with columns:

            - ``sample_batch_name``: Name of the batch the sample belongs to
            - ``sample_item_name``: Name of the sample
            - ``datetime_utc``: Measurement start timestamp (UTC)

            Plus all columns from :meth:`~mascope_sdk.resources.samples.SamplesResource.get_peaks`.
            Returns None if no peaks are found.
        :rtype: pd.DataFrame | None
        :raises ValueError: If the workspace or batches cannot be resolved.
        :raises KeyboardInterrupt: If the user declines the confirmation prompt.

        Example::

            mascope = MascopeClient()

            # Load all peaks from batches containing "Uronium"
            peaks = mascope.load_peaks(
                workspace="My Workspace",
                batches="Uronium",
            )

            # Filter to specific samples
            peaks = mascope.load_peaks(
                workspace="My Workspace",
                samples="blank",
            )

            # Load all peaks, skip confirmation
            peaks = mascope.load_peaks(
                workspace="My Workspace",
                confirm_above=None,
            )
        """
        from ._loaders import load_peaks as _load_peaks

        return _load_peaks(
            self,
            workspace,
            batches,
            samples=samples,
            matches=matches,
            areas=areas,
            heights=heights,
            average=average,
            confirm_above=confirm_above,
            max_workers=max_workers,
        )

    def load_peak_timeseries(
        self,
        workspace: str,
        batches: str | None = None,
        *,
        samples: str | None = None,
        compound: str | list[str] | None = None,
        ion: str | list[str] | None = None,
        isotope: str | list[str] | None = None,
        confirm_above: int | None = 20,
        max_workers: int = 8,
    ) -> pd.DataFrame | None:
        """Load intra-sample peak timeseries for matched peaks across batches.

        Resolves a compound, ion, or isotope formula to the corresponding peak
        IDs via match data, then fetches the per-scan timeseries for each peak
        in each sample. The hierarchy is:
        compound -> ions -> isotopes -> peaks (1:1).

        Provide exactly one of ``compound``, ``ion``, or ``isotope``. Each
        accepts a single string or a list of strings to load timeseries for
        multiple targets in a single pass.

        Requests are made concurrently for better performance. Two progress bars
        are displayed: one for peak discovery and one for timeseries loading.

        :param workspace: Workspace name (or substring) or workspace ID.
        :type workspace: str
        :param batches: Optional substring filter on batch names (case-insensitive).
        :type batches: str, optional
        :param samples: Optional substring filter on sample names (case-insensitive).
        :type samples: str, optional
        :param compound: Target compound name(s) or formula(s).
        :type compound: str | list[str], optional
        :param ion: Target ion formula(s).
        :type ion: str | list[str], optional
        :param isotope: Target isotope formula(s).
        :type isotope: str | list[str], optional
        :param confirm_above: If the number of samples exceeds this threshold,
                              an interactive confirmation prompt is shown before
                              loading starts. Set to ``None`` to disable.
                              Defaults to 20.
        :type confirm_above: int | None
        :param max_workers: Maximum number of concurrent requests. Defaults to 8.
        :type max_workers: int
        :return: A DataFrame with one row per time point per peak, containing:

                 - ``sample_batch_name``: Batch name
                 - ``sample_item_id``: Sample ID
                 - ``sample_item_name``: Sample name
                 - ``datetime_utc``: Absolute datetime per data point (UTC)
                 - ``peak_id``: Peak identifier
                 - ``mz``: Actual m/z of the peak
                 - ``target_compound_name``, ``target_compound_formula``,
                   ``target_ion_formula``, ``target_isotope_formula``: Match metadata
                 - ``time``: Relative time in seconds within the sample
                 - ``height``: Intensity at each time point

                 Returns None if no matching peaks are found.
        :rtype: pd.DataFrame | None
        :raises ValueError: If zero or more than one formula parameter is provided.
        :raises KeyboardInterrupt: If the user declines the confirmation prompt.

        Example::

            mascope = MascopeClient()

            # Single compound
            ts = mascope.load_peak_timeseries(
                workspace="My Workspace",
                batches="Uronium",
                compound="CH4N2O",
            )

            # Multiple compounds in one call
            ts = mascope.load_peak_timeseries(
                workspace="My Workspace",
                compound=["CH4N2O", "Lactic acid"],
            )
        """
        from ._loaders import load_peak_timeseries as _load_peak_timeseries

        return _load_peak_timeseries(
            self,
            workspace,
            batches,
            samples=samples,
            compound=compound,
            ion=ion,
            isotope=isotope,
            confirm_above=confirm_above,
            max_workers=max_workers,
        )

    def load_peaks_by_stage(
        self,
        sample: str,
        stages: list[tuple[float, float] | tuple[float, float, str]],
        *,
        matches: bool = True,
        areas: bool = True,
        heights: bool = True,
        max_workers: int = 8,
    ) -> pd.DataFrame | None:
        """Load averaged peaks for each time-range stage of a single sample.

        For each stage (time range), requests the averaged peak list and
        concatenates everything into a single DataFrame. Useful when a
        measurement has distinct phases (e.g. blank, sample introduction, wash).

        :param sample: Sample name or sample ID.
        :type sample: str
        :param stages: List of time-range tuples. Each element can be
                       ``(t_min, t_max)`` or ``(t_min, t_max, name)`` where
                       *name* is a human-readable label for the stage.
        :type stages: list[tuple[float, float] | tuple[float, float, str]]
        :param matches: Include matched compounds/ions/isotopes. Defaults to True.
        :type matches: bool
        :param areas: Include peak areas. Defaults to True.
        :type areas: bool
        :param heights: Include peak heights. Defaults to True.
        :type heights: bool
        :param max_workers: Maximum number of concurrent requests. Defaults to 8.
        :type max_workers: int
        :return: A DataFrame with stage-enriched peak data. Extra columns:

                 - ``stage``: 0-based stage index
                 - ``stage_name``: Stage label (or None)
                 - ``t_min`` / ``t_max``: Time range in seconds

                 Returns None if no peaks are found.
        :rtype: pd.DataFrame | None

        Example::

            mascope = MascopeClient()

            stages = [
                (0, 30, "blank"),
                (30, 120, "sample"),
                (120, 180, "wash"),
            ]

            peaks = mascope.load_peaks_by_stage(
                sample="my-sample-id",
                stages=stages,
            )

            peaks.groupby("stage_name")["area"].sum()
        """
        from ._loaders import load_peaks_by_stage as _load_peaks_by_stage

        return _load_peaks_by_stage(
            self,
            sample,
            stages,
            matches=matches,
            areas=areas,
            heights=heights,
            max_workers=max_workers,
        )

    def clear_cache(self) -> None:
        """Clear the metadata cache.

        Call this when workspaces, batches, or samples have changed on the
        server and you want subsequent calls to fetch fresh data.

        Example::

            mascope.clear_cache()
        """
        self._cache.clear()

    def __repr__(self) -> str:
        return f"MascopeClient(url='{self._url}')"


# Type hints for lazy-loaded resources
# pylint: disable=wrong-import-order, wrong-import-position
from typing import TYPE_CHECKING  # noqa: E402

if TYPE_CHECKING:
    from .resources.batches import BatchesResource
    from .resources.cheminfo import ChemInfoResource
    from .resources.ionization import IonizationResource
    from .resources.matching import MatchingResource
    from .resources.samples import SamplesResource
    from .resources.workspaces import WorkspacesResource
