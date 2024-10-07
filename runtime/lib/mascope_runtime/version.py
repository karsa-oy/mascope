import subprocess
import shlex


def exec(cmd: str):
    try:
        return (
            subprocess.check_output(shlex.split(cmd), stderr=subprocess.DEVNULL)
            .decode("utf-8")
            .replace("\n", "")
        )
    except:
        return None


def get_version():
    # construct a prefix from branch
    branch = exec("git rev-parse --abbrev-ref HEAD")
    if branch == "master":
        prefix = ""
    elif branch == "develop":
        prefix = "staging-"
    else:
        prefix = f"{branch}-"
    # get the latest commit date and short hash
    commit_id = exec('git log -1 --date=format:"%Y.%m.%d" --format="%ad-%h"')
    # combine them to form the version string
    return f"{prefix}{commit_id}" if commit_id else "unknown-version"
