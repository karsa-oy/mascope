import mascope_hardware.runtime as hardware_runtime


from mascope_runtime import Runtime


lib_runtime = None


def init(**opts):
    global lib_runtime
    if not lib_runtime:
        hardware_runtime.init(**opts)
        lib_runtime = Runtime("standard-lib", **opts)
