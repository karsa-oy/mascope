import typer
from typing import Annotated

backend_app = typer.Typer()


@backend_app.callback()
def main():
    """
    Run services in the Mascope backend
    """
    pass


@backend_app.command()
def run(
    service: Annotated[
        str | None,
        typer.Argument(
            help="The backend service to launch",
        ),
    ],
):
    """
    Launch a Mascope backend service
    """
    if service == "api-server":
        from mascope_backend.app import run as run_api_server

        run_api_server()
    elif service == "file-converter":
        from mascope_backend.file_converter.service import run as run_file_converter

        run_file_converter()


def exec():
    backend_app()
