import os, subprocess, shlex

mascope_path=os.environ['MASCOPE_PATH']

def run(command, cwd=mascope_path):
    subprocess.run(
        shlex.split(command),
        cwd=cwd,
        stderr=subprocess.STDOUT
    )
