from typing import List, Dict, Annotated, Optional
import os
import json
import typer
import platform

from mascope_runtime import MascopeRuntimeModule

from mascope_cli.runtime import runtime

from .tools import dev_tools_app
from .. import lib



dev_app=typer.Typer()

concurrently='concurrently.cmd' if platform.system() == 'Windows' else 'concurrently'


def run_module(mod: List[Dict]):
    return f'"cd {mod['pkg_path']} && {mod['run']}"'


@dev_app.callback()
def main():
    """
    Manage your development environment
    """

# Add the tools_app as a subgroup under dev
dev_app.add_typer(dev_tools_app, name="tools")

@dev_app.command()
def run(
        modules: Annotated[List[str], typer.Argument()]=None,
        host: Annotated[Optional[bool], typer.Option("--host", "-h")] = False
    ):
    """
    Run your development environment

    Runs the backend and frontend by default. Use the --all flag to run all
    services, or pass service names as arguments. To list available services,
    run 'mascope modules --runnable'.

    """
    # select processes
    selected=[mod
        for mod in runtime.pkgs
        if mod['name'] in (modules or ['backend', 'frontend'])
    ]
    if not len(selected):
        [tag] = modules
        selected=[mod
            for mod in runtime.pkgs
            if tag in mod['tags']
        ]
    # set mode to dev
    runtime.state.mode = "dev"
    # set config env var
    frontend_runtime = MascopeRuntimeModule('frontend')
    os.environ['MASCOPE_ENV'] = runtime.env
    os.environ['MASCOPE_RUNTIME'] = json.dumps({
        "mode": frontend_runtime.mode,
        "env": frontend_runtime.env,
        "meta": frontend_runtime.meta.model_dump(),
        "config": frontend_runtime.config.model_dump()
    })
    if host:
        os.environ['MASCOPE_DEVHOST'] = 'HOST'
    # construct arguments
    names=f'--names {','.join(map(lambda proc: f'{proc['name']}', selected))}'
    cmds=f'{" ".join(map(run_module, selected))}'
    # run command
    command=f'{concurrently} --raw {names} {cmds}'
    print(f"Running command: {command}")
    lib.run(command)


def install_module(mod, lock = False):
    if mod['install']:
        options=f'--names "{mod['name']}"'
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
        lib.run(f'{concurrently} {options} "cd {mod['pkg_path']} && {env_setup} {lock_cmd} {mod['install']}"')


def uninstall_module(mod):
    if mod['install']:
        options=f'--names "{mod['name']}"'
        # execution
        lib.run(f'{concurrently} {options} "cd {mod['pkg_path']} && {mod['uninstall']}"')


@dev_app.command()
def install(mods: Annotated[Optional[List[str]], typer.Argument()] = None):
    """
    Install or update modules in your dev env

    To preview which packages get installed, run 'mascope modules --installable'.
    """
    install_all = mods == None
    for pkg in runtime.pkgs:
        if (install_all or (pkg['name'] in (mods or []))):
            install_module(pkg)


@dev_app.command()
def uninstall(mods: Annotated[Optional[List[str]], typer.Argument()] = None):
    """
    Uninstall modules in your dev env

    To preview which packages can be uninstall, run 'mascope modules --installable'.
    """
    uninstall_all = mods == None
    for pkg in reversed(runtime.pkgs):
        if (uninstall_all or (pkg['name'] in (mods or []))):
            uninstall_module(pkg)
