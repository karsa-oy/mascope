import sys

from pythonnet import load

from mascope_thermo.runtime import runtime


initialized = False


def load_dotnet(*refs):
    global initialized

    if not initialized:
        dll_path = runtime.path("./libraries/thermo/src/mascope_thermo/lib/dlls/")
        sys.path.append(dll_path)
        runtime.logger.info(f"loaded ThermoFisher DLLs from {dll_path}")

        load("coreclr")
        import clr

        for ref in refs:
            clr.AddReference(ref)
            runtime.logger.info(f"Added PythonNet CLR reference: {ref}")

        initialized = True
