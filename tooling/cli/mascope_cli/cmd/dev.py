import typer, os
from typing import List, Dict, Annotated

import mascope_runtime as runtime

from .. import lib

mascope_path = os.environ['MASCOPE_PATH']

dev=typer.Typer()

def run_pkg(pkg: List[Dict]):
    return f'"cd {os.path.join(mascope_path, *pkg['path'])} && {pkg['run']}"'

@dev.callback()
def main():
    """
    🏗️ Manage your development environment
    """

@dev.command()
def run(processes: Annotated[List[str], typer.Argument()]=None, kill_others: bool=True, all: bool=False):
    """
    Run your development environment

    Runs the backend and frontend by default. Use the --all flag to run all
    services, or pass service names as arguments.

    To list available services, run 'mascope dev pkgs --runnable'.
    """
    runnable=[pkg['name'] for pkg in lib.pkgs if pkg['run']]
    pkg_names=(processes                 # use argument if provided
        or (runnable if all else None)   # if --all option used, run anything runnable
        or ['backend', 'frontend']       # otherwise use common defaults
    )
    # select processes
    selected=[pkg
        for pkg in lib.pkgs 
        if pkg['name'] in pkg_names
    ]
    # set config env var
    config=runtime.config.autoload()
    os.environ['MASCOPE_CONFIG'] = config.model_dump_json()
    # construct arguments
    names=f'--names "{','.join(map(lambda proc: f'"{proc['name']}"', selected))}"'
    colors=f'--prefix-colors "{','.join(map(lambda proc: proc['color'], selected))}"'
    cmds=f'{" ".join(map(run_pkg, selected))}'
    options='--kill-others' if kill_others else ''
    # run command
    lib.run(f'concurrently.cmd {options} {names} {colors} {cmds}')

# INSTALL

def install_pkg(pkg, lock):
    if pkg['install']:
        options=f'--names "{pkg['name']}" --prefix-colors {pkg['color']}'
        path=os.path.join(mascope_path, *pkg['path'])
        python_path=os.environ['PIPX_DEFAULT_PYTHON']
        # lock command
        poetry_lock=(
            f'poetry lock &&'
            if 'poetry' in pkg['install']
            else None
        )
        npm_lock=(
            f'npm install --package-lock-only &&'
            if 'npm' in pkg['install']
            else None
        )
        lock_cmd= (poetry_lock or npm_lock or '') if lock else ''
        # environment setup
        env_setup=(
            f'poetry env use {python_path} &&'
            if 'poetry' in pkg['install']
            else ''
        )
        # execution
        lib.run(f'concurrently.cmd {options} "cd {path} && {env_setup} {lock_cmd} {pkg['install']}"')

@dev.command()
def install(lock: bool = False):
    """
    Install or update your dev env

    To preview which packages get installed, run 'mascope dev pkgs --installable'.
    """
    for pkg in lib.pkgs:
        install_pkg(pkg, lock)
