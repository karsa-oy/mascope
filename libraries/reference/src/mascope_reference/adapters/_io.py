"""Shared low-level readers for the common source dump formats.

Two formats cover most of the sources: SDF (PubChem, ChEBI, LIPID MAPS,
COCONUT) and delimited text (CompTox, NORMAN, COCONUT CSV). Both readers are
streaming and transparently handle gzip so adapters can be pointed straight at
a downloaded ``.sdf`` / ``.sdf.gz`` / ``.tsv`` / ``.csv`` without a decompress
step.
"""

import csv
import gzip
from collections.abc import Iterator
from pathlib import Path
from typing import IO


def _open_text(path: Path) -> IO[str]:
    """Open a path as UTF-8 text, transparently decompressing ``.gz``."""
    if path.suffix == ".gz":
        return gzip.open(path, mode="rt", encoding="utf-8", errors="replace")
    return open(path, mode="rt", encoding="utf-8", errors="replace")


def _open_binary(path: Path) -> IO[bytes]:
    """Open a path as raw bytes, transparently decompressing ``.gz``.

    XML parsers must read bytes so an ``encoding`` declaration in the document
    prolog is honored rather than rejected - a pre-decoded text stream with such
    a declaration raises.
    """
    if path.suffix == ".gz":
        return gzip.open(path, mode="rb")
    return open(path, mode="rb")


def read_sdf_records(path: Path) -> Iterator[dict[str, str]]:
    """Stream an SDF file, yielding one dict of data fields per molecule.

    SDF molecules are separated by a ``$$$$`` line; data fields follow the
    connection table as ``> <FIELD_NAME>`` headers each followed by their value
    line(s). Only the data fields are returned - the connection table (atom /
    bond block) is skipped, since every identity field an adapter needs
    (formula, InChIKey, name, SMILES) is published as a tagged data field.

    :param path: Path to an ``.sdf`` or ``.sdf.gz`` file.
    :yield: Mapping of data-field name to its (possibly multi-line) value.
    """
    with _open_text(path) as handle:
        fields: dict[str, str] = {}
        current_key: str | None = None
        current_lines: list[str] = []

        def flush_field() -> None:
            nonlocal current_key, current_lines
            if current_key is not None:
                fields[current_key] = "\n".join(current_lines).strip()
            current_key = None
            current_lines = []

        for line in handle:
            line = line.rstrip("\n").rstrip("\r")
            if line.startswith("$$$$"):
                flush_field()
                if fields:
                    yield fields
                fields = {}
                continue
            if line.startswith("> "):
                # New data-field header, e.g. "> <PUBCHEM_COMPOUND_CID>".
                flush_field()
                start = line.find("<")
                end = line.find(">", start + 1)
                if start != -1 and end != -1:
                    current_key = line[start + 1 : end]
                continue
            if current_key is not None:
                if line == "":
                    # Blank line terminates a data-field value in SDF.
                    flush_field()
                else:
                    current_lines.append(line)
            # Lines outside a data field (the connection table) are ignored.
        # A trailing molecule with no terminating $$$$ is still emitted.
        flush_field()
        if fields:
            yield fields


def read_delimited(path: Path, delimiter: str = ",") -> Iterator[dict[str, str]]:
    """Stream a delimited text file, yielding one dict per data row.

    Uses the header row for keys. Handles gzip transparently. Field values are
    returned verbatim (stripped of surrounding whitespace); empty strings are
    left as-is for the adapter to interpret.

    :param path: Path to a ``.csv`` / ``.tsv`` (optionally ``.gz``) file.
    :param delimiter: Field delimiter (``","`` for CSV, ``"\\t"`` for TSV).
    :yield: Mapping of header column name to cell value.
    """
    with _open_text(path) as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        for row in reader:
            yield {
                (key.strip() if key else key): (value.strip() if value else "")
                for key, value in row.items()
                if key is not None
            }
