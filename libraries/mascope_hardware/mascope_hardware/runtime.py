from mascope_runtime import MascopeRuntimeModule


hardware_runtime = None


def init(**kwargs):
    global hardware_runtime
    if not hardware_runtime:
        hardware_runtime = MascopeRuntimeModule("hardware-lib", **kwargs)
