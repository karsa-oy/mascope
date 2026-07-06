"""
Version resolution for the CLI.

In a source checkout the version comes from git (`Runtime.parse_version`:
release tag or branch build id). A pip-installed CLI has no checkout, so the
installed distribution version is used instead, formatted like a release tag
(`v1.2.0`) — which also makes `mascope prod up` deploy the images matching
the installed CLI rather than `latest`.
"""

from importlib import metadata


def resolve_version(runtime) -> str:
    """
    The Mascope version for this invocation.

    :param runtime: The CLI runtime (only `parse_version` is used).
    :return: A git-derived version when available, otherwise the installed
             `mascope_cli` distribution version as `v{version}`, otherwise
             the literal `unknown-version`.
    :rtype: str
    """
    version = runtime.parse_version()
    if version != "unknown-version":
        return version
    try:
        package_version = metadata.version("mascope_cli")
    except metadata.PackageNotFoundError:
        return version
    # The workspace uses a 0.0.0 placeholder; only a real release version
    # is meaningful as a deploy tag.
    if package_version and package_version != "0.0.0":
        return f"v{package_version}"
    return version
