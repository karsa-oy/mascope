import os
import platform
import subprocess
import shlex
import sys
import tomllib

concurrently = "concurrently.cmd" if platform.system() == "Windows" else "concurrently"

path = os.getcwd()

toml_path = os.path.join(path, "runtime", "lib", "mascope_runtime", "base.mascope.toml")

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
    "tof-agent": palette["magenta"],
    "file-mover": palette["purple"],
}


def load_modules():
    with open(toml_path, "rb") as f:
        config = tomllib.load(f)
        return [
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


def run(command: str, vars: dict = dict()) -> None:
    """
    Execute a command in a subprocess

    :param command: The shell command to execute
    :param runtime: The current runtime
    :param vars: A dictionary of environment variables to set in the subprocess
    """
    env = os.environ.copy()
    for key, val in vars.items():
        env[key] = val
    result = subprocess.run(
        shlex.split(command),  # split to ensure correct parsing
        cwd=path,
        env=env,
    )
    if result.stderr:
        raise Exception(result.stderr)


def install_module(mod, lock=False):
    if mod["install"]:
        options = f'--names "{mod["name"]}" --prefixColors {colors[mod["name"]]}'
        python_path = os.environ["PIPX_DEFAULT_PYTHON"]
        # lock command
        poetry_lock = "poetry lock &&" if "poetry" in mod["install"] else None
        npm_lock = (
            "npm install --package-lock-only &&" if "npm" in mod["install"] else None
        )
        lock_cmd = (poetry_lock or npm_lock or "") if lock else ""
        # environment setup
        env_setup = (
            f"poetry env use {python_path} &&" if "poetry" in mod["install"] else ""
        )
        # execution
        run(
            f'{concurrently} {options} "cd {mod["pkg_path"]} && {env_setup} {lock_cmd} {mod["install"]}"'
        )


def uninstall_module(mod):
    if mod["uninstall"]:
        options = f'--names "{mod["name"]}" --prefixColors {colors[mod["name"]]}'
        # execution
        run(f'{concurrently} {options} "cd {mod["pkg_path"]} && {mod["uninstall"]}"')


def install():
    """
    Install or update modules in your dev env
    """
    # install CLI
    options = f"--names cli --prefixColors {colors['cli']}"
    try:
        run(f'{concurrently} {options} "pipx uninstall mascope_cli"')
    except Exception:
        pass
    # install modules
    run(f'{concurrently} {options} "cd ./runtime/cli && pipx install ."')
    modules = load_modules()
    for mod in modules:
        install_module(mod)


def uninstall():
    """
    Uninstall modules in your dev env
    """
    # uninstall modules
    modules = load_modules()
    for mod in reversed(modules):
        uninstall_module(mod)
    # uninstall CLI
    options = f"--names cli --prefixColors {colors['cli']}"
    run(f'{concurrently} {options} "pipx uninstall mascope_cli"')


if __name__ == "__main__":
    if sys.argv[1] == "install":
        install()
    elif sys.argv[1] == "uninstall":
        uninstall()
