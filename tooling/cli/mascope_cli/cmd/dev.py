import typer, os
from typing import List, Dict, Annotated

import time

import mascope_runtime as runtime

from .. import lib

mascope_path = os.environ['MASCOPE_PATH']

dev=typer.Typer()

def run_mod(mod: List[Dict]):
    return f'"cd {os.path.join(mascope_path, *mod['path'])} && {mod['run']}"'

@dev.callback()
def main():
    """
    🏗️ Manage your development environment
    """

@dev.command()
def run(processes: Annotated[List[str], typer.Argument()]=None, kill_others: bool=False, all: bool=False):
    """
    Run your development environment

    Runs the backend and frontend by default. Use the --all flag to run all
    services, or pass service names as arguments.

    To list available services, run 'mascope modules --runnable'.
    """
    runnable=[mod['name'] for mod in runtime.modules if mod['run']]
    mod_names=(processes                 # use argument if provided
        or (runnable if all else None)   # if --all option used, run anything runnable
        or ['backend', 'frontend']       # otherwise use common defaults
    )
    # select processes
    selected=[mod
        for mod in runtime.modules
        if mod['name'] in mod_names
    ]
    # set config env var
    config=runtime.config.autoload()
    os.environ['MASCOPE_CONFIG'] = config.model_dump_json()
    # construct arguments
    names=f'--names {','.join(map(lambda proc: f'{proc['name']}', selected))}'
    colors=f'--prefix-colors "{','.join(map(lambda proc: proc['color'], selected))}"'
    cmds=f'{" ".join(map(run_mod, selected))}'
    options='--kill-others' if kill_others else ''
    # run command
    lib.run(f'concurrently.cmd --raw {options} {names} {colors} {cmds}')

# INSTALL

def install_mod(mod, lock):
    if mod['install']:
        options=f'--names "{mod['name']}" --prefix-colors {mod['color']}'
        path=os.path.join(mascope_path, *mod['path'])
        python_path=os.environ['PIPX_DEFAULT_PYTHON']
        # lock command
        poetry_lock=(
            f'poetry lock &&'
            if 'poetry' in mod['install']
            else None
        )
        npm_lock=(
            f'npm install --package-lock-only &&'
            if 'npm' in mod['install']
            else None
        )
        lock_cmd= (poetry_lock or npm_lock or '') if lock else ''
        # environment setup
        env_setup=(
            f'poetry env use {python_path} &&'
            if 'poetry' in mod['install']
            else ''
        )
        # execution
        lib.run(f'concurrently.cmd {options} "cd {path} && {env_setup} {lock_cmd} {mod['install']}"')

@dev.command()
def install(lock: bool = False):
    """
    Install or update your dev env

    To preview which packages get installed, run 'mascope modules --installable'.
    """
    for mod in runtime.modules:
        install_mod(mod, lock)
