"""
Lazy access to the CLI's Runtime instance.

Importing this module is side-effect free. Creating a `Runtime` requires a
configured environment — `MASCOPE_PATH`, the `*.mascope.toml` layers, a
writable `.runtime/` for `state.json` — and reconfigures the global logger,
so instantiation is deferred until a command actually needs it. This keeps
`import mascope_cli` (and e.g. `mascope --help`) working anywhere.
"""

from mascope_runtime import Runtime


_runtime: Runtime | None = None


def get_runtime() -> Runtime:
    """
    The CLI's Runtime singleton, created on first use.

    :return: The shared Runtime instance for the `cli` module.
    :rtype: Runtime
    """
    global _runtime
    if _runtime is None:
        _runtime = Runtime("cli")
    return _runtime


class _LazyRuntime:
    """
    Attribute proxy over :func:`get_runtime`.

    Lets command modules keep importing `runtime` at module scope while the
    underlying Runtime is only instantiated on first attribute access.
    """

    def __getattr__(self, name: str):
        return getattr(get_runtime(), name)


runtime = _LazyRuntime()
