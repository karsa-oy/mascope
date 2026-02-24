"""
Redis utilities for development.

Container managed by docker-compose. Use 'mascope dev up/down' for lifecycle management.
"""

import subprocess
import time
from typing import Annotated
import typer

from mascope_cli.cmd.dev.docker import is_docker_running
from mascope_cli.runtime import runtime

dev_redis_app = typer.Typer()


def _is_container_running() -> bool:
    """Check if Redis container is running."""
    container_name = runtime.full_config.backend.redis.get_redis_container_name(
        mode="dev"
    )

    try:
        result = subprocess.run(
            [
                "docker",
                "ps",
                "--filter",
                f"name={container_name}",
                "--format",
                "{{.Names}}",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        return container_name in result.stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def _is_redis_responding() -> bool:
    """Check if Redis responds to PING."""
    redis_cfg = runtime.full_config.backend.redis

    result = subprocess.run(
        [
            "docker",
            "exec",
            redis_cfg.get_redis_container_name(mode="dev"),
            "redis-cli",
            "-p",
            str(redis_cfg.port),
            "ping",
        ],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )

    return result.returncode == 0 and "PONG" in result.stdout


def _check_prerequisites() -> bool:
    """
    Check if Redis environment is ready.

    :return: True if all checks pass
    """
    if not (redis_cfg := runtime.full_config.backend.redis):
        runtime.logger.warning("Redis not configured in .mascope.toml")
        return False

    # Skip Docker management for remote Redis hosts
    if redis_cfg.host not in ["localhost", "127.0.0.1"]:
        runtime.logger.info(f"Redis configured for remote host: {redis_cfg.host}")
        return False

    if not is_docker_running():
        runtime.logger.error("Docker daemon is not running")
        return False

    return True


def _check_redis() -> bool:
    """
    Check if Redis is ready.

    :return: True if configured, running, and responding
    """
    if not _check_prerequisites():
        return False

    if not _is_container_running():
        return False

    return _is_redis_responding()


def wait_for_redis(max_wait: int = 30) -> bool:
    """
    Wait for Redis container to be running and responding (public check for other modules).

    :param max_wait: Maximum wait time in seconds
    :return: True if Redis is ready within timeout, False otherwise
    """
    runtime.logger.info("Waiting for redis...")

    waited = 0
    while waited < max_wait:
        if _check_redis():
            runtime.logger.success("Redis is ready")
            return True
        time.sleep(2)
        waited += 2

    runtime.logger.warning(f"Redis not ready after {max_wait}s")
    return False


@dev_redis_app.callback()
def main():
    """Redis utilities (container managed by docker-compose)"""


@dev_redis_app.command()
def status():
    """
    Show Redis container status and configuration.
    """
    if not _check_prerequisites():
        return

    redis_cfg = runtime.full_config.backend.redis

    # Configuration
    runtime.logger.info("=== Configuration ===")
    runtime.logger.info(f"Host: {redis_cfg.host}:{redis_cfg.port}")
    runtime.logger.info(f"URL:  {redis_cfg.get_redis_url()}")
    runtime.logger.info(f"Container: {redis_cfg.get_redis_container_name(mode='dev')}")

    # Status
    runtime.logger.info("=== Status ===")
    if not _is_container_running():
        runtime.logger.warning("Container not running")
        runtime.logger.info("Run 'mascope dev up' to start")
        return

    if _is_redis_responding():
        runtime.logger.success("Redis ready")
    else:
        runtime.logger.warning("Redis not responding")
        runtime.logger.info("Check logs: mascope dev redis logs")


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

    Useful for debugging connection issues or monitoring activity.
    """
    if not _check_prerequisites():
        return

    if not _is_container_running():
        runtime.logger.warning("Container not running")
        runtime.logger.info("Run 'mascope dev up' to start")
        return

    container_name = runtime.full_config.backend.redis.get_redis_container_name(
        mode="dev"
    )
    cmd = ["docker", "logs"]

    if follow:
        cmd.append("-f")
    cmd.extend(["--tail", str(tail), container_name])

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError:
        runtime.logger.warning(f"Container '{container_name}' not found")
    except KeyboardInterrupt:
        runtime.logger.success("Stopped following logs")


@dev_redis_app.command()
def cli():
    """
    Open Redis CLI inside the container.

    Provides direct access to Redis for debugging or manual operations.

    Example commands:
        INFO                                 # Server info and stats
        CLIENT LIST                          # Show connected clients
        PUBSUB CHANNELS                      # List active pub/sub channels
        MONITOR                              # Watch all commands (Ctrl+C to exit)
        KEYS mascope:session:*               # List all saved mascope sessions
        TTL mascope:session:/:{session_key}  # Check session TTL
    """
    if not _check_prerequisites():
        return

    if not _is_container_running():
        runtime.logger.warning("Redis container is not running")
        runtime.logger.info("Run 'mascope dev up' first")
        return

    redis_cfg = runtime.full_config.backend.redis

    runtime.logger.info("Opening Redis CLI")
    runtime.logger.info("Type 'exit' or press Ctrl+D to close")

    try:
        subprocess.run(
            [
                "docker",
                "exec",
                "-it",
                redis_cfg.get_redis_container_name(mode="dev"),
                "redis-cli",
                "-p",
                str(redis_cfg.port),
            ],
            check=True,
        )
    except subprocess.CalledProcessError:
        runtime.logger.error("Failed to open Redis CLI")
    except KeyboardInterrupt:
        runtime.logger.success("Closed Redis CLI")
