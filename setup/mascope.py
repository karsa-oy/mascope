import os
import platform
import subprocess
import shlex
import sys
import tomllib

# CONSTS

path = os.getcwd()


palette = {
    "magenta": "#d8137f",
    "red": "#d65407",
    "orange": "#dc8a0e",
    "green": "#17ad98",
    "blue": "#149bda",
    "purple": "#796af5",
    "pink": "#c720ca",
}

colors = {
    "cli": palette["blue"],
    "backend": palette["green"],
    "frontend": palette["orange"],
    "notebooks": palette["red"],
    "tof-agent": palette["pink"],
    "file-uploader": palette["purple"],
    "file-converter": palette["magenta"],
    "error": "red",
}

# CONFIG

cli = {"name": "cli"}

toml_path = os.path.join(path, "runtime", "lib", "mascope_runtime", "base.mascope.toml")
with open(toml_path, "rb") as f:
    config = tomllib.load(f)
    modules = [
        {
            key: mod.get(key) if key != "name" else name
            for key in (
                "name",  # name of the module (e.g. 'backend')
                "tags",  # tags for running as part of a group (e.g. 'file')
                "pkg_path",  # path of the module's package
                "install",  # command to install the module (optional)
                "uninstall",  # command to uninstall the module (optional)
                "run",  # command to run the module (optional)
            )
        }
        for name, mod in config.items()
        if (mod is not None)
    ]

# UTILS


def concurrently(prefix: str, color: str, command: str):
    executible = (
        "concurrently.cmd" if platform.system() == "Windows" else "concurrently"
    )
    options = f'--names "{prefix}" --prefixColors {color}'
    return subprocess.run(
        shlex.split(
            f'{executible} {options} "{command}"'
        ),  # split to ensure correct parsing
        cwd=path,
    )


def run(mod: dict, command: str, throw: bool = True) -> None:
    """
    Execute a command in a subprocess

    :param command: The shell command to execute
    :param runtime: The current runtime
    :param vars: A dictionary of environment variables to set in the subprocess
    """
    result = concurrently(mod["name"], colors[mod["name"]], command)
    if result.returncode > 0 and throw:
        concurrently(mod["name"], "red", "echo 'Critical error: operation failed.'")
        raise SystemExit("Mascope setup script failed.")


# INSTALLERS


def install_module(mod):
    if mod["install"]:
        python_path = os.environ["PIPX_DEFAULT_PYTHON"]
        # environment setup
        env_setup = (
            f"poetry env use {python_path} &&" if "poetry" in mod["install"] else ""
        )
        # execution
        run(mod, f"cd {mod['pkg_path']} && {env_setup} {mod['install']}")


def uninstall_module(mod):
    if mod["uninstall"]:
        run(mod, f"cd {mod['pkg_path']} && {mod['uninstall']}")


def install():
    """
    Install or update modules in your dev env
    """
    # install CLI
    run(cli, "pipx uninstall mascope_cli", throw=False)
    run(cli, "cd ./runtime/cli && pipx install .")
    # install modules
    for mod in modules:
        install_module(mod)


def uninstall():
    """
    Uninstall modules in your dev env
    """
    # uninstall modules
    for mod in reversed(modules):
        uninstall_module(mod)
    # uninstall CLI
    run(cli, "pipx uninstall mascope_cli", throw=False)


# EXECUTION

if __name__ == "__main__":
    if sys.argv[1] == "install":
        install()
    elif sys.argv[1] == "uninstall":
        uninstall()
