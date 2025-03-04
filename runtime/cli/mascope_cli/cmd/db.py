import subprocess
import os
import typer
from mascope_cli.runtime import runtime

db_app = typer.Typer()


@db_app.callback()
def main():
    """
    Manage mascope SQLite database
    """


@db_app.command()
def backup():
    """
    Create a backup of the SQLite database.
    """
    run_poetry_command("mascope-db-backup")


def run_poetry_command(command_name: str):
    """
    Helper function to run a poetry command within the backend directory.
    """
    backend_dir = os.path.join(runtime.path, "backend")
    try:
        result = subprocess.run(
            ["poetry", "run", command_name],
            cwd=backend_dir,
            check=True,
            capture_output=True,
            text=True,
        )
        if result.stdout:
            print(result.stdout)
    except subprocess.CalledProcessError as e:
        runtime.logger.error(f"Command {command_name} failed:\n{e.stderr}")
        raise typer.Exit(code=1)
