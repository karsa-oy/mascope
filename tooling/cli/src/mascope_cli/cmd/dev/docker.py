"""
Docker daemon management for development.

Provides reusable utilities for checking and starting Docker
across platforms (Windows, macOS, Linux).
"""

import os
import platform
import subprocess
import time

import typer

from mascope_cli.runtime import runtime


dev_docker_app = typer.Typer()


def is_docker_running() -> bool:
    """
    Check if Docker daemon is running.

    :return: True if Docker daemon is accessible, False otherwise
    :rtype: bool
    """
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=5,
            check=False,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def start_docker_desktop() -> bool:
    """
    Attempt to start Docker Desktop on the host system.

    Platform-specific:
    - Windows: Start 'Docker Desktop.exe'
    - macOS: Use 'open -a Docker'
    - Linux: Attempt systemctl (requires sudo)

    :return: True if start command succeeded, False otherwise
    :rtype: bool
    """
    system = platform.system()

    try:
        if system == "Windows":
            docker_paths = [
                r"C:\Program Files\Docker\Docker\Docker Desktop.exe",
                os.path.expandvars(r"%ProgramFiles%\Docker\Docker\Docker Desktop.exe"),
            ]

            for docker_path in docker_paths:
                if os.path.exists(docker_path):
                    runtime.logger.info(f"Starting Docker Desktop from: {docker_path}")
                    subprocess.Popen(
                        [docker_path],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        creationflags=subprocess.DETACHED_PROCESS
                        | subprocess.CREATE_NEW_PROCESS_GROUP,
                    )
                    return True

            runtime.logger.warning(
                "Docker Desktop executable not found in standard locations"
            )
            return False

        elif system == "Darwin":  # macOS
            runtime.logger.info("Starting Docker Desktop...")
            subprocess.Popen(
                ["open", "-a", "Docker"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True

        elif system == "Linux":
            runtime.logger.info(
                "Attempting to start Docker daemon (may require sudo)..."
            )
            result = subprocess.run(
                ["sudo", "systemctl", "start", "docker"],
                capture_output=True,
                timeout=10,
                check=False,
            )
            return result.returncode == 0

        else:
            runtime.logger.warning(f"Unsupported platform: {system}")
            return False

    except Exception as e:
        runtime.logger.error(f"Failed to start Docker: {e}")
        return False


def wait_for_docker(
    max_wait: int = 90, message: str = "Waiting for Docker to start..."
) -> bool:
    """
    Wait for Docker daemon to become available.

    :param max_wait: Maximum seconds to wait
    :param message: Message to display while waiting
    :return: True if Docker started within timeout, False otherwise
    :rtype: bool
    """
    runtime.logger.info(message)
    typer.echo("Press Ctrl+C to abort\n")

    waited = 0
    try:
        while waited < max_wait:
            if is_docker_running():
                runtime.logger.success("Docker is now running!")
                return True

            time.sleep(2)
            waited += 2
            typer.echo(f"\rStill waiting... ({waited}s/{max_wait}s)", nl=False)

        typer.echo("")
        runtime.logger.warning(f"Docker did not start within {max_wait}s")
        return False

    except KeyboardInterrupt:
        typer.echo("")
        runtime.logger.info("Aborted by user")
        return False


def check_and_start_docker() -> None:
    """
    Check if Docker is running and start it if necessary.

    High-level function for services that require Docker.

    :return: True if Docker is running, False if user chose to skip
    :raises typer.Exit: If user chooses to abort
    :rtype: None
    """
    if is_docker_running():
        return

    runtime.logger.error("Docker daemon is not running, it is required to run Mascope.")

    # Build options based on parameters
    options = []
    options.append("  [s] Try to start Docker automatically")
    options.append("  [w] I'll start Docker manually (wait and retry)")
    options.append("  [a] Abort")

    typer.echo("\nOptions:")
    for option in options:
        typer.echo(option)

    choice = typer.prompt(
        "\nWhat would you like to do?",
        type=str,
        default="a",
        show_default=True,
    ).lower()

    if choice == "s":
        if start_docker_desktop():
            typer.echo(
                "Waiting for Docker to initialize (this may take 20-30 seconds)..."
            )
            if wait_for_docker(max_wait=90):
                return
        else:
            runtime.logger.error("Failed to start Docker Desktop automatically")
            raise typer.Exit(1)

    elif choice == "w":
        if wait_for_docker(max_wait=60):
            return
        runtime.logger.error("Docker did not start within timeout")
        raise typer.Exit(1)

    else:  # "a" or any other input
        runtime.logger.info("Aborted")
        raise typer.Exit(1)


@dev_docker_app.callback()
def main():
    """
    Manage Docker Desktop for development
    """


@dev_docker_app.command()
def status():
    """
    Check Docker daemon status.
    """
    if is_docker_running():
        runtime.logger.success("Docker daemon is running")

        # Show version info
        result = subprocess.run(
            ["docker", "version", "--format", "{{.Server.Version}}"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            typer.echo(f"Docker version: {result.stdout.strip()}")
    else:
        runtime.logger.error("Docker daemon is not running")
        typer.echo("\nRun 'mascope dev docker start' to start it")


@dev_docker_app.command()
def start():
    """
    Start Docker Desktop if it's not running.
    """
    if is_docker_running():
        runtime.logger.success("Docker is already running")
        return

    runtime.logger.info("Docker is not running. Attempting to start...")

    if start_docker_desktop():
        wait_for_docker(max_wait=90)
    else:
        runtime.logger.error("Failed to start Docker Desktop")
        runtime.logger.info("  Please start Docker Desktop manually")


@dev_docker_app.command()
def restart():
    """
    Restart Docker Desktop (requires manual restart on most platforms).
    """
    system = platform.system()

    if system == "Linux":
        runtime.logger.info("Restarting Docker daemon...")
        result = subprocess.run(
            ["sudo", "systemctl", "restart", "docker"],
            check=False,
        )
        if result.returncode == 0:
            runtime.logger.success("Docker daemon restarted")
        else:
            runtime.logger.error("Failed to restart Docker daemon")
    else:
        runtime.logger.info(
            f"Docker Desktop restart on {system} requires manual action:"
        )
        typer.echo("  1. Right-click Docker Desktop icon in system tray")
        typer.echo("  2. Select 'Restart'")
