import os
import sys

from pythonnet import load

from mascope_thermo.runtime import runtime


# Mascope ships WITHOUT the proprietary Thermo RawFileReader DLLs and uses the
# open-source OpenTFRaw backend by default. To use the Thermo backend instead,
# obtain the RawFileReader DLLs and point this environment variable at the
# directory that holds them.
ENV_DLL_DIR = "MASCOPE_THERMO_DLL_DIR"
_REQUIRED_DLL = "ThermoFisher.CommonCore.RawFileReader.dll"

initialized = False


def dll_dir() -> str | None:
    """The Thermo RawFileReader DLL directory from ``MASCOPE_THERMO_DLL_DIR``,
    or ``None`` when it is not configured."""
    path = os.environ.get(ENV_DLL_DIR)
    return os.path.abspath(path) if path else None


def thermo_available() -> bool:
    """True if the Thermo RawFileReader DLLs are configured and present."""
    d = dll_dir()
    return bool(d and os.path.isfile(os.path.join(d, _REQUIRED_DLL)))


def load_dotnet(*refs):
    global initialized

    if not initialized:
        d = dll_dir()
        if not d or not os.path.isfile(os.path.join(d, _REQUIRED_DLL)):
            raise RuntimeError(
                "Thermo RawFileReader DLLs not found. Mascope ships without them "
                "and uses the OpenTFRaw backend by default. To use the Thermo "
                f"backend, obtain the RawFileReader DLLs and set {ENV_DLL_DIR} to "
                f"the directory containing them (expected: {_REQUIRED_DLL})."
            )
        sys.path.append(d)
        runtime.logger.info(f"loaded ThermoFisher DLLs from {d}")

        load("coreclr")
        import clr

        for ref in refs:
            clr.AddReference(ref)
            runtime.logger.info(f"Added PythonNet CLR reference: {ref}")

        initialized = True
