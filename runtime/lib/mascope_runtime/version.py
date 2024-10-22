import subprocess
import shlex


def exec(cmd: str):
    """
    Run a command in a subprocess and return the output
    """
    try:
        return (
            subprocess.check_output(shlex.split(cmd), stderr=subprocess.DEVNULL)
            .decode("utf-8")
            .replace("\n", "")
        )
    except Exception:
        # ignore errors, return nothing
        return None


def get_version():
    """
    Construct a version string for the app from git history.
    The latest commit is used to construct the version, with
    the format differing depend on branch:

    In `master`:
      format: v{iso_date}-{short_commit_hash}
      example: v2024.09.03-d06bfef9

    In other branches:
      format: {branch}-v{iso_date}-{short_commit_hash}
      example: feature/new-stuff-v2024.09.03-d06bfef9
    """
    # construct a prefix from branch
    branch = exec("git rev-parse --abbrev-ref HEAD")
    if branch == "master":
        prefix = "v"
    else:
        prefix = f"{branch}-v"
    # get the latest commit date and short hash
    date_and_commit_hash = exec('git log -1 --date=format:"%Y.%m.%d" --format="%ad-%h"')
    # combine them to form the version string
    return (
        f"{prefix}{date_and_commit_hash}" if date_and_commit_hash else "unknown-version"
    )
