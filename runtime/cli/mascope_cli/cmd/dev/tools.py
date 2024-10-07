"""
Development tools for the Mascope CLI.

This module contains utility commands that assist in various development tasks.
These tools are grouped under the 'dev tools' section and are designed to enhance
developer productivity by automating common tasks, such as managing files or running scripts.
"""

import os
import subprocess
from shutil import which
import typer

dev_tools_app = typer.Typer(
    help="Additional helper tools to assist in development tasks"
)


@dev_tools_app.command()
def open_gitignore():
    """
    Opens all .gitignore files in the repository in VSCode.
    """
    repo_path = os.environ["MASCOPE_PATH"]
    gitignore_files = []

    # Use os.walk to find all .gitignore files
    for root, _, files in os.walk(repo_path):
        for file in files:
            if file == ".gitignore":
                gitignore_files.append(os.path.join(root, file))

    # Find the full path to the code executable
    code_path = which("code")

    if not code_path:
        print(
            "Error: 'code' command not found. Make sure VSCode is installed and 'code' is in your PATH."
        )
        return

    # Open each .gitignore file in VSCode
    for file in gitignore_files:
        try:
            subprocess.run([code_path, file], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Failed to open {file}: {e}")

    print(f"Opened {len(gitignore_files)} .gitignore files in VSCode")
