"""Reader-backend seam for ``mascope_thermo``.

Selects the file-reading implementation behind a single switch so the public
functions in :mod:`mascope_thermo.thermo` can run on either Thermo's
RawFileReader (the current default) or — once implemented — the open-source
OpenTFRaw reader, without the callers caring which.

Select with the ``MASCOPE_THERMO_BACKEND`` environment variable::

    "thermo"     -> ThermoBackend (default; pythonnet + bundled .NET DLLs)
    "opentfraw"  -> OpenTFRawBackend (built in a later migration step)

See ``libraries/thermo/OpenTFRaw_migration_execution_plan.md`` (§3) for the
rationale (a capability protocol, not an emulation of the .NET RawFile object).

This is introduced incrementally: :class:`ReaderBackend` lists only the
capabilities of functions already migrated onto the seam. More methods (profile
arrays, centroids, multi-scan averaging, XIC, trailer, run header, ...) are
added as the remaining ``thermo.py`` functions move over.
"""

from __future__ import annotations

import os
from typing import Literal, Protocol, runtime_checkable

import numpy as np


ENV_BACKEND = "MASCOPE_THERMO_BACKEND"

Polarity = Literal["+", "-"]
MsType = Literal["Ms", "Ms2"]


@runtime_checkable
class ReaderBackend(Protocol):
    """Capability interface the :mod:`mascope_thermo.thermo` functions depend on.

    Implementations are context managers: open the file in ``__enter__`` and
    release it in ``__exit__``. All methods return backend-neutral Python/NumPy
    data (never .NET objects), so callers are backend-agnostic.
    """

    def __enter__(self) -> ReaderBackend: ...
    def __exit__(self, *exc) -> None: ...

    def polarities(self) -> set[str]:
        """Set of polarities present in the file, as ``"+"`` / ``"-"``."""
        ...

    def scan_times(
        self,
        polarity: Polarity | None = None,
        t_min: float | None = None,
        t_max: float | None = None,
        ms_type: MsType | None = "Ms",
    ) -> np.ndarray:
        """Scan start times [s] for the scans matching the given filters."""
        ...

    def tic_per_scan(
        self,
        polarity: Polarity | None = None,
        t_min: float | None = None,
        t_max: float | None = None,
        ms_type: MsType | None = "Ms",
    ) -> tuple[np.ndarray, np.ndarray]:
        """``(scan_times_s, tic)`` for the scans matching the given filters."""
        ...

    def instrument_details(self) -> dict:
        """Instrument metadata dict (Name, Model, SerialNumber, ...)."""
        ...


# Field set returned by GetInstrumentData (excluding non-serializable
# ChannelLabels / Units). Kept here so every backend reports the same shape.
INSTRUMENT_FIELDS = (
    "Name",
    "Model",
    "SerialNumber",
    "SoftwareVersion",
    "HardwareVersion",
    "Flags",
    "AxisLabelX",
    "AxisLabelY",
    "IsValid",
    "HasAccurateMassPrecursors",
)


class ThermoBackend:
    """:class:`ReaderBackend` backed by Thermo RawFileReader via pythonnet.

    Wraps the existing ``RawFileManager`` + ``ScanSelector`` machinery in
    :mod:`mascope_thermo.thermo` (imported lazily to avoid an import cycle).
    """

    def __init__(self, datafile_path: str):
        self.datafile_path = datafile_path
        self._mgr = None
        self._raw = None

    def __enter__(self) -> ThermoBackend:
        from mascope_thermo.thermo import RawFileManager

        self._mgr = RawFileManager(self.datafile_path)
        self._raw = self._mgr.__enter__()
        return self

    def __exit__(self, *exc) -> None:
        try:
            if self._mgr is not None:
                self._mgr.__exit__(*exc)
        finally:
            self._mgr = None
            self._raw = None

    def _selector(
        self,
        polarity: Polarity | None = None,
        t_min: float | None = None,
        t_max: float | None = None,
        ms_type: MsType | None = "Ms",
    ):
        from mascope_thermo.thermo import ScanSelector

        return ScanSelector(
            self._raw,
            polarity=polarity,
            t_min=t_min,
            t_max=t_max,
            ms_type=ms_type,
        )

    def polarities(self) -> set[str]:
        out: set[str] = set()
        for scan_filter in self._selector(ms_type=None).raw_scan_filters:
            verbose = scan_filter.Polarity.ToString()
            if verbose == "Positive":
                out.add("+")
            elif verbose == "Negative":
                out.add("-")
        return out

    def scan_times(
        self,
        polarity: Polarity | None = None,
        t_min: float | None = None,
        t_max: float | None = None,
        ms_type: MsType | None = "Ms",
    ) -> np.ndarray:
        return self._selector(polarity, t_min, t_max, ms_type).scan_times

    def tic_per_scan(
        self,
        polarity: Polarity | None = None,
        t_min: float | None = None,
        t_max: float | None = None,
        ms_type: MsType | None = "Ms",
    ) -> tuple[np.ndarray, np.ndarray]:
        selector = self._selector(polarity, t_min, t_max, ms_type)
        times = selector.scan_times
        tic = np.asarray(
            [
                self._raw.GetScanStatsForScanNumber(i).TIC
                for i in selector.scan_indices_1based
            ],
            dtype=np.float64,
        )
        return times, tic

    def instrument_details(self) -> dict:
        data = self._raw.GetInstrumentData()
        return {field: getattr(data, field) for field in INSTRUMENT_FIELDS}


def open_backend(datafile_path: str) -> ReaderBackend:
    """Open ``datafile_path`` with the backend selected by ``MASCOPE_THERMO_BACKEND``.

    Returns a context manager. Defaults to the Thermo backend, preserving today's
    behaviour when the variable is unset.
    """
    name = os.environ.get(ENV_BACKEND, "thermo").lower()
    if name == "thermo":
        return ThermoBackend(datafile_path)
    if name == "opentfraw":
        raise NotImplementedError(
            "OpenTFRaw backend is not implemented yet "
            "(see OpenTFRaw_migration_execution_plan.md, step 4)."
        )
    raise ValueError(
        f"Unknown {ENV_BACKEND}={name!r}; expected 'thermo' or 'opentfraw'."
    )
