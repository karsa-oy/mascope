import os, subprocess, shlex

from mascope_cli.runtime import runtime


def run(command, runtime=runtime, vars=dict()):
    env = os.environ.copy()
    for key, val in vars.items():
        env[key] = val
    subprocess.run(
        shlex.split(command), cwd=runtime.root_path, stderr=subprocess.STDOUT, env=env
    )
