import subprocess, shlex

from .env import repo_path

def run(command):
    subprocess.run(
        shlex.split(command),
        cwd=repo_path,
        stderr=subprocess.STDOUT
    )
