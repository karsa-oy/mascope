from mascope_runtime import MascopeRuntimeModule


lib_runtime = None


def init(**kwargs):
    global lib_runtime
    if not lib_runtime:
        lib_runtime = MascopeRuntimeModule("standard-lib", **kwargs)
