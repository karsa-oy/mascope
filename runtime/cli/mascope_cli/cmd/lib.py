import os
import subprocess
import shlex

from mascope_cli.runtime import runtime
from mascope_runtime.module import MascopeRuntimeModule


def run(
    command: str, runtime: MascopeRuntimeModule = runtime, vars: dict = dict()
) -> None:
    """
    Execute a command in a subprocess

    :param command: The shell command to execute
    :param runtime: The current runtime
    :param vars: A dictionary of environment variables to set in the subprocess
    """
    env = os.environ.copy()
    for key, val in vars.items():
        env[key] = val
    subprocess.run(
        shlex.split(command),  # split to ensure correct parsing
        cwd=runtime.root_path,
        stderr=subprocess.STDOUT,
        env=env,
    )
