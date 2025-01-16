import mascope_lib.runtime as lib_runtime

lib_runtime.init()

import mascope_hardware.runtime as hardware_runtime

hardware_runtime.init()

# Import this here to avoid "free(): invalid pointer" error on Linux
if hardware_runtime.hardware_runtime.mode == "prod":
    from mascope_hardware.tofwerk.lib.TwTool import *


# this should be last to ensure log level is correct
from mascope_runtime import MascopeRuntimeModule

runtime = MascopeRuntimeModule("backend")
