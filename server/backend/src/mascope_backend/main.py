import typer
from typing import Annotated

backend_app = typer.Typer()


@backend_app.callback()
def main():
    """
    Run services in the Mascope backend
    """
    pass


services = ["api-server", "file-converter"]


@backend_app.command()
def run(
    service: Annotated[
        str,
        typer.Argument(
            help="The backend service to launch, one of: " + ", ".join(services),
        ),
    ] = "api-server",
):
    """
    Launch a Mascope backend service
    """
    match service:
        case "api-server":
            from mascope_backend.app import run as run_api_server

            run_api_server()
        case "file-converter":
            from mascope_backend.file_converter.service import run as run_file_converter

            run_file_converter()
        case _:
            raise ValueError(f"Unknown service: {service}")


def exec():
    backend_app()
