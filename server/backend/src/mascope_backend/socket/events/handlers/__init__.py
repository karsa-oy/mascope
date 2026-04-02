"""Socket.IO event handlers for client-server communication."""

# Imported for side-effects — each submodule registers
# its own socket handlers on import.
from . import default, file_converter, tof_agent  # noqa: F401
