"""Per-user scoping for ephemeral temp downloads.

Temp files (spreadsheet exports, peak CSVs, download bundles) are written under
a per-user subdirectory of the runtime temp dir. The ``/api/temp`` download
route only ever reads from the caller's own subdirectory, so a user can only
download files they generated - never another tenant's, even when the filename
is known or guessable. The basename reduction plus the containment check also
close off path traversal.
"""

import os

from mascope_backend.runtime import runtime


def user_temp_dir(user_id: int, *, create: bool = True) -> str:
    """
    Return the temp directory reserved for ``user_id``.

    :param user_id: The owning user's id.
    :param create: Create the directory if missing. Writers keep the default;
        the download route passes ``False`` so a mere GET probe does not mint
        empty per-user directories.
    :return: Absolute path to the user's temp directory.
    """
    path = runtime.env.path("temp", str(int(user_id)))
    if create:
        os.makedirs(path, exist_ok=True)
    return path


def user_temp_path(user_id: int, filename: str, *, create: bool = True) -> str:
    """
    Resolve ``filename`` inside the user's temp dir, rejecting traversal.

    The filename is reduced to its basename so no path separators or parent
    references can escape the per-user directory, and the resolved path is
    verified to stay within it.

    :param user_id: The owning user's id.
    :param filename: Untrusted leaf filename (e.g. from a download link).
    :param create: Create the user's directory if missing (see
        :func:`user_temp_dir`).
    :raises ValueError: If ``filename`` does not resolve to a file directly
        inside the user's temp directory.
    :return: Absolute path to the file inside the user's temp directory.
    """
    safe = os.path.basename(filename)
    if not safe or safe in (os.curdir, os.pardir):
        raise ValueError(f"Unsafe temp filename: {filename!r}")
    base = os.path.normpath(user_temp_dir(user_id, create=create))
    # The normalized path must stay within the user's dir. (normpath +
    # prefix check is the containment guard static analysis recognizes.)
    path = os.path.normpath(os.path.join(base, safe))
    if not path.startswith(base + os.sep):
        raise ValueError(f"Unsafe temp filename: {filename!r}")
    # Defense in depth: a symlink inside the dir must not escape it either.
    if not os.path.realpath(path).startswith(os.path.realpath(base) + os.sep):
        raise ValueError(f"Unsafe temp filename: {filename!r}")
    return path
