"""
Backend runtime initialization.

This module initializes the backend runtime and imports all dependency
modules so that their runtimes are properly initialized before use.
"""

# ruff: noqa: F401
# pylint: disable=unused-import

from mascope_runtime import Runtime

# Initialize dependency module runtimes (required for proper initialization)
import mascope_chem.runtime
import mascope_file.runtime
import mascope_match.runtime
import mascope_signal.runtime
import mascope_thermo.runtime
import mascope_tofwerk.runtime

runtime = Runtime("backend")
