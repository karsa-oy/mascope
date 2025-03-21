import typer

from typing import Optional, List
from typing_extensions import Annotated


from mascope_cli import runtime
from mascope_cli.cmd import lib

agent_app = typer.Typer(add_help_option=False)


@agent_app.callback(
    invoke_without_command=True, context_settings={"ignore_unknown_options": True}
)
def main(args: Annotated[Optional[List[str]], typer.Argument()] = None) -> None:
    """
    Run a Mascope agent
    """
    if len(args) != 1:
        runtime.logger.error("mascope agent requires exactly 1 argument: file or tof")
        return
    lib.run(command=f"uv run mascope-{args[0]}-agent")
