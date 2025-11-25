"""
Redis container management for multi-worker development.

Provides commands to start, stop, and manage Redis Docker containers
required for Socket.IO coordination across multiple uvicorn workers.
"""

import os
import subprocess
from typing import Annotated
import typer
from mascope_cli.cmd.dev.docker import (
    is_docker_running,
    check_and_start_docker,
)
from mascope_cli.runtime import runtime

dev_redis_app = typer.Typer()


def _manage_redis_container() -> bool:
    """
    Manage local Redis Docker container.

    Checks if container exists and is running, starts if stopped,
    or creates if it doesn't exist.

    :raise: subprocess.CalledProcessError: If Docker commands fail
    :return: True if container is running or successfully started
    :rtype: bool
    """
    redis_cfg = runtime.full_config.backend.redis

    # Check if container is running
    result = subprocess.run(
        [
            "docker",
            "ps",
            "--filter",
            f"name={redis_cfg.container_name}",
            "--format",
            "{{.Names}}",
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    if redis_cfg.container_name in result.stdout:
        runtime.logger.success(
            f"Redis container '{redis_cfg.container_name}' is running on port {redis_cfg.port}"
        )
        return True

    # Check if container exists but is stopped
    result = subprocess.run(
        [
            "docker",
            "ps",
            "-a",
            "--filter",
            f"name={redis_cfg.container_name}",
            "--format",
            "{{.Names}}",
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    # Start if exists
    if redis_cfg.container_name in result.stdout:
        runtime.logger.info(f"Starting Redis container '{redis_cfg.container_name}'...")
        subprocess.run(
            ["docker", "start", redis_cfg.container_name],
            capture_output=True,
            check=True,
        )
        runtime.logger.success(f"Redis started on port {redis_cfg.port}")
        return True

    # Container doesn't exist, create it
    runtime.logger.info(
        f"Creating Redis container '{redis_cfg.container_name}' on port {redis_cfg.port}..."
    )
    subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "-p",
            f"{redis_cfg.port}:{redis_cfg.port}",
            "--name",
            redis_cfg.container_name,
            "--restart",
            "unless-stopped",
            redis_cfg.image,
            "redis-server",
            "--port",
            str(redis_cfg.port),
        ],
        capture_output=True,
        check=True,
    )
    runtime.logger.success(f"Redis created and started on port {redis_cfg.port}")
    return True


def check_and_start_redis() -> bool:
    """
    Check if Redis is running and start it if necessary.

    Validates Redis configuration, checks container status, and automatically
    creates/starts the container if needed. Only manages local Docker containers
    (localhost/127.0.0.1); remote Redis hosts are assumed to be externally managed.

    :return: True if Redis is running or successfully started, False otherwise
    :rtype: bool
    """
    # Validate Redis configuration exists
    if not (redis_cfg := runtime.full_config.backend.redis):
        runtime.logger.warning("Redis not configured in .mascope.toml")
        return False

    # Skip Docker management for remote Redis hosts
    if redis_cfg.host not in ["localhost", "127.0.0.1"]:
        runtime.logger.info(f"Redis configured for remote host: {redis_cfg.host}")
        runtime.logger.info("  Skipping Docker container management")
        return True

    # Check if Docker is running (with interactive prompts)
    if not check_and_start_docker(allow_skip=True, auto_start=True):
        return False  # User chose to skip or Docker failed to start

    # Manage local Docker container
    try:
        return _manage_redis_container()
    except subprocess.CalledProcessError as e:
        runtime.logger.error(f"Failed to start Redis: {e}")
        runtime.logger.info("  Redis is required for multi-worker mode.")
        runtime.logger.info(
            f"  Run manually: docker run -d -p {redis_cfg.port}:{redis_cfg.port} "
            f"--name {redis_cfg.container_name} {redis_cfg.image}"
        )
        return False
    except FileNotFoundError:
        runtime.logger.error(
            "Docker not found. Install Docker to use Redis for multi-worker mode."
        )
        return False


@dev_redis_app.callback()
def main():
    """
    Manage Redis for multi-worker Socket.IO
    """


@dev_redis_app.command()
def start():
    """
    Start Redis container (or check if already running).

    Checks configuration, creates container if needed, and ensures Redis is running.
    """
    check_and_start_redis()


@dev_redis_app.command()
def stop():
    """
    Stop the Redis container.

    Container is not removed and can be restarted with 'start' command.
    """
    if not (redis_cfg := runtime.full_config.backend.redis):
        runtime.logger.warning("Redis not configured in .mascope.toml")
        return

    runtime.logger.info(f"Stopping Redis container '{redis_cfg.container_name}'...")

    result = subprocess.run(
        ["docker", "stop", redis_cfg.container_name],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode == 0:
        runtime.logger.success("Redis container stopped")
    else:
        runtime.logger.warning(
            f"Container '{redis_cfg.container_name}' not found or already stopped"
        )


@dev_redis_app.command()
def restart():
    """
    Restart the Redis container.

    Useful for clearing Redis data or applying configuration changes.
    """
    if not (redis_cfg := runtime.full_config.backend.redis):
        runtime.logger.warning("Redis not configured in .mascope.toml")
        return

    runtime.logger.info(f"Restarting Redis container '{redis_cfg.container_name}'...")

    result = subprocess.run(
        ["docker", "restart", redis_cfg.container_name],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode == 0:
        runtime.logger.success("Redis container restarted")
    else:
        runtime.logger.warning(f"Container '{redis_cfg.container_name}' not found")
        runtime.logger.info("  Run 'mascope dev redis start' to create it")


@dev_redis_app.command()
def remove():
    """
    Remove the Redis container completely.

    WARNING: This will delete any data stored in Redis.
    Container can be recreated with 'start' command.
    """
    if not (redis_cfg := runtime.full_config.backend.redis):
        runtime.logger.warning("Redis not configured in .mascope.toml")
        return

    # Confirm before removing
    if not typer.confirm(
        f"Remove Redis container '{redis_cfg.container_name}'? This will delete all data."
    ):
        runtime.logger.info("Cancelled.")
        return

    runtime.logger.info(f"Removing Redis container '{redis_cfg.container_name}'...")
    subprocess.run(
        ["docker", "rm", "-f", redis_cfg.container_name],
        capture_output=True,
        check=False,
    )
    runtime.logger.success("Redis container removed")


@dev_redis_app.command()
def status():
    """
    Show Redis container status and configuration.

    Displays current configuration from .mascope.toml, worker settings,
    and Docker container status.
    """
    if not (redis_cfg := runtime.full_config.backend.redis):
        runtime.logger.warning("Redis not configured in .mascope.toml")
        typer.echo("\nTo enable Redis, add to your .mascope.toml:")
        typer.echo(
            """
            [redis]
            host = "localhost"
            port = 6379
            container_name = "mascope_redis"
            image = "redis:7-alpine"
            """
        )
        return

    # Display Redis configuration
    typer.secho("\n=== Redis Configuration ===", bold=True)
    typer.echo(f"Host:           {redis_cfg.host}")
    typer.echo(f"Port:           {redis_cfg.port}")
    typer.echo(f"URL:            {redis_cfg.get_url()}")
    typer.echo(f"Container name: {redis_cfg.container_name}")
    typer.echo(f"Image:          {redis_cfg.image}")

    # Display worker configuration if backend exists
    if backend_cfg := runtime.full_config.backend:
        workers_config = backend_cfg.workers
        workers_actual = backend_cfg.get_worker_count()

        typer.secho("\n=== Worker Configuration ===", bold=True)
        typer.echo(f"Config:         {workers_config}")
        if workers_config == "auto":
            typer.echo(
                f"Calculated:     {workers_actual} ({os.cpu_count()} CPU cores // 2)"
            )
        else:
            typer.echo(f"Workers:        {workers_actual}")

    # Check Docker status
    if not is_docker_running():
        typer.secho("\n=== Docker Status ===", bold=True)
        typer.secho("Status: NOT RUNNING", fg=typer.colors.RED)
        typer.echo("  Start Docker to use Redis")
        typer.echo("============================\n")
        return

    # Check Docker container status
    typer.secho("\n=== Container Status ===", bold=True)

    try:
        # Check if running
        result = subprocess.run(
            [
                "docker",
                "ps",
                "--filter",
                f"name={redis_cfg.container_name}",
                "--format",
                "{{.Status}}",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        if result.stdout.strip():
            typer.secho("Status: RUNNING", fg=typer.colors.GREEN)
            typer.echo(f"  {result.stdout.strip()}")
        else:
            # Check if stopped
            result = subprocess.run(
                [
                    "docker",
                    "ps",
                    "-a",
                    "--filter",
                    f"name={redis_cfg.container_name}",
                    "--format",
                    "{{.Status}}",
                ],
                capture_output=True,
                text=True,
                check=True,
            )

            if result.stdout.strip():
                typer.secho("Status: STOPPED", fg=typer.colors.YELLOW)
                typer.echo(f"  {result.stdout.strip()}")
                typer.echo("\nRun 'mascope dev redis start' to start it")
            else:
                typer.secho("Status: NOT CREATED", fg=typer.colors.BLUE)
                typer.echo("\nRun 'mascope dev redis start' to create it")

    except (subprocess.CalledProcessError, FileNotFoundError):
        typer.secho("Status: UNKNOWN (Docker not available)", fg=typer.colors.RED)

    typer.echo("============================\n")


@dev_redis_app.command()
def logs(
    follow: Annotated[
        bool,
        typer.Option("--follow", "-f", help="Follow log output"),
    ] = False,
    tail: Annotated[
        int,
        typer.Option("--tail", "-n", help="Number of lines to show from the end"),
    ] = 100,
):
    """
    Show Redis container logs.

    Useful for debugging connection issues or monitoring Redis activity.
    """
    if not (redis_cfg := runtime.full_config.backend.redis):
        runtime.logger.warning("Redis not configured in .mascope.toml")
        return

    cmd = ["docker", "logs"]
    if follow:
        cmd.append("-f")
    cmd.extend(["--tail", str(tail), redis_cfg.container_name])

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError:
        runtime.logger.warning(f"Container '{redis_cfg.container_name}' not found")
        runtime.logger.info("  Run 'mascope dev redis start' to create it")
    except KeyboardInterrupt:
        runtime.logger.success("\nStopped following logs")


@dev_redis_app.command()
def cli():
    """
    Open Redis CLI inside the container.

    Provides direct access to Redis for debugging or manual operations.

    Example commands:
        INFO              # Server info and stats
        CLIENT LIST       # Show connected clients
        PUBSUB CHANNELS   # List active pub/sub channels
        MONITOR           # Watch all commands (Ctrl+C to exit)
    """
    if not (redis_cfg := runtime.full_config.backend.redis):
        runtime.logger.warning("Redis not configured in .mascope.toml")
        return

    # Check if Docker is running
    if not is_docker_running():
        runtime.logger.error("Docker daemon is not running")
        runtime.logger.info("  Start Docker Desktop first")
        return

    # Check if container is running
    result = subprocess.run(
        [
            "docker",
            "ps",
            "--filter",
            f"name={redis_cfg.container_name}",
            "--format",
            "{{.Names}}",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    if redis_cfg.container_name not in result.stdout:
        runtime.logger.warning(f"Container '{redis_cfg.container_name}' is not running")
        runtime.logger.info("  Run 'mascope dev redis start' first")
        return

    runtime.logger.info(
        f"Opening Redis CLI in container '{redis_cfg.container_name}'..."
    )
    runtime.logger.info("  Type 'exit' or press Ctrl+D to close")
    typer.echo("")

    try:
        subprocess.run(
            [
                "docker",
                "exec",
                "-it",
                redis_cfg.container_name,
                "redis-cli",
                "-p",
                str(redis_cfg.port),
            ],
            check=True,
        )
    except subprocess.CalledProcessError:
        runtime.logger.error("Failed to open Redis CLI")
    except KeyboardInterrupt:
        runtime.logger.success("\nClosed Redis CLI")
