import typer, os
from typing import List, Dict, Annotated

import mascope_runtime as runtime

from .. import lib

mascope_path = os.environ['MASCOPE_PATH']

dev=typer.Typer()

def run_mod(mod: List[Dict]):
    return f'"cd {os.path.join(mascope_path, *mod['path'])} && {mod['run']}"'

@dev.callback()
def main():
    """
    Manage your development environment
    """

def run_threaded(processes: Annotated[List[str], typer.Argument()]=None, all: bool=False):
    import shlex
    import subprocess
    import threading

    keep_running = True

    def run_thread(module):
        args = shlex.split(module['run'])
        proc = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=os.path.join(mascope_path, *module['path'])
        )
        assert proc.stdout
        try:
            while keep_running:
                line = proc.stdout.readline().decode("utf-8", errors="replace")
                if line != "":
                    print(line)
        except Exception:
            pass
        proc.terminate()  # ensure its dead
        print(f"{module['name']} exited")

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

    # run commands in threads
    threads = [
        threading.Thread(
            target=run_thread,
            args=[mod]
        ) for mod in selected
    ]
    for thread in threads:
        thread.start()
    # run loop
    try:
        while True:
            pass
    except KeyboardInterrupt:
        keep_running = False
        # wait for proper exit
        for thread in threads:
            thread.join()

def run_concurrently(processes: Annotated[List[str], typer.Argument()]=None, kill_others: bool=False, all: bool=False):
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


@dev.command()
def run(processes: Annotated[List[str], typer.Argument()]=None, kill_others: bool=False, all: bool=False, threaded: bool=False):
    """
    Run your development environment

    Runs the backend and frontend by default. Use the --all flag to run all
    services, or pass service names as arguments. To list available services,
    run 'mascope modules --runnable'.

    Python services can still be run directly with poetry, but the frontend
    must be run with this command.
    
    Runs with concurrently.js by default, or using a custom Python threads
    implementation when using the --threaded flag.

    """
    if (threaded):
        run_threaded(processes, all)
    else:
        run_concurrently(processes, kill_others, all)

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

