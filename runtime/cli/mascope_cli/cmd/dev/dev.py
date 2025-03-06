from typing import List, Annotated, Optional
import os
import json
import typer
import platform
import base64

from mascope_runtime import Runtime

from mascope_cli.runtime import runtime

from .tools import dev_tools_app
from .. import lib


dev_app = typer.Typer()

concurrently = "concurrently.cmd" if platform.system() == "Windows" else "concurrently"


@dev_app.callback()
def main():
    """
    Manage your development environment
    """


# Add the tools_app as a subgroup under dev
dev_app.add_typer(dev_tools_app, name="tools")


@dev_app.command()
def run(
    modules: Annotated[
        List[str],
        typer.Argument(
            help="List of modules or module groups to run; see `mascope modules --runnable` to see runnable modules",
            show_default="backend frontend",
        ),
    ] = None,
    host: Annotated[
        Optional[bool],
        typer.Option(
            "--host",
            "-h",
            help="Expose the backend and frontend dev servers to the network",
        ),
    ] = False,
    reload: Annotated[
        Optional[bool],
        typer.Option(
            "--reload",
            "-r",
            help="Spawn the backend in a seperate terminal tab to enable HMR in Windows",
        ),
    ] = False,
):
    """
    Run your development environment

    Pass modules to run as arguments, for example:
        mascope dev run backend file-converter
    """
    # select modules by name
    selected = [
        mod
        for mod in runtime.modules
        if mod["name"] in (modules or ["backend", "frontend"])
    ]
    # use tags if no modules were selected
    if not len(selected):
        [tag] = modules
        selected = [mod for mod in runtime.modules if tag in mod["tags"]]
    # set mode to dev
    runtime.state.mode = "dev"
    # set config env var
    frontend_runtime = Runtime("frontend")
    os.environ["MASCOPE_ENV"] = runtime.env.name
    os.environ["MASCOPE_RUNTIME"] = json.dumps(
        {
            "mode": frontend_runtime.mode,
            "env": frontend_runtime.env.name,
            "meta": frontend_runtime.meta.model_dump(),
            "config": frontend_runtime.config.model_dump(),
            "version": os.environ["MASCOPE_VERSION"],
        }
    )
    # if --host set, expose dev server to network
    if host:
        os.environ["MASCOPE_DEVHOST"] = "HOST"

    # build a module runner
    def run_module(mod):
        """
        Run a module, overriding the backend's default behavior
        when a reload flag is passed.
        """
        if reload and mod["name"] == "backend":
            # helper to pass env vars
            def pass_envvar(var):
                value = os.environ.get(var)
                return (
                    f"[Environment]::SetEnvironmentVariable('{var}', '{value}')"
                    if value
                    else None
                )

            pass_envvars = " && ".join(
                [
                    envvar
                    for envvar in map(
                        pass_envvar,
                        [
                            "MASCOPE_LOGLEVEL",  # pass the log level
                            "MASCOPE_LOGGREP",  # pass the log grep
                            "MASCOPE_ENV",  # pass the runtime env
                            "MASCOPE_DEVHOST",  # pass host option
                        ],
                    )
                    if envvar
                ]
            )
            # construct the command
            cmd = f"cd '{mod['pkg_path']}' && {pass_envvars} && {mod['run']}"
            # complex commands are best encoded to avoid needing escape chars
            base64_cmd = base64.b64encode(bytearray(cmd, "utf-16-le")).decode()
            # open a new tab in the current windows terminal and run
            return f'"wt --window 0 pwsh -noExit -EncodedCommand {base64_cmd}"'
        else:
            # default behavior
            return f'"cd {mod["pkg_path"]} && {mod["run"]}"'

    # construct arguments
    names = f"--names {','.join(map(lambda proc: f'{proc["name"]}', selected))}"
    cmds = f"{' '.join(map(run_module, selected))}"
    # run command
    command = f"{concurrently} --raw {names} {cmds}"
    print(f"Running command: {command}")
    lib.run(command)
