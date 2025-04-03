import typer

from typing import Optional, List
from typing_extensions import Annotated


import mascope_cli.cmd.lib as lib

backend_app = typer.Typer(add_help_option=False)


@backend_app.callback(
    invoke_without_command=True, context_settings={"ignore_unknown_options": True}
)
def main(args: Annotated[Optional[List[str]], typer.Argument()] = None) -> None:
    """
    Run a Mascope backend service.
    """
    lib.run(command=f"uv run mascope-backend {' '.join(args)}")
