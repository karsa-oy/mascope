"""Mascope's Thermo Fisher Orbitrap API.

Importing this package does not load any .NET (Thermo RawFileReader) assemblies:
the default reader backend is the open-source OpenTFRaw (`mascope-opentfraw`), and
the Thermo backend loads its DLLs lazily, only when used. Mascope ships without
the proprietary RawFileReader DLLs; see `mascope_thermo.lib` and the README to
enable the Thermo backend.
"""
