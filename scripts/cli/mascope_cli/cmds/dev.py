import typer, os
from typing import List, Dict, Annotated

from . import lib

dev=typer.Typer(help="🏗️ Manage your development environment")

# RUN

def run_pkg(pkg: List[Dict]):
    return f'"cd {os.path.join(lib.repo_path, *pkg['path'])} && {pkg['run']}"'

@dev.command()
def run(processes: Annotated[List[str], typer.Argument()]=None, kill_others: bool=True, all: bool=False):
    """
    🚀 Run your development environment

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
    # construct arguments
    names=f'--names "{','.join(map(lambda proc: f'"{proc['name']}"', selected))}"'
    colors=f'--prefix-colors "{','.join(map(lambda proc: proc['color'], selected))}"'
    cmds=f'{" ".join(map(run_pkg, selected))}'
    options='--kill-others' if kill_others else ''
    # run command
    lib.run(f'concurrently.cmd {options} {names} {colors} {cmds}')

# INSTALL

def install_pkg(pkg):
    if pkg['install']:
        options=f'--names "{pkg['name']}" --prefix-colors {pkg['color']}'
        path=os.path.join(lib.repo_path, *pkg['path'])
        env_setup=(
            f'poetry env use {lib.python_path} &&'
            if 'poetry' in pkg['install']
            else ''
        )
        print(env_setup)
        lib.run(f'concurrently.cmd {options} "cd {path} && {env_setup} {pkg['install']}"')

@dev.command()
def install():
    """
    ✨ Install or update your dev env

    To preview which packages get installed, run 'mascope dev pkgs --installable'.
    """
    for pkg in lib.pkgs:
        install_pkg(pkg)

# PKGS

@dev.command()
def pkgs(installable: bool = False, runnable: bool = False):
    """
    📦 List packages in the monorepo

    Use --installable to list packages installed by 'mascope dev install' and
    --runnable to list packages that can be run by 'mascope dev run'.
    """
    def show(pkg):
        conditions=[
            (pkg['install'] if installable else True),
            (pkg['run'] if runnable else True)
        ]
        return all(conditions)

    for pkg in lib.pkgs:
        if show(pkg):
            print(pkg['name'])
            for key, value in pkg.items():
                if key != 'name' and key != 'path':
                    print('', key, value, sep="\t")
                if key == 'path':
                    print('', key, os.path.join('.', *value), sep="\t")

# PATH

@dev.command()
def path():
    """
    📂 Print the path to your mascope repository

    This information is stored in the MASCOPE_REPO_PATH enviroment
    variable and used by the CLI.
    """
    print(lib.repo_path)