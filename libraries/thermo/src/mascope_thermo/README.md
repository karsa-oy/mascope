# mascope_thermo

Reads Thermo `.raw` files for Mascope. The public functions in `thermo.py`
(centroids, profiles, XICs, averaged spectra, MS² extraction, run-header
metadata) are backend-agnostic: they run on top of a reader seam and don't care
which reader is underneath.

## Reader backends

The implementation is selected by the `MASCOPE_THERMO_BACKEND` environment
variable (see `backend.py`):

- **`opentfraw`** (default) — the open-source reader, via the
  [`mascope-opentfraw`](https://pypi.org/project/mascope-opentfraw/) wheel. No
  proprietary dependency; nothing to install beyond the package.
- **`thermo`** — Thermo's RawFileReader (.NET via pythonnet). Opt-in: it needs
  the proprietary `ThermoFisher.CommonCore.*` DLLs, which are **not** shipped in
  this repository. Point `MASCOPE_THERMO_DLL_DIR` at a directory containing them
  and set `MASCOPE_THERMO_BACKEND=thermo`.

The .NET runtime is loaded lazily and only when the Thermo backend is actually
used, so importing this package never requires .NET or the DLLs. See the
repository-root `README.md` ("Reader backend") for the user-facing setup.

## Layout

- `thermo.py` — the public, backend-agnostic reader functions.
- `backend.py` — the `ReaderBackend` seam and the two implementations.
- `lib/` — lazy .NET loader and DLL discovery for the Thermo backend.
