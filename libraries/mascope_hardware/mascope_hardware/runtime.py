from mascope_runtime import Runtime


hardware_runtime = None


def init(**opts):
    global hardware_runtime
    if not hardware_runtime:
        hardware_runtime = Runtime("hardware-lib", **opts)
