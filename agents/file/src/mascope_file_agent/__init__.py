"""Mascope File Agent - watches a folder and uploads new data files."""

try:
    # Written by build.ps1 so the frozen exe reports its release version;
    # absent (and gitignored) in a source checkout.
    from mascope_file_agent._version import __version__
except ImportError:
    __version__ = "dev"
